from fastapi import FastAPI, Query, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, List, AsyncGenerator
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timedelta
from pydantic import ValidationError
from pymongo.errors import PyMongoError, DuplicateKeyError, ConnectionFailure
import asyncio
import logging
import os
import re


from app.article_search import (
    article_matches_primary_terms,
    build_article_search_filter,
    build_case_insensitive_tags_filter,
    build_news_fetch_plans,
    processed_article_matches_primary_terms,
    resolve_auto_process_concurrency,
    resolve_auto_process_limit,
    should_auto_fetch_articles,
    sort_articles_by_relevance,
    split_search_terms,
)
from app.entity_aliases import (
    dedupe_artists_by_identity,
    dedupe_groups_by_canonical_name,
    group_alias_candidates,
)
from app.interfaces.query_params import (
    ArtistFilters,
    ContentFilters,
    GroupFilters,
    SourceFilters,
)
from app.interfaces.pipeline_requests import (
    FetchArticlesRequest,
    FetchArticlesResponse,
    ProcessArticlesRequest,
    ProcessArticlesResponse,
    RunFullPipelineRequest,
    FullPipelineResponse,
)
from app.models.articles import Article
from app.models.artists import Artist
from app.models.events import Event
from app.models.groups import Group
from app.models.sources import Source

from app.data_layer.schemas import Event_db, Article_db

from app.interfaces.unit_of_work import IUnitOfWork
from app.adapters.mongo_unit_of_work import MongoUnitOfWork
from app.data_layer.mongo_database import init_db
from app.pipeline.pipeline import Pipeline, PipelineOrchestrator
from app.pipeline.llm_modules.config import setup_dspy
from app.news_aggregators.news_api import NewsAPIAggregator
import dspy


logger = logging.getLogger(__name__)


# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup... Initializing database connections...")
    URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/idolTracker")

    # Initialize and obtain client
    db_client = await init_db(URI=URI)

    # Store the client in app.state so that it can be used in requests.
    app.state.db_client = db_client

    # Initialize DSPy for pipeline
    print("Initializing DSPy for pipeline...")
    nlp_provider = os.getenv("NLP_PROVIDER", "groq").strip().lower()
    provider_config = {
        "openai": {
            "api_key_env": "OPEN_AI_KEY",
            "litellm_key_env": "OPENAI_API_KEY",
            "default_model": "openai/gpt-4o-mini",
            "default_max_tokens": 256,
        },
        "gemini": {
            "api_key_env": "GEMINI_API_KEY",
            "litellm_key_env": "GEMINI_API_KEY",
            "default_model": "gemini/gemini-2.5-flash-lite",
            "default_max_tokens": 768,
        },
        "groq": {
            "api_key_env": "GROQ_API_KEY",
            "litellm_key_env": "GROQ_API_KEY",
            "default_model": "groq/llama-3.1-8b-instant",
            "default_max_tokens": 256,
        },
    }
    llm_config = provider_config.get(nlp_provider)

    if llm_config:
        llm_key = os.getenv(llm_config["api_key_env"])
    else:
        llm_key = None
        print(
            f"Warning: unsupported NLP_PROVIDER={nlp_provider!r}. "
            "Pipeline endpoints will not work."
        )

    if llm_config and llm_key:
        os.environ[llm_config["litellm_key_env"]] = llm_key
        llm_model = os.getenv("LLM_MODEL") or llm_config["default_model"]
        configured_max_tokens = os.getenv("LLM_MAX_TOKENS")
        llm_max_tokens = (
            int(configured_max_tokens)
            if configured_max_tokens is not None and configured_max_tokens.strip()
            else llm_config.get("default_max_tokens", 8000)
        )
        llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
        lm = setup_dspy(
            model=llm_model,
            api_key=llm_key,
            max_tokens=llm_max_tokens,
            temperature=llm_temperature,
        )
        dspy.configure(lm=lm)
        print(f"DSPy configured successfully with {nlp_provider}:{llm_model}")
    elif llm_config:
        print(
            f"Warning: {llm_config['api_key_env']} not found. "
            "Pipeline endpoints will not work."
        )

    # Initialize News Aggregator
    news_api_key = os.getenv("NEWS_API_KEY")
    if news_api_key:
        app.state.news_aggregator = NewsAPIAggregator(apiKey=news_api_key)
        print("News aggregator initialized")
    else:
        print("Warning: NEWS_API_KEY not found. Pipeline endpoints will not work.")

    yield

    # --- Code executed when the application closes ---
    print("Application closed... Database connection closed...")
    if hasattr(app.state, "db_client") and app.state.db_client:
        app.state.db_client.close()


