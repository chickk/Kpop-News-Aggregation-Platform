# AWS deployment

This repo deploys as a private S3 frontend behind CloudFront and a Docker Compose
FastAPI backend on EC2.

## CloudFront routing

Configure two origins and two cache behaviors:

| Path behavior | Origin | Notes |
| --- | --- | --- |
| `/api/*` | EC2 public DNS or load balancer | Disable/minimize caching, allow API methods, forward query strings and required headers. |
| `*` | Private S3 bucket | Default behavior for the Vite static app. |

Add a second behavior for `/health` to the EC2 origin if you want to check the
backend through CloudFront. Configure SPA fallback errors `403` and `404` to
return `/index.html` with status `200` for the S3 behavior.

## S3

- Keep Block Public Access enabled.
- Do not enable public bucket policies or public ACLs.
- Use CloudFront Origin Access Control (OAC) for the S3 origin.
- The bucket policy should only allow `s3:GetObject` from the CloudFront
  distribution ARN.

## EC2

Install Docker, Docker Compose, AWS CLI v2, and attach an instance profile that
can pull from ECR.

Create `/opt/idoltracker/.env`:

```dotenv
ALLOWED_ORIGINS=https://YOUR_CLOUDFRONT_DOMAIN
NLP_PROVIDER=groq
LLM_MODEL=groq/llama-3.1-8b-instant
LLM_MAX_TOKENS=768
LLM_TEMPERATURE=0.7
NLP_ARTICLE_MAX_CHARS=3000
NEWS_AUTO_FETCH_MAX_RESULTS=100
NEWS_AUTO_FETCH_FALLBACK_DAYS=30
NEWS_AUTO_FETCH_LANGUAGE=eng
OPEN_AI_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
NEWS_API_KEY=
```

The production compose file publishes only nginx on port `80`. The backend and
MongoDB are only reachable on the Docker network. MongoDB data is persisted in
the `mongo-data` named volume.

Recommended security group:

- Inbound `80` from CloudFront managed prefix list, or temporarily `0.0.0.0/0`
  during first setup.
- Inbound `443` only if TLS terminates on EC2.
- Inbound `22` only from your admin IP.
- No inbound `27017` or `8000`.

## GitHub configuration

Use GitHub OIDC with an AWS IAM role. Required repository variables:

- `AWS_REGION`
- `S3_BUCKET`
- `CLOUDFRONT_DISTRIBUTION_ID`
- `ECR_REPOSITORY`
- `EC2_HOST`
- `EC2_USER`

Required repository secrets:

- `AWS_ROLE_TO_ASSUME`
- `EC2_SSH_KEY`

The backend deploy workflow assumes the EC2 instance role can run
`aws ecr get-login-password` for the target ECR repository.
