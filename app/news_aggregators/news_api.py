import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from eventregistry import (
    EventRegistry,
    QueryArticlesIter,
    ComplexArticleQuery,
    CombinedQuery,
    BaseQuery,
)

from app.interfaces.news_aggregator import INewsAggregator
from app.models.articles import RawArticle
from app.models.sources import RawSource


class NewsAPIAggregator(INewsAggregator):
    """EventRegistry News API implementation of the news aggregator."""

    def __init__(self, apiKey):
        self.api = EventRegistry(apiKey=apiKey, allowUseOfArchive=False)

    async def fetch_articles(
        self,
        query_terms: List[str],
        concepts: bool,
        start_date: datetime = None,
        end_date: datetime = None,
        language: Optional[str] = None,
        max_results: int = 100,
    ) -> List[RawArticle]:
        """Fetch articles from EventRegistry based on query terms and concepts."""

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        query_parts = [
            BaseQuery(dateStart=start_date_str, dateEnd=end_date_str),
        ]

        if language:
            query_parts.append(BaseQuery(lang=language))

        if concepts:
            concept_uris = self.get_concept_uris(concepts=query_terms)
            queries = (
                [BaseQuery(conceptUri=uri) for uri in concept_uris]
                if concept_uris
                else []
            )
        else:
            queries = (
                [BaseQuery(keyword=term) for term in query_terms] if query_terms else []
            )

        search_queries = [CombinedQuery.OR(queries)]

        if search_queries:
            query_parts.append(CombinedQuery.OR(search_queries))

        cq = ComplexArticleQuery(CombinedQuery.AND(query_parts))
        q = QueryArticlesIter.initWithComplexQuery(cq)

        raw_articles = []
        results = q.execQuery(self.api, sortBy="date", maxItems=max_results)
        for article_data in results:
            raw_article = self._parse_article(article_data)
            if raw_article:
                raw_articles.append(raw_article)

        return raw_articles

    def get_concept_uris(self, concepts: List[str]) -> List[str]:
        """Get concept URIs from concept names using EventRegistry."""
        uris = []
        for concept in concepts:
            uri = self.api.getConceptUri(concept)
            if uri:
                uris.append(uri)

        return uris

    async def get_source_info(self) -> str:
        """Get information about this news source."""
        return "EventRegistry News API - Global news aggregator"

    def _parse_article(self, article_data: dict) -> Optional[RawArticle]:
        """
        Parse EventRegistry article data into RawArticle model.

        EventRegistry article structure (from schema):
        {
            'uri': '...',
            'title': '...',
            'body': '...',
            'url': '...',
            'lang': 'en',
            'date': '2024-01-01',
            'time': '12:00:00',
            'dateTime': '2024-01-01T12:00:00Z',
            'source': {'title': 'Source Name', 'uri': '...'},
            'image': 'https://...',
            'isDuplicate': false,
            'concepts': [...],  # Array of concepts with labels and scores
            'categories': [...],  # Array of categories
            'location': {...}  # Location information
        }
        """
        try:
            pub_date = None
            if article_data.get("dateTime"):
                pub_date = datetime.fromisoformat(
                    article_data["dateTime"].replace("Z", "+00:00")
                )

            author = None
            if article_data.get("author"):
                if isinstance(article_data["author"], dict):
                    author = article_data["author"].get("name")
                elif isinstance(article_data["author"], str):
                    author = article_data["author"]

            # Extract source information
            source = None
            if article_data.get("source") and isinstance(article_data["source"], dict):
                source_data = article_data["source"]
                source_name = source_data.get("title", "Unknown")
                source_description = source_data.get("description")
                source_image = source_data.get("image")

                source_country_code = None
                if source_data.get("location") and isinstance(
                    source_data["location"], dict
                ):
                    source_country_code = source_data["location"].get("code2")

                source = RawSource(
                    title=source_name,
                    description=source_description,
                    image=source_image,
                    country_code=source_country_code,
                )

            image_urls = []
            if article_data.get("image"):
                image_urls = [article_data["image"]]

            return RawArticle(
                title=article_data.get("title", ""),
                text=article_data.get("body", ""),
                url=article_data.get("url", ""),
                author=author,
                publication_date=pub_date,
                raw_source=source,
                language=article_data.get("lang"),
                processed=False,
                image_urls=image_urls,
            )
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None


if __name__ == "__main__":
    import asyncio

    async def main():
        load_dotenv()
        news_agg = NewsAPIAggregator(os.getenv("NEWS_API_KEY"))

        print("Fetching K-Pop articles from EventRegistry...")
        articles = await news_agg.fetch_articles(
            query_terms=["K-Pop"],
            concepts=True,
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 7),
            max_results=25,
        )

        print(f"\nFetched {len(articles)} articles:")
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article.title}")
            print(f"   Source: {article.raw_source.title}")
            print(f"   Date: {article.publication_date}")
            print(f"   URL: {article.url}")
            if article.image_urls:
                print(f"   Image: {article.image_urls[0][:60]}...")

    asyncio.run(main())