# --- Pass Lifespan to FastAPI ---
app = FastAPI(
    title="Idol Tracker API",
    description="An API for managing articles, events, and artists.",
    lifespan=lifespan,
)

default_origins = [
    "http://localhost",
    "http://localhost:5001",
    "http://localhost:5173",
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]
origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(default_origins)).split(",")
    if origin.strip()
]
allow_all_origins = "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Unit of Work Dependency Injection ---
async def get_uow(request: Request) -> AsyncGenerator[IUnitOfWork, None]:
    """
    Get the database client from app.state and build UoW.
    """
    # Get the client from the application state.
    db_client: AsyncIOMotorClient = getattr(request.app.state, "db_client", None)

    if not db_client:
        raise HTTPException(
            status_code=500, detail="The database client has not yet been initialized."
        )

    use_transaction = False

    # Create Unit of Work
    uow = MongoUnitOfWork(db_client, use_transaction=use_transaction)

    async with uow:
        yield uow


# --- Pipeline Orchestrator Dependency Injection ---
def get_pipeline_orchestrator(request: Request) -> PipelineOrchestrator:
    """
    Get the pipeline orchestrator with news aggregator and database client.
    """
    db_client: AsyncIOMotorClient = getattr(request.app.state, "db_client", None)
    news_aggregator = getattr(request.app.state, "news_aggregator", None)

    if not db_client:
        raise HTTPException(
            status_code=500, detail="the database client has not yet been initialized."
        )

    if not news_aggregator:
        raise HTTPException(
            status_code=500,
            detail="The news aggregator has not been initialized. Check NEWS_API_KEY environment variable.",
        )

    return PipelineOrchestrator(news_aggregator=news_aggregator, db_client=db_client)


# --- API router ---
@app.get("/health")
async def get_health():
    return {"status": "ok"}


@app.get("/")
async def get_root():
    return {"Response": "Welcome To Idol Tracker"}


