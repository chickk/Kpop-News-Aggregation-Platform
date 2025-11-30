import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient

from app.interfaces.nlp_module import ArticlePipelineResult
from app.interfaces.news_aggregator import INewsAggregator
from app.adapters.mongo_unit_of_work import MongoUnitOfWork
from app.models.articles import RawArticle
from app.pipeline.generators import NLPModule

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pipeline:

    @staticmethod
    async def save_pipeline_results(
        results: ArticlePipelineResult,
        client: AsyncIOMotorClient,
    ) -> dict:
        """
        Save pipeline results to database using Unit of Work pattern for transactional safety.
        All operations succeed together or fail together (rollback).

        Args:
            results: ArticlePipelineResult containing generated objects
            client: AsyncIOMotorClient instance for database connection

        Returns:
            Dictionary containing saved database objects with their IDs

        Raises:
            Exception: If any database operation fails (transaction will be rolled back)
        """
        # Use Unit of Work for transactional safety
        async with MongoUnitOfWork(client, use_transaction=False) as uow:
            saved_results = {
                "article": None,
                "source": None,
                "created_artists": [],
                "created_groups": [],
            }
            # Create source (check if exists first to avoid duplicates)
            if results.source:
                existing_source = await uow.sources.get_by_name(results.source.name)
                if existing_source:
                    saved_source = existing_source
                else:
                    saved_source = await uow.sources.create(results.source)
                saved_results["source"] = saved_source
                # Set source_id on article
                results.article.source_id = str(saved_source.id)

            # Create Group, get group ids
            group_name_to_id = {}
            for group in results.new_groups:
                existing_group = await uow.groups.get_by_name(group.name)
                if existing_group:
                    group_store = existing_group
                else:
                    group_store = await uow.groups.create(group)
                    saved_results["created_groups"].append(group_store)

                group_name_to_id[group.name] = group_store.id

                if group.name in results.article.groups_mentioned:
                    group_id_str = str(group_store.id)
                    if group_id_str not in results.article.groups_mentioned_ids:
                        results.article.groups_mentioned_ids.append(group_id_str)

            # Create artists and artist-group links
            artist_updates = []
            group_updates = {}

            for artist in results.new_artists:
                existing_artist = await uow.artists.get_by_name(artist.name)
                if existing_artist:
                    artist_store = existing_artist
                else:
                    artist_store = await uow.artists.create(artist)
                    saved_results["created_artists"].append(artist_store)

                artist_id_str = str(artist_store.id)
                if artist_id_str not in results.article.artists_mentioned_ids:
                    results.article.artists_mentioned_ids.append(artist_id_str)

                # Establish bidirectional links between artist and their groups
                if artist_store.in_groups and hasattr(artist_store, "group_names"):
                    artist_needs_update = False

                    for group_name in artist_store.group_names:
                        if group_name in group_name_to_id:
                            group_id = group_name_to_id[group_name]
                            group_id_str = str(group_id)
                            artist_id_str = str(artist_store.id)

                            # Artist → Group link
                            if group_id_str not in artist_store.group_ids:
                                artist_store.group_ids.append(group_id_str)
                                artist_needs_update = True

                            # Group → Artist link
                            if group_id not in group_updates:
                                group_updates[group_id] = []
                            if artist_id_str not in group_updates[group_id]:
                                group_updates[group_id].append(artist_id_str)

                    if artist_needs_update:
                        artist_updates.append(artist_store)

            for artist_to_update in artist_updates:
                await uow.artists.update(artist_to_update.id, artist_to_update)

            # Update groups with artist references
            for group_id, artist_ids in group_updates.items():
                group = await uow.groups.get_by_id(str(group_id))
                if group:
                    group_needs_update = False

                    if not hasattr(group, "artist_ids"):
                        group.artist_ids = []

                    for artist_id in artist_ids:
                        if artist_id not in group.artist_ids:
                            group.artist_ids.append(artist_id)
                            group_needs_update = True

                    if group_needs_update:
                        await uow.groups.update(group_id, group)

            # Save article
            saved_article = await uow.articles.create(results.article)
            saved_results["article"] = saved_article

        return saved_results

    @staticmethod
    async def process_raw_article(
        raw_article: RawArticle,
        client: AsyncIOMotorClient,
    ) -> dict:
        """
        Complete pipeline: generate objects from raw article and save to database.

        Args:
            raw_article: RawArticle object from news aggregator
            client: AsyncIOMotorClient instance for database connection

        Returns:
            Dictionary containing saved database objects with their IDs
        """
        results = await NLPModule.generate_all_from_article(raw_article)
        return await Pipeline.save_pipeline_results(results, client)


