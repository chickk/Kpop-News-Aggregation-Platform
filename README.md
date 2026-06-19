# K-Pop News Aggregation Platform

K-Pop News Aggregation Platform is a news tracking and analysis tool for K-pop coverage. It fetches articles from news providers, uses an LLM pipeline to extract summaries, sentiment scores, tags, artists, groups, and source metadata, then enriches artists and groups with Wikimedia/Wikidata data so users can search for a keyword and open each result with processed context already available.

## Features

- Search K-pop news by keyword and automatically fetch new articles when local results are missing or insufficient.
- Process fetched articles with an LLM to generate summaries, sentiment, tags, mentions, and source metadata.
- Handle ambiguous search terms such as `TWICE`, where the query can also match unrelated general-language content.
- Use concept search for known entity mappings and keyword search plus post-filtering for unknown terms.
- Enrich artists and groups with canonical names, aliases, images, Wikipedia links, Wikidata IDs, and member/group relationships.
- Provide Articles, Artists, Groups, and Sources views in the frontend.
- Show processed article details, including summary, signals, matched content, and article content.
- Run locally with Docker Compose for MongoDB and the FastAPI backend, plus a Vite/React frontend.

## Architecture

```text
frontend/              React + Vite UI
app/main.py            FastAPI API entrypoint
app/news_aggregators/  News API adapter
app/pipeline/          Fetch/process pipeline and LLM extraction
app/entity_enrichment/ Wikimedia/Wikidata entity enrichment
app/data_layer/        Beanie/MongoDB document schemas
app/adapters/          Mongo repositories and unit of work
tests/                 Backend unit and integration tests
```

High-level data flow:

```text
User search
  -> GET /api/content
  -> local MongoDB query
  -> auto fetch from News API when needed
  -> LLM processing
  -> entity dedupe/enrichment
  -> frontend article/detail views
```

## Requirements

- Python `>=3.12,<3.14`
- Node.js `24` recommended
- MongoDB on port `27017`
- Docker / Docker Compose, optional but recommended
- News API key
- LLM provider key, recommended: Gemini API key
- Wikimedia user agent when Wikimedia enrichment is enabled

## Environment Variables

Create a `.env` file in the project root. `.env` is ignored by git and must not be committed.

```dotenv
MONGO_URI=mongodb://localhost:27017/idolTracker
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

NEWS_API_KEY=your_news_api_key

NLP_MODE=cheap
NLP_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.5-flash-lite
LLM_MAX_TOKENS=768
LLM_TEMPERATURE=0
NLP_ARTICLE_MAX_CHARS=1500
NLP_ALLOW_RULE_FALLBACK=false

GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=
OPEN_AI_KEY=

NEWS_AUTO_FETCH_MAX_RESULTS=25
NEWS_AUTO_PROCESS_MAX_RESULTS=
NEWS_AUTO_PROCESS_CONCURRENCY=4
NEWS_AUTO_FETCH_FALLBACK_DAYS=30
NEWS_AUTO_FETCH_LANGUAGE=eng

WIKI_ENRICHMENT_ENABLED=true
WIKI_GROUP_MIN_CONFIDENCE=0.65
WIKI_ARTIST_MIN_CONFIDENCE=0.65
WIKI_REQUEST_TIMEOUT_SECONDS=4
WIKI_REQUEST_MIN_INTERVAL_SECONDS=0.5
WIKI_REQUEST_MAX_RETRIES=3
WIKIMEDIA_USER_AGENT=Kpop-News-Aggregation-Platform/0.1 (your-email@example.com)
```

Supported LLM providers:

| Provider | `NLP_PROVIDER` | Key env | Default model |
| --- | --- | --- | --- |
| Gemini | `gemini` | `GEMINI_API_KEY` | `gemini/gemini-2.5-flash-lite` |
| Groq | `groq` | `GROQ_API_KEY` | `groq/llama-3.1-8b-instant` |
| OpenAI | `openai` | `OPEN_AI_KEY` | `openai/gpt-4o-mini` |

## Local Development

### 1. Start the backend and MongoDB

```bash
docker compose up --build
```

The backend runs at:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

### 2. Start the frontend

```bash
cd frontend
npm ci
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

If the backend is running somewhere else, set:

```bash
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

## API Overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check |
| `GET` | `/api/content` | Search/list processed articles; may trigger auto fetch and processing |
| `GET` | `/api/content/latest` | Latest processed articles |
| `GET` | `/api/content/{id}` | Article detail |
| `GET` | `/api/artists` | Artist list |
| `GET` | `/api/artists/{id}` | Artist detail |
| `GET` | `/api/groups` | Group list |
| `GET` | `/api/group/{id}` | Group detail |
| `GET` | `/api/sources` | Source list |
| `POST` | `/api/pipeline/fetch` | Manually fetch raw articles |
| `POST` | `/api/pipeline/process` | Manually process raw articles |
| `POST` | `/api/pipeline/run` | Run fetch and process pipeline |

Example:

```bash
curl "http://localhost:8000/api/content?search=NMIXX&limit=10"
```

## Testing

Backend tests:

```bash
python -m pytest
```

MongoDB integration tests require MongoDB to be reachable. The default test URI is:

```text
mongodb://localhost:27017/idolTracker_test
```

Override it with:

```bash
MONGO_TEST_URI=mongodb://localhost:27017/idolTracker_test python -m pytest
```

Frontend build:

```bash
cd frontend
npm run build
```

LLM smoke test:

```bash
python scripts/smoke_llm.py
```

Before running the LLM smoke test, make sure `.env` contains `NLP_PROVIDER` and the matching API key.

## Deployment

The repository includes GitHub Actions workflows and AWS deployment examples:

- Frontend: S3 + CloudFront
- Backend: Docker image + ECR + EC2 Docker Compose

See:

```text
docs/aws-deployment.md
```

The frontend workflow currently runs only the build step on push. AWS deployment steps run only when the workflow is triggered manually with `workflow_dispatch`, which prevents push builds from failing before AWS repository secrets and variables are configured.

## Security Notes

- Do not commit `.env`, API keys, AWS credentials, or SSH keys.
- Store GitHub Actions secrets and variables in repository settings, not in workflow files or documentation.
- Set a clear `WIKIMEDIA_USER_AGENT` when using Wikimedia APIs.
- Do not expose MongoDB port `27017` or internal backend ports in production.

## Development Notes

- News search strategy and query filtering are mainly in `app/article_search.py`.
- LLM provider setup is in `app/main.py` and `app/pipeline/llm_modules/config.py`.
- Wikimedia enrichment is in `app/entity_enrichment/`.
- Artist/group alias and dedupe logic is in `app/entity_aliases.py`.
- The main frontend UI is in `frontend/src/App.tsx`.