async def _auto_fetch_articles_for_search(
    request: Request,
    search: str,
    limit: int,
    uow: IUnitOfWork,
    start_date=None,
    end_date=None,
) -> int:
    news_aggregator = getattr(request.app.state, "news_aggregator", None)
    if news_aggregator is None:
        return 0

    search_terms = split_search_terms(search)
    if not search_terms:
        return 0

    if end_date is None:
        end_date = datetime.now()
    user_provided_start_date = start_date is not None
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    max_results = min(int(os.getenv("NEWS_AUTO_FETCH_MAX_RESULTS", "25")), max(limit, 1))
    process_limit = resolve_auto_process_limit(
        page_limit=limit,
        max_fetch_results=max_results,
        configured_limit=os.getenv("NEWS_AUTO_PROCESS_MAX_RESULTS"),
    )
    process_concurrency = resolve_auto_process_concurrency(
        os.getenv("NEWS_AUTO_PROCESS_CONCURRENCY")
    )
    language = os.getenv("NEWS_AUTO_FETCH_LANGUAGE", "eng")

    fetch_plans = build_news_fetch_plans(search_terms)

    async def fetch_matching_articles(fetch_start_date):
        async def fetch_for_plan(fetch_plan):
            raw_articles = await news_aggregator.fetch_articles(
                query_terms=fetch_plan["query_terms"],
                concepts=fetch_plan["concepts"],
                start_date=fetch_start_date,
                end_date=end_date,
                language=language,
                max_results=max_results,
                keyword_loc=fetch_plan.get("keyword_locs", "body"),
                sort_by=fetch_plan["sort_by"],
            )
            if fetch_plan["concepts"]:
                return raw_articles
            return [
                raw_article
                for raw_article in raw_articles
                if article_matches_primary_terms(raw_article, search_terms)
            ]

        article_batches = await asyncio.gather(
            *(fetch_for_plan(fetch_plan) for fetch_plan in fetch_plans)
        )
        return [
            raw_article
            for article_batch in article_batches
            for raw_article in article_batch
        ]

    raw_articles = []
    seen_urls = set()
    for raw_article in await fetch_matching_articles(start_date):
        if raw_article.url in seen_urls:
            continue
        raw_articles.append(raw_article)
        seen_urls.add(raw_article.url)

    if not raw_articles and not user_provided_start_date:
        fallback_days = int(os.getenv("NEWS_AUTO_FETCH_FALLBACK_DAYS", "30"))
        fallback_start_date = end_date - timedelta(days=fallback_days)
        for raw_article in await fetch_matching_articles(fallback_start_date):
            if raw_article.url in seen_urls:
                continue
            raw_articles.append(raw_article)
            seen_urls.add(raw_article.url)

    raw_articles = sort_articles_by_relevance(raw_articles, search_terms)

    raw_articles_to_process = []
    attempted_llm_count = 0
    for raw_article in raw_articles:
        try:
            existing_raw = await uow.raw_articles.get_by_url(raw_article.url)
            if existing_raw is None:
                existing_raw = await uow.raw_articles.create(raw_article)

            if existing_raw.processed:
                continue

            if await uow.articles.exact_article_exists(raw_article.text):
                await uow.raw_articles.mark_as_processed(str(existing_raw.id))
                continue

            if attempted_llm_count >= process_limit:
                break
            attempted_llm_count += 1
            raw_articles_to_process.append(existing_raw)
        except DuplicateKeyError:
            continue
        except Exception as e:
            logger.warning(
                "Auto-fetch raw article staging failed for %r; leaving article unprocessed: %s",
                raw_article.title,
                e,
            )
            continue

    semaphore = asyncio.Semaphore(process_concurrency)

    async def process_existing_raw(existing_raw):
        async with semaphore:
            try:
                result = await Pipeline.process_raw_article(
                    existing_raw,
                    request.app.state.db_client,
                )
                async with MongoUnitOfWork(
                    request.app.state.db_client, use_transaction=False
                ) as mark_uow:
                    await mark_uow.raw_articles.mark_as_processed(str(existing_raw.id))
                return result
            except DuplicateKeyError:
                async with MongoUnitOfWork(
                    request.app.state.db_client, use_transaction=False
                ) as mark_uow:
                    await mark_uow.raw_articles.mark_as_processed(str(existing_raw.id))
                return {"skipped": True}
            except Exception as e:
                logger.warning(
                    "Auto-fetch LLM processing failed for %r; leaving raw article unprocessed: %s",
                    existing_raw.title,
                    e,
                )
                return e

    if not raw_articles_to_process:
        return 0

    results = await asyncio.gather(
        *(process_existing_raw(existing_raw) for existing_raw in raw_articles_to_process)
    )
    processed_count = sum(
        1
        for result in results
        if isinstance(result, dict) and not result.get("skipped")
    )
    return processed_count


@app.get("/api/content/latest", response_model=List[Article])
async def get_latest_content(uow: IUnitOfWork = Depends(get_uow)):
    """
    Get the latest articles from the database.
    """
    try:
        articles_db = await uow.articles.get_all(limit=10)
        return articles_db
    except ConnectionFailure as e:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/content/test-article", response_model=Article, status_code=201)