class PipelineOrchestrator:
    """
    Orchestrates fetching articles from news aggregators and processing them through the pipeline.
    Handles batch processing, error handling, and statistics tracking.
    """

    def __init__(
        self,
        news_aggregator: INewsAggregator,
        db_client: AsyncIOMotorClient,
    ):
        """
        Initialize the pipeline orchestrator.

        Args:
            news_aggregator: News aggregator instance for fetching articles
            db_client: Database client for saving processed results
        """
        self.news_aggregator = news_aggregator
        self.db_client = db_client

    async def process_article(self, raw_article: RawArticle) -> dict:
        """
        Process a single raw article through the pipeline.

        Args:
            raw_article: RawArticle from news aggregator

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing article: {raw_article.title[:50]}...")
            result = await Pipeline.process_raw_article(raw_article, self.db_client)
            logger.info(
                f"✓ Successfully processed. "
                f"Created {len(result.get('created_artists', []))} artists, "
                f"{len(result.get('created_groups', []))} groups"
            )
            return result
        except Exception as e:
            logger.error(f"x Failed to process '{raw_article.title[:50]}': {e}")
            raise

    async def fetch_and_store_articles(
        self,
        query_terms: List[str],
        concepts: bool = True,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        language: Optional[str] = "en",
        max_results: int = 100,
    ) -> dict:
        """
        Stage 1: Fetch articles from news aggregator and store in raw_articles collection.

        Returns:
            Dictionary with statistics about fetched and stored articles
        """
        # Default date range: last 7 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        logger.info(
            f"Fetching articles for {query_terms} from {start_date.date()} to {end_date.date()}"
        )

        # Fetch articles from news aggregator
        try:
            raw_articles = await self.news_aggregator.fetch_articles(
                query_terms=query_terms,
                concepts=concepts,
                start_date=start_date,
                end_date=end_date,
                language=language,
                max_results=max_results,
            )
            logger.info(f"Fetched {len(raw_articles)} articles from news aggregator")
        except Exception as e:
            logger.error(f"Failed to fetch articles: {e}")
            raise

        # Store articles in raw_articles collection
        from app.adapters.mongo_unit_of_work import MongoUnitOfWork

        stats = {"fetched": len(raw_articles), "stored": 0, "duplicates": 0}

        async with MongoUnitOfWork(self.db_client, use_transaction=False) as uow:
            for article in raw_articles:
                # Check if article already exists by URL
                existing = await uow.raw_articles.get_by_url(article.url)
                if existing:
                    stats["duplicates"] += 1
                    continue

                # Store raw article
                await uow.raw_articles.create(article)
                stats["stored"] += 1

        logger.info(
            f"Stored {stats['stored']} new articles, skipped {stats['duplicates']} duplicates"
        )
        return stats

    async def process_unprocessed_articles(
        self,
        batch_size: int = 10,
        limit: int = 100,
    ) -> dict:
        """
        Stage 2: Process unprocessed articles from raw_articles collection through the pipeline.

        Args:
            batch_size: Number of articles to process concurrently
            limit: Maximum number of articles to process

        Returns:
            Dictionary with statistics about processed articles
        """
        from app.adapters.mongo_unit_of_work import MongoUnitOfWork

        # Get unprocessed articles
        async with MongoUnitOfWork(self.db_client, use_transaction=False) as uow:
            raw_articles = await uow.raw_articles.get_unprocessed(limit=limit)

        logger.info(f"Found {len(raw_articles)} unprocessed articles")

        if not raw_articles:
            return {"processed": 0, "failed": 0}

        stats = {"processed": 0, "failed": 0, "failed_articles": []}

        # Process in batches
        for i in range(0, len(raw_articles), batch_size):
            batch = raw_articles[i : i + batch_size]
            logger.info(
                f"Processing batch {i // batch_size + 1} ({len(batch)} articles)..."
            )

            # Process batch concurrently
            tasks = [self.process_article(article) for article in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Update stats and mark articles as processed
            async with MongoUnitOfWork(self.db_client, use_transaction=False) as uow:
                for article, result in zip(batch, results):
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                        stats["failed_articles"].append(
                            {"title": article.title, "error": str(result)}
                        )
                    else:
                        stats["processed"] += 1
                        # Mark article as processed
                        await uow.raw_articles.mark_as_processed(str(article.id))

        logger.info(
            f"Completed processing: {stats['processed']} successful, {stats['failed']} failed"
        )
        return stats
