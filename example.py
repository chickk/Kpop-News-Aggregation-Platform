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

from app.pipeline.llm_modules.signatures import ArticleInput

load_dotenv()


async def main():
    lm = setup_dspy(api_key=os.getenv("OPEN_AI_KEY"))

    # with dspy.context(lm=lm):
    #     extractor = ArtistExtractor()

    #     response = await extractor.aforward(
    #         artist_name="Taylor Swift", artist_groups=[]
    #     )
    #     print(response.artist_output)

    # with dspy.context(lm=lm):
    #     extractor = ArticleExtractor()
    #     example_article = RawArticle(
    #         title="Taylor Swift Announces New Album",
    #         text="Pop superstar Taylor Swift announced today that she will be releasing a new album...",
    #         url="https://example.com/article",
    #         raw_source=RawSource(
    #             title="Music News Daily", description="Latest music industry news"
    #         ),
    #         publication_date=datetime.now(),
    #     )

    #     article_in = ArticleInput(
    #         article_title=example_article.title, article_text=example_article.text
    #     )

    #     response = await extractor.aforward(article_input=article_in)
    #     # print("Extraction Response:", response)

    #     article_extract = response.article_output
    #     print("\nExtracted Info:", article_extract)

    #     final_article = Article(
    #         title=example_article.title,
    #         author=example_article.author,
    #         source_id="test-source-id",
    #         publication_date=example_article.publication_date,
    #         text=example_article.text,
    #         language=example_article.language or "en",
    #         summary=article_extract.summary,
    #         sentiment=article_extract.sentiment,
    #         artists_mentioned=article_extract.artists_mentioned,
    #         groups_mentioned=article_extract.groups_mentioned,
    #         tags=article_extract.tags,
    #         countries=article_extract.countries,
    #         in_event=False,
    #         event_id=None,
    #         groups_mentioned_ids=[],
    #         artists_mentioned_ids=[],
    #     )

    #     print("\nFinal Article:", final_article)

    with dspy.context(lm=lm):
        extractor = SourceExtractor()

        example_source = SourceInput(
            title="Pitchfork",
            description="The most trusted voice in music.",
            language="en",
            country_code="US",
        )
        response = await extractor.aforward(source_input=example_source)

        print(response.source_output)


if __name__ == "__main__":
    asyncio.run(main())