async def create_test_article(article: Article, uow: IUnitOfWork = Depends(get_uow)):
    try:
        groups_ids = article.groups_mentioned_ids
        artists_ids = article.artists_mentioned_ids

        # Turn publication_date to datetime
        pub_date = article.publication_date
        if isinstance(pub_date, str):
            pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))

        # Create Beanie DB model
        article_db = Article_db(
            **article.model_dump(
                exclude={
                    "groups_mentioned_ids",
                    "artists_mentioned_ids",
                    "publication_date",
                }
            ),
            groups_mentioned_ids=groups_ids,
            artists_mentioned_ids=artists_ids,
            publication_date=pub_date,
        )

        # Save to DB
        created_article = await uow.articles.create(article_db)

        return created_article
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Article already exists")
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/events/merge", response_model=Event, status_code=201)
async def merge_articles_to_event(event: Event, uow: IUnitOfWork = Depends(get_uow)):
    """
    Create a new event and store it in the database.
    """
    try:
        event_db = Event_db(**event.model_dump())
        created_event = await uow.events.create(event_db)
        return created_event
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Event already exists")
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/content", response_model=List[Article])
async def list_content(
    request: Request,
    filter_query: Annotated[ContentFilters, Query()],
    uow: IUnitOfWork = Depends(get_uow),
):
    """
    Get articles with optional filters for source, artist, group, event, tags, date range, and text search.
    """
    try:
        query_filters = {}

        if filter_query.source_id != None:
            query_filters["source_id"] = filter_query.source_id

        if filter_query.artist_id != None:
            query_filters["artists_mentioned_ids"] = filter_query.artist_id

        if filter_query.group_id != None:
            query_filters["groups_mentioned_ids"] = filter_query.group_id

        if filter_query.event_id != None:
            query_filters["event_id"] = filter_query.event_id

        if len(filter_query.tags) > 0:
            query_filters.update(build_case_insensitive_tags_filter(filter_query.tags))

        if filter_query.from_date != None or filter_query.to_date != None:
            date_filter = {}
            if filter_query.from_date != None:
                date_filter["$gte"] = datetime.combine(
                    filter_query.from_date, datetime.min.time()
                )
            if filter_query.to_date != None:
                date_filter["$lte"] = datetime.combine(
                    filter_query.to_date, datetime.max.time()
                )
            query_filters["publication_date"] = date_filter

        if filter_query.search != None:
            query_filters.update(build_article_search_filter(filter_query.search))

        articles_db = await uow.articles.get_all(
            filters=query_filters, limit=filter_query.limit, skip=filter_query.skip
        )
        search_terms = (
            split_search_terms(filter_query.search)
            if filter_query.search is not None
            else []
        )
        if search_terms:
            articles_db = [
                article
                for article in articles_db
                if processed_article_matches_primary_terms(article, search_terms)
            ]

        should_auto_fetch = should_auto_fetch_articles(
            search=filter_query.search,
            skip=filter_query.skip,
            current_count=len(articles_db),
            limit=filter_query.limit,
            has_date_range=(
                filter_query.from_date is not None or filter_query.to_date is not None
            ),
            max_fetch_results=int(os.getenv("NEWS_AUTO_FETCH_MAX_RESULTS", "25")),
        )
        if should_auto_fetch:
            await _auto_fetch_articles_for_search(
                request=request,
                search=filter_query.search,
                limit=filter_query.limit,
                uow=uow,
                start_date=(
                    datetime.combine(filter_query.from_date, datetime.min.time())
                    if filter_query.from_date
                    else None
                ),
                end_date=(
                    datetime.combine(filter_query.to_date, datetime.max.time())
                    if filter_query.to_date
                    else None
                ),
            )
            articles_db = await uow.articles.get_all(
                filters=query_filters, limit=filter_query.limit, skip=filter_query.skip
            )
            articles_db = [
                article
                for article in articles_db
                if processed_article_matches_primary_terms(article, search_terms)
            ]

        return articles_db
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid filter parameters: {str(e)}"
        )
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/content/{id}", response_model=Article)
async def get_article(id: str, uow: IUnitOfWork = Depends(get_uow)):
    """Gets article by id"""
    try:
        article = await uow.articles.get_by_id(id=id)
        if article is None:
            raise HTTPException(
                status_code=404, detail=f"Article with id '{id}' not found"
            )
        return article
    except HTTPException:
        raise
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/artists", response_model=List[Artist])
async def list_artists(
    filter_query: Annotated[ArtistFilters, Query()],
    uow: IUnitOfWork = Depends(get_uow),
):
    """
    Get artists with optional filters for name, country, tags, group membership, and active status.
    """
    try:
        query_filters = {}
        query_filters["entity_type"] = {"$nin": ["group", "invalid"]}

        if filter_query.name != None:
            name_pattern = re.escape(filter_query.name)
            query_filters["$or"] = [
                {"name": {"$regex": name_pattern, "$options": "i"}},
                {"canonical_name": {"$regex": name_pattern, "$options": "i"}},
                {"aliases": {"$regex": name_pattern, "$options": "i"}},
            ]

        if filter_query.country != None:
            query_filters["countries"] = filter_query.country

        if len(filter_query.tags) > 0:
            query_filters.update(build_case_insensitive_tags_filter(filter_query.tags))

        if filter_query.group_id != None:
            query_filters["group_ids"] = ObjectId(filter_query.group_id)

        if filter_query.get_active != None:
            query_filters["is_active"] = filter_query.get_active

        artists_db = await uow.artists.get_all(
            filters=query_filters, limit=filter_query.limit, skip=filter_query.skip
        )

        return dedupe_artists_by_identity(artists_db)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid filter parameters: {str(e)}"
        )
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/artists/{id}", response_model=Artist)
async def get_artist(id: str, uow: IUnitOfWork = Depends(get_uow)):
    """Gets artist by id"""
    try:
        artist = await uow.artists.get_by_id(id=id)
        if artist is None:
            raise HTTPException(
                status_code=404, detail=f"Artist with id '{id}' not found"
            )
        return artist
    except HTTPException:
        raise
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/groups", response_model=List[Group])
async def list_groups(
    filter_query: Annotated[GroupFilters, Query()],
    uow: IUnitOfWork = Depends(get_uow),
):
    """
    Get groups with optional filters for name, country, tags, artist membership, and active status.
    """
    try:
        query_filters = {}

        if filter_query.name != None:
            aliases = group_alias_candidates(filter_query.name)
            if len(aliases) > 1:
                alias_filters = []
                for alias in aliases:
                    exact_pattern = f"^{re.escape(alias)}$"
                    alias_filters.extend(
                        [
                            {"name": {"$regex": exact_pattern, "$options": "i"}},
                            {"canonical_name": {"$regex": exact_pattern, "$options": "i"}},
                            {"aliases": {"$regex": exact_pattern, "$options": "i"}},
                        ]
                    )
                query_filters["$or"] = alias_filters
            else:
                name_pattern = re.escape(filter_query.name)
                query_filters["$or"] = [
                    {"name": {"$regex": name_pattern, "$options": "i"}},
                    {"canonical_name": {"$regex": name_pattern, "$options": "i"}},
                    {"aliases": {"$regex": name_pattern, "$options": "i"}},
                ]

        if filter_query.country != None:
            query_filters["countries"] = filter_query.country

        if len(filter_query.tags) > 0:
            query_filters.update(build_case_insensitive_tags_filter(filter_query.tags))

        if filter_query.artist_id != None:
            query_filters["artist_ids"] = ObjectId(filter_query.artist_id)

        if filter_query.get_active != None:
            query_filters["is_active"] = filter_query.get_active

        groups_db = await uow.groups.get_all(
            filters=query_filters, limit=filter_query.limit, skip=filter_query.skip
        )

        return dedupe_groups_by_canonical_name(groups_db)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid filter parameters: {str(e)}"
        )
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/group/{id}", response_model=Group)
async def get_group(id: str, uow: IUnitOfWork = Depends(get_uow)):
    """Gets group by id"""
    try:
        group = await uow.groups.get_by_id(id=id)
        if group is None:
            raise HTTPException(
                status_code=404, detail=f"Group with id '{id}' not found"
            )
        return group
    except HTTPException:
        raise
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/sources", response_model=List[Source])
async def list_sources(
    filter_query: Annotated[SourceFilters, Query()],
    uow: IUnitOfWork = Depends(get_uow),
):
    """
    Get sources with optional filters for name, country, tags, and language.
    """
    try:
        query_filters = {}

        if filter_query.name != None:
            query_filters["name"] = {"$regex": filter_query.name, "$options": "i"}

        if filter_query.country != None:
            query_filters["countries"] = filter_query.country

        if len(filter_query.tags) > 0:
            query_filters.update(build_case_insensitive_tags_filter(filter_query.tags))

        if filter_query.language != None:
            query_filters["language"] = filter_query.language

        sources_db = await uow.sources.get_all(
            filters=query_filters, limit=filter_query.limit, skip=filter_query.skip
        )

        return sources_db
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid filter parameters: {str(e)}"
        )
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/source/{id}", response_model=Source)
async def get_source(id: str, uow: IUnitOfWork = Depends(get_uow)):
    """Gets source by id"""
    try:
        source = await uow.sources.get_by_id(id=id)
        if source is None:
            raise HTTPException(
                status_code=404, detail=f"Source with id '{id}' not found"
            )
        return source
    except HTTPException:
        raise
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# --- Pipeline Endpoints ---


