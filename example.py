import asyncio
from datetime import datetime
import dspy
from app.models.articles import Article, RawArticle
from app.models.sources import RawSource, SourceInput
from app.pipeline.llm_modules.config import setup_dspy
from app.pipeline.llm_modules.modules import (
    ArticleExtractor,
    ArtistExtractor,
    SourceExtractor,
)
import os
from dotenv import load_dotenv
import argparse

from app.pipeline.llm_modules.signatures import ArticleInput

load_dotenv()


async def main(args):
    api_key = os.getenv("OPEN_AI_KEY")
    lm = setup_dspy(api_key=api_key)
    with dspy.context(lm=lm):
        if args.mode == "artist":
            extractor = ArtistExtractor()
            artist = args.artist
            response = await extractor.aforward(artist_name=artist, artist_groups=[])
            print(response.artist_output)
        elif args.mode == "article":
            extractor = ArticleExtractor()
            example_article = RawArticle(
                title="Taylor Swift Announces New Album",
                text="Pop superstar Taylor Swift announced today that she will be releasing a new album...",
                url="https://example.com/article",
                raw_source=RawSource(
                    title="Music News Daily", description="Latest music industry news"
                ),
                publication_date=datetime.now(),
            )

            article_in = ArticleInput(
                article_title=example_article.title, article_text=example_article.text
            )

            response = await extractor.aforward(article=article_in)
            print("Extraction Response:", response)

            article_extract = response.article_output
            print("\nExtracted Info:", article_extract)

            final_article = Article(
                title=example_article.title,
                author=example_article.author,
                source_id="test-source-id",
                publication_date=example_article.publication_date,
                text=example_article.text,
                language=example_article.language or "en",
                summary=article_extract.summary,
                sentiment=article_extract.sentiment,
                artists_mentioned=article_extract.artists_mentioned,
                groups_mentioned=article_extract.groups_mentioned,
                tags=article_extract.tags,
                countries=article_extract.countries,
                in_event=False,
                event_id=None,
                groups_mentioned_ids=[],
                artists_mentioned_ids=[],
            )

            print("\nFinal Article:", final_article)

        else:
            extractor = SourceExtractor()
            if args.source == "Pitchfork":
                example_source = SourceInput(
                    title="Pitchfork",
                    description="The most trusted voice in music.",
                    language="en",
                    country_code="US",
                )
            else:
                example_source = SourceInput(title=args.source)
            response = await extractor.aforward(source=example_source)

            print(response.source_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Pipeline Example Script")

    parser.add_argument(
        "--mode",
        type=str,
        choices=["artist", "article", "source"],
        default="source",
        help="Which extractor to run (default: source)",
    )

    parser.add_argument(
        "--artist",
        type=str,
        default="Taylor Swift",
        help="Which artist to pull from (default: Taylor Swift)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="Pitchfork",
        help="Which source to get details on (default: Pitchfork)",
    )

    args = parser.parse_args()
    asyncio.run(main(args))
