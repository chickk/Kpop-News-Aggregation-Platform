import asyncio
import logging
import re
from datetime import date, datetime, timedelta
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from app.interfaces.nlp_module import ArticlePipelineResult
from app.interfaces.news_aggregator import INewsAggregator
from app.adapters.mongo_unit_of_work import MongoUnitOfWork
from app.entity_aliases import (
    canonical_group_name,
    canonicalize_group_mentions,
    group_alias_candidates,
)
from app.entity_enrichment.resolver import WikiEntityResolver
from app.entity_enrichment.resolver import apply_group_enrichment
from app.models.articles import RawArticle
from app.models.groups import Group
from app.pipeline.generators import NLPModule

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pipeline:

    @staticmethod
    async def _get_group_by_alias(uow: MongoUnitOfWork, name: str):
        exact_filters = []
        for candidate in group_alias_candidates(name):
            exact_pattern = f"^{re.escape(candidate)}$"
            exact_filters.extend(
                [
                    {"name": {"$regex": exact_pattern, "$options": "i"}},
                    {"canonical_name": {"$regex": exact_pattern, "$options": "i"}},
                    {"aliases": {"$regex": exact_pattern, "$options": "i"}},
                ]
            )
        groups = await uow.groups.get_all(filters={"$or": exact_filters}, limit=1)
        if groups:
            return groups[0]
        return None

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
                    try:
                        saved_source = await uow.sources.create(results.source)
                    except DuplicateKeyError:
                        existing_source = await uow.sources.get_by_name(
                            results.source.name
                        )
                        if existing_source:
                            saved_source = existing_source
                        else:
                            raise
                saved_results["source"] = saved_source
                # Store a human-readable source label for article display.
                results.article.source_id = saved_source.name

            # Create Group, get group ids
            results.article.groups_mentioned = canonicalize_group_mentions(
                results.article.groups_mentioned
            )
            for group in results.new_groups:
                group.name = canonical_group_name(group.name)
                group.canonical_name = group.canonical_name or group.name

            group_name_to_id = {}
            entity_resolver = WikiEntityResolver()
            for group in results.new_groups:
                original_group_name = group.name
                existing_group = await Pipeline._get_group_by_alias(uow, group.name)
                if existing_group:
                    if entity_resolver.should_enrich_group(existing_group):
                        await entity_resolver.enrich_group(
                            existing_group,
                            original_group_name,
                        )
                        updated_group = await uow.groups.update(
                            str(existing_group.id),
                            existing_group,
                        )
                        if updated_group:
                            existing_group = updated_group
                    group_store = existing_group
                else:
                    await entity_resolver.enrich_group(group, original_group_name)
                    existing_group = await Pipeline._get_group_by_alias(uow, group.name)
                    if existing_group is None:
                        existing_group = (
                            await entity_resolver.find_existing_group_by_wikidata_id(
                                uow,
                                group.wikidata_id,
                            )
                        )
                    if existing_group:
                        group_store = existing_group
                    else:
                        group_store = await uow.groups.create(group)
                        saved_results["created_groups"].append(group_store)

                names_for_group = [
                    group.name,
                    original_group_name,
                    *getattr(group_store, "aliases", []),
                ]
                for name_for_group in names_for_group:
                    group_name_to_id[name_for_group] = group_store.id

                if any(
                    mentioned_name in results.article.groups_mentioned
                    for mentioned_name in names_for_group
                ):
                    group_id_str = str(group_store.id)
                    if group_id_str not in results.article.groups_mentioned_ids:
                        results.article.groups_mentioned_ids.append(group_id_str)

            for group_name in set(results.article.groups_mentioned):
                if group_name in group_name_to_id:
                    continue
                existing_group = await Pipeline._get_group_by_alias(uow, group_name)
                if existing_group:
                    if entity_resolver.should_enrich_group(existing_group):
                        await entity_resolver.enrich_group(existing_group, group_name)
                        updated_group = await uow.groups.update(
                            str(existing_group.id),
                            existing_group,
                        )
                        if updated_group:
                            existing_group = updated_group
                    group_name_to_id[group_name] = existing_group.id
                    group_id_str = str(existing_group.id)
                    if group_id_str not in results.article.groups_mentioned_ids:
                        results.article.groups_mentioned_ids.append(group_id_str)

            # Create artists and artist-group links
            artist_updates = []
            group_updates = {}
            artist_id_to_name = {}
            linked_artist_names = set()

            for artist in results.new_artists:
                original_artist_name = artist.name
                group_candidate = await entity_resolver.resolve_group(original_artist_name)
                if group_candidate is not None:
                    candidate_group = Group(
                        name=original_artist_name,
                        bio=f"{original_artist_name} was mentioned in recent music news coverage.",
                        formed=(
                            results.article.publication_date.date()
                            if results.article.publication_date
                            else date.today()
                        ),
                        is_active=True,
                        disbanded=None,
                        language=[results.article.language],
                        countries=results.article.countries,
                        tags=[],
                        member_artists=[],
                        artist_ids=[],
                    )
                    apply_group_enrichment(
                        candidate_group,
                        group_candidate,
                        original_artist_name,
                    )
                    existing_group = await Pipeline._get_group_by_alias(
                        uow,
                        candidate_group.name,
                    )
                    if existing_group is None:
                        existing_group = (
                            await entity_resolver.find_existing_group_by_wikidata_id(
                                uow,
                                candidate_group.wikidata_id,
                            )
                        )
                    if existing_group:
                        group_store = existing_group
                    else:
                        group_store = await uow.groups.create(candidate_group)
                        saved_results["created_groups"].append(group_store)

                    group_id_str = str(group_store.id)
                    if group_id_str not in results.article.groups_mentioned_ids:
                        results.article.groups_mentioned_ids.append(group_id_str)
                    if group_store.name not in results.article.groups_mentioned:
                        results.article.groups_mentioned.append(group_store.name)
                    group_name_to_id[group_store.name] = group_store.id
                    linked_artist_names.add(original_artist_name)
                    continue

                existing_artist = await entity_resolver.find_existing_artist(
                    uow,
                    artist.name,
                )
                if existing_artist:
                    if entity_resolver.should_enrich_artist(existing_artist):
                        await entity_resolver.enrich_artist(
                            existing_artist,
                            original_artist_name,
                        )
                        updated_artist = await uow.artists.update(
                            str(existing_artist.id),
                            existing_artist,
                        )
                        if updated_artist:
                            existing_artist = updated_artist
                    artist_store = existing_artist
                else:
                    await entity_resolver.enrich_artist(artist, original_artist_name)
                    existing_artist = await entity_resolver.find_existing_artist(
                        uow,
                        artist.name,
                    )
                    if existing_artist is None:
                        existing_artist = (
                            await entity_resolver.find_existing_artist_by_wikidata_id(
                                uow,
                                artist.wikidata_id,
                            )
                        )
                    if existing_artist:
                        artist_store = existing_artist
                    else:
                        artist_store = await uow.artists.create(artist)
                        saved_results["created_artists"].append(artist_store)

                artist_id_str = str(artist_store.id)
                artist_id_to_name[artist_id_str] = artist_store.name
                if artist_id_str not in results.article.artists_mentioned_ids:
                    results.article.artists_mentioned_ids.append(artist_id_str)
                linked_artist_names.update(
                    {
                        artist.name,
                        original_artist_name,
                        *getattr(artist_store, "aliases", []),
                    }
                )

                membership_group_ids = []
                for member_group_wikidata_id in getattr(
                    artist_store,
                    "member_of_wikidata_ids",
                    [],
                ):
                    member_group = await entity_resolver.find_existing_group_by_wikidata_id(
                        uow,
                        member_group_wikidata_id,
                    )
                    if member_group:
                        membership_group_ids.append(member_group.id)
                        member_group_name = getattr(member_group, "name", "")
                        if member_group_name and member_group_name not in artist_store.group_names:
                            artist_store.group_names.append(member_group_name)

                if membership_group_ids:
                    artist_needs_update = False
                    for group_id in membership_group_ids:
                        group_id_str = str(group_id)
                        if group_id_str not in artist_store.group_ids:
                            artist_store.group_ids.append(group_id_str)
                            artist_needs_update = True
                        if group_id not in group_updates:
                            group_updates[group_id] = []
                        if artist_id_str not in group_updates[group_id]:
                            group_updates[group_id].append(artist_id_str)
                    if artist_needs_update:
                        artist_updates.append(artist_store)

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

            for artist_name in set(results.article.artists_mentioned):
                if artist_name in linked_artist_names:
                    continue
                existing_artist = await uow.artists.get_by_name(artist_name)
                if existing_artist:
                    if entity_resolver.should_enrich_artist(existing_artist):
                        await entity_resolver.enrich_artist(existing_artist, artist_name)
                        updated_artist = await uow.artists.update(
                            str(existing_artist.id),
                            existing_artist,
                        )
                        if updated_artist:
                            existing_artist = updated_artist
                    artist_id_str = str(existing_artist.id)
                    if artist_id_str not in results.article.artists_mentioned_ids:
                        results.article.artists_mentioned_ids.append(artist_id_str)

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
                        artist_name = artist_id_to_name.get(artist_id)
                        if artist_name and artist_name not in group.member_artists:
                            group.member_artists.append(artist_name)
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
        # Check for duplicate content BEFORE running expensive NLP pipeline
        async with MongoUnitOfWork(client, use_transaction=False) as uow:
            if await uow.articles.exact_article_exists(raw_article.text):
                logger.info(f"Skipping duplicate article: {raw_article.title[:50]}...")
                return {
                    "article": None,
                    "source": None,
                    "created_artists": [],
                    "created_groups": [],
                    "skipped": True,
                }

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
                        # Check if article was skipped due to duplicate
                        if isinstance(result, dict) and result.get("skipped"):
                            logger.info(f"Marking skipped duplicate as processed: {article.title[:50]}...")
                        stats["processed"] += 1
                        # Mark article as processed (whether created or skipped as duplicate)
                        await uow.raw_articles.mark_as_processed(str(article.id))

        logger.info(
            f"Completed processing: {stats['processed']} successful, {stats['failed']} failed"
        )
        return stats