@app.post("/api/pipeline/fetch", response_model=FetchArticlesResponse, status_code=202)
async def fetch_articles(
    request: FetchArticlesRequest,
    orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator),
):
    """
    Stage 1: Fetch articles from news sources and store them in the raw_articles collection.

    This endpoint fetches articles based on query terms and stores them for later processing.
    Articles are not processed through the NLP pipeline yet - use the process endpoint for that.
    """
    try:
        stats = await orchestrator.fetch_and_store_articles(
            query_terms=request.query_terms,
            concepts=request.concepts,
            start_date=request.start_date,
            end_date=request.end_date,
            language=request.language,
            max_results=request.max_results,
        )

        return FetchArticlesResponse(
            success=True,
            message=f"Successfully fetched {stats['fetched']} articles, stored {stats['stored']} new articles",
            fetched=stats["fetched"],
            stored=stats["stored"],
            duplicates=stats["duplicates"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/pipeline/process", response_model=ProcessArticlesResponse, status_code=202)
async def process_articles(
    request: ProcessArticlesRequest,
    orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator),
):
    """
    Stage 2: Process unprocessed articles through the NLP pipeline.

    This endpoint takes articles from the raw_articles collection that haven't been processed yet
    and runs them through the full NLP pipeline to extract entities, generate summaries, etc.
    """
    try:
        stats = await orchestrator.process_unprocessed_articles(
            batch_size=request.batch_size,
            limit=request.limit,
        )

        return ProcessArticlesResponse(
            success=True,
            message=f"Successfully processed {stats['processed']} articles, {stats['failed']} failed",
            processed=stats["processed"],
            failed=stats["failed"],
            failed_articles=stats.get("failed_articles", []),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/pipeline/run", response_model=FullPipelineResponse, status_code=202)
async def run_full_pipeline(
    request: RunFullPipelineRequest,
    orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator),
):
    """
    Run the complete pipeline: fetch articles AND process them.

    This is a convenience endpoint that combines both stages:
    1. Fetch articles from news sources based on query terms
    2. Process the fetched articles through the NLP pipeline

    Use this for a complete end-to-end pipeline run.
    """
    try:
        # Stage 1: Fetch articles
        fetch_stats = await orchestrator.fetch_and_store_articles(
            query_terms=request.query_terms,
            concepts=request.concepts,
            start_date=request.start_date,
            end_date=request.end_date,
            language=request.language,
            max_results=request.max_results,
        )

        # Stage 2: Process articles
        process_limit = request.process_limit or fetch_stats["stored"]
        process_stats = await orchestrator.process_unprocessed_articles(
            batch_size=request.batch_size,
            limit=process_limit,
        )

        return FullPipelineResponse(
            success=True,
            message=f"Pipeline complete: fetched {fetch_stats['stored']} new articles, processed {process_stats['processed']} articles",
            fetch_stats=fetch_stats,
            process_stats=process_stats,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
