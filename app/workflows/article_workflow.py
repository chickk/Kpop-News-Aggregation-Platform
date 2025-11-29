"""
Article ingestion workflow showing the proper separation of concerns.

This demonstrates how the NewsAggregator, RawArticleRepository, and
ArticleRepository work together.
"""

from datetime import datetime
from typing import List, Optional

from app.interfaces.news_aggregator import INewsAggregator
from app.interfaces.unit_of_work import IUnitOfWork
from app.models.articles import Article


class ArticleWorkflow:
    """
    Orchestrates the article ingestion pipeline.

    Steps:
    1. Fetch raw articles from external APIs (NewsAggregator)
    2. Store raw articles in staging area (RawArticleRepository)
    3. Process raw articles with LLMs
    4. Store processed articles (ArticleRepository)
    """

    def __init__(self, aggregator: INewsAggregator, uow: IUnitOfWork):
        self.aggregator = aggregator
        self.uow = uow

    async def fetch_and_stage_articles(
        self,
        query_terms: List[str],
        use_concepts: bool = False,
        start_date: datetime = None,
        end_date: datetime = None,
        language: Optional[str] = None,
        max_results: int = 100,
    ) -> int:
        """
        Step 1: Fetch articles from external API and store in staging area.

        Args:
            query_terms: Search terms (either keywords or concept names)
            use_concepts: If True, treat query_terms as concepts; if False, as keywords
            start_date: Earliest publication date
            end_date: Latest publication date
            language: Optional language filter
            max_results: Maximum articles to fetch

        Returns:
            Number of new articles staged
        """
        # Fetch from external API (NewsAggregator does NOT store anything)
        raw_articles = await self.aggregator.fetch_articles(
            query_terms=query_terms,
            concepts=use_concepts,
            start_date=start_date,
            end_date=end_date,
            language=language,
            max_results=max_results,
        )

        new_articles = 0

        async with self.uow:
            for raw_article in raw_articles:
                # Check if we already have this article (by URL)
                existing = await self.uow.raw_articles.get_by_url(raw_article.url)
                if existing:
                    continue

                # Store in staging area
                await self.uow.raw_articles.create(raw_article)
                new_articles += 1

            await self.uow.commit()

        return new_articles

    async def process_staged_articles(self, batch_size: int = 10) -> int:
        """
        Step 2: Process raw articles from staging area.

        This would:
        - Get unprocessed raw articles
        - Run LLM extraction
        - Create processed Article objects
        - Mark raw articles as processed

        Returns:
            Number of articles processed
        """
        async with self.uow:
            # Get batch of unprocessed articles
            raw_articles = await self.uow.raw_articles.get_unprocessed(limit=batch_size)

            processed_count = 0

            for raw_article in raw_articles:
                # TODO: Run LLM extraction here
                # extracted = await self.extract_info(raw_article)

                # For now, create basic Article
                article = Article(
                    title=raw_article.title,
                    text=raw_article.text,
                    author=raw_article.author,
                    source_id=raw_article.source_name,
                    publication_date=raw_article.publication_date,
                    language=raw_article.language or "unknown",
                    summary=raw_article.text[:200],
                    sentiment=0.5,
                    artists_mentioned=[],
                    groups_mentioned=[],
                    tags=[],
                    countries=[],
                    in_event=False,
                    event_id=None,
                    groups_mentioned_ids=[],
                    artists_mentioned_ids=[],
                )

                # Save processed article
                await self.uow.articles.create(article)

                # Mark raw article as processed
                # Assuming raw articles have an 'id' field
                await self.uow.raw_articles.mark_as_processed(raw_article.url)

                processed_count += 1

            await self.uow.commit()

        return processed_count

    async def run_full_pipeline(
        self,
        query_terms: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """
        Run the complete pipeline: fetch, stage, and process.

        Returns:
            Statistics about the run
        """
        # Step 1: Fetch and stage
        staged = await self.fetch_and_stage_articles(
            query_terms=query_terms,
            start_date=start_date,
            end_date=end_date,
        )

        # Step 2: Process staged articles
        processed = await self.process_staged_articles()

        return {
            "articles_staged": staged,
            "articles_processed": processed,
        }
