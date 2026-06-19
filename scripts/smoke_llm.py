import asyncio
import os
from pathlib import Path

import dspy
from dotenv import load_dotenv

from app.models.articles import RawArticle
from app.models.sources import RawSource
from app.pipeline.generators import NLPModule
from app.pipeline.llm_modules.config import setup_dspy


ROOT_DIR = Path(__file__).resolve().parents[1]


async def main():
    load_dotenv(ROOT_DIR / ".env")

    provider = os.getenv("NLP_PROVIDER", "groq").strip().lower()
    model = os.getenv("LLM_MODEL") or {
        "groq": "groq/llama-3.1-8b-instant",
        "gemini": "gemini/gemini-2.5-flash-lite",
        "openai": "openai/gpt-4o-mini",
    }.get(provider, "groq/llama-3.1-8b-instant")
    key_env = {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai": "OPEN_AI_KEY",
    }.get(provider, "GROQ_API_KEY")
    api_key = os.getenv(key_env)

    if not api_key:
        raise SystemExit(f"Missing {key_env}. Add it to .env before running this smoke test.")

    os.environ.setdefault("NLP_MODE", "cheap")
    os.environ.setdefault("NLP_ARTICLE_MAX_CHARS", "1500")

    lm = setup_dspy(
        model=model,
        api_key=api_key,
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "384")),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
    )
    dspy.configure(lm=lm)

    raw_article = RawArticle(
        title="NMIXX announces comeback",
        text=(
            "K-pop girl group NMIXX announced a new comeback with a single album "
            "next month. Fans reacted positively online."
        ),
        url="https://example.com/nmixx",
        raw_source=RawSource(
            title="Example Kpop News",
            description="K-pop news",
            country_code="kor",
        ),
    )

    result = await NLPModule.generate_all_from_article(raw_article)

    print("Article extraction:")
    print(result.article.model_dump_json(indent=2))
    print("\nSource:")
    print(result.source.model_dump_json(indent=2) if result.source else None)
    print(
        f"\nCheap mode entity generation: "
        f"{len(result.new_artists)} new artists, {len(result.new_groups)} new groups"
    )


if __name__ == "__main__":
    asyncio.run(main())
