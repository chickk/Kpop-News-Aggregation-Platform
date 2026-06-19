import hashlib
import logging
import os
from datetime import date
from typing import List, Optional

from app.article_search import article_from_raw_article
from app.entity_aliases import canonical_group_name, canonicalize_group_mentions
from app.interfaces.nlp_module import ArticlePipelineResult, iNLPModule
from app.models.articles import Article, ArticleExtract, RawArticle
from app.models.artists import Artist
from app.models.events import Event
from app.models.groups import Group
from app.models.sources import RawSource, Source
from app.pipeline.llm_modules.modules import (
    ArticleExtractor,
    ArtistExtractor,
    EventExtractor,
    GroupExtractor,
    SourceExtractor,
)
from app.pipeline.llm_modules.signatures import ArticleInput, ArtistInput, GroupInput


logger = logging.getLogger(__name__)


class NLPModule(iNLPModule):
    """Implementation of iNLPModule for performing NLP tasks using LLM extractors"""

    _artist_extractor: Optional[ArtistExtractor] = None
    _article_extractor: Optional[ArticleExtractor] = None
    _group_extractor: Optional[GroupExtractor] = None
    _source_extractor: Optional[SourceExtractor] = None
    _event_extractor: Optional[EventExtractor] = None
    _article_extract_cache: dict[str, ArticleExtract] = {}

    @staticmethod
    def _nlp_mode() -> str:
        return os.getenv("NLP_MODE", "cheap").strip().lower()

    @staticmethod
    def _article_max_chars() -> int:
        return int(os.getenv("NLP_ARTICLE_MAX_CHARS", "800"))

    @staticmethod
    def _allow_rule_fallback() -> bool:
        return os.getenv("NLP_ALLOW_RULE_FALLBACK", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }

    @staticmethod
    def _article_cache_key(raw_article: RawArticle, article_text: str) -> str:
        provider = os.getenv("NLP_PROVIDER", "groq")
        model = os.getenv("LLM_MODEL", "")
        mode = NLPModule._nlp_mode()
        schema_version = "article_extract:v1"
        cache_input = "\n".join(
            [
                schema_version,
                mode,
                provider,
                model,
                raw_article.title,
                article_text,
            ]
        )
        return hashlib.sha256(cache_input.encode()).hexdigest()

    @staticmethod
    def _article_from_extract(
        raw_article: RawArticle,
        article_extract: ArticleExtract,
    ) -> Article:
        sentiment = NLPModule._adjust_neutral_sentiment(
            article_extract.sentiment,
            raw_article,
        )
        return Article(
            summary=article_extract.summary,
            sentiment=sentiment,
            artists_mentioned=article_extract.artists_mentioned,
            groups_mentioned=canonicalize_group_mentions(article_extract.groups_mentioned),
            tags=article_extract.tags,
            countries=article_extract.countries,
            title=raw_article.title,
            author=raw_article.author,
            source_id="",  # Will be set when source is saved
            publication_date=raw_article.publication_date,
            text=raw_article.text,
            images=raw_article.image_urls,
            video=raw_article.video_url,
            language=raw_article.language or "en",
            url=raw_article.url,
            groups_mentioned_ids=[],
            artists_mentioned_ids=[],
        )

    @staticmethod
    def _adjust_neutral_sentiment(sentiment: float, raw_article: RawArticle) -> float:
        if abs(sentiment - 0.5) > 0.001:
            return max(0.0, min(1.0, sentiment))

        text = f"{raw_article.title} {raw_article.text}".lower()
        negative_terms = {
            "back pain",
            "breakdown",
            "concern",
            "controversy",
            "crying",
            "health condition",
            "injury",
            "pain",
            "tears",
            "worried",
        }
        positive_terms = {
            "ambassador",
            "appointed",
            "award",
            "comeback",
            "reassures",
            "recovered",
            "success",
            "win",
        }
        negative_score = sum(1 for term in negative_terms if term in text)
        positive_score = sum(1 for term in positive_terms if term in text)
        if negative_score > positive_score:
            return 0.35
        if positive_score > negative_score:
            return 0.65
        return sentiment

    @staticmethod
    def _source_from_raw_source(raw_source: RawSource) -> Source:
        countries = [raw_source.country_code.upper()] if raw_source.country_code else []
        bio = raw_source.description or f"{raw_source.title} is a news source."
        return Source(
            name=raw_source.title,
            bio=bio,
            formed=None,
            language="en",
            countries=countries,
            tags=["news"],
        )

    @staticmethod
    def _placeholder_date(raw_article: RawArticle) -> date:
        if raw_article.publication_date:
            return raw_article.publication_date.date()
        return date.today()

    @staticmethod
    def _artist_from_mention(
        name: str,
        article: Article,
        raw_article: RawArticle,
    ) -> Artist:
        return Artist(
            name=name,
            bio=f"{name} was mentioned in recent music news coverage.",
            career_start=NLPModule._placeholder_date(raw_article),
            is_active=True,
            retirement_date=None,
            in_groups=False,
            group_names=[],
            language=article.language,
            countries=article.countries,
            tags=article.tags,
            group_ids=[],
        )

    @staticmethod
    def _group_from_mention(
        name: str,
        article: Article,
        raw_article: RawArticle,
    ) -> Group:
        canonical_name = canonical_group_name(name)
        return Group(
            name=canonical_name,
            bio=f"{canonical_name} was mentioned in recent music news coverage.",
            formed=NLPModule._placeholder_date(raw_article),
            is_active=True,
            disbanded=None,
            language=[article.language],
            countries=article.countries,
            tags=article.tags,
            member_artists=[],
            artist_ids=[],
        )

    @classmethod
    def _get_artist_extractor(cls) -> ArtistExtractor:
        if cls._artist_extractor is None:
            cls._artist_extractor = ArtistExtractor()
        return cls._artist_extractor

    @classmethod
    def _get_article_extractor(cls) -> ArticleExtractor:
        if cls._article_extractor is None:
            cls._article_extractor = ArticleExtractor()
        return cls._article_extractor

    @classmethod
    def _get_group_extractor(cls) -> GroupExtractor:
        if cls._group_extractor is None:
            cls._group_extractor = GroupExtractor()
        return cls._group_extractor

    @classmethod
    def _get_source_extractor(cls) -> SourceExtractor:
        if cls._source_extractor is None:
            cls._source_extractor = SourceExtractor()
        return cls._source_extractor

    @classmethod
    def _get_event_extractor(cls) -> EventExtractor:
        if cls._event_extractor is None:
            cls._event_extractor = EventExtractor()
        return cls._event_extractor

    @staticmethod
    async def create_artist(name: str, group_membership: List[str] = []) -> Artist:
        """Generate an Artist object using their name and a list of groups they're apart of"""
        from app.pipeline.llm_modules.signatures import ArtistInput

        # Create ArtistInput object
        artist_input = ArtistInput(artist_name=name, artist_groups=group_membership)

        extractor = NLPModule._get_artist_extractor()
        results = await extractor.aforward(artist=artist_input)
        artist_generated = results.artist_output

        # Combine generated fields with artist name to create full Artist
        artist = Artist(
            **artist_generated.model_dump(),
            name=name,
            group_ids=[],
        )
        return artist

    @staticmethod
    async def create_group(name: str, group_members: List[str] = []) -> Group:
        """Create a group using names and member artists"""
        name = canonical_group_name(name)
        group_input = GroupInput(group_name=name, artists_in_group=group_members)
        extractor = NLPModule._get_group_extractor()
        results = await extractor.aforward(group=group_input)
        group_generated = results.group_output

        # Combine generated fields with group name to create full Group
        group = Group(
            **group_generated.model_dump(),
            name=name,
            artist_ids=[],  # Will be populated when artists are saved
        )
        return group

    @staticmethod
    async def create_event(articles: List[Article], events: List[Event] = []) -> Event:
        """Create an event using a list of articles or events, or both"""
        extractor = NLPModule._get_event_extractor()
        results = await extractor.aforward(articles=articles, events=events)
        return results.event_output

    @staticmethod
    async def create_article(raw_article: RawArticle) -> Article:
        """Create an article using the response fields from the news aggregator"""
        max_chars = NLPModule._article_max_chars()
        article_text = raw_article.text[:max_chars]
        article = ArticleInput(
            article_title=raw_article.title, article_text=article_text
        )
        cache_key = NLPModule._article_cache_key(raw_article, article_text)

        try:
            cached_extract = NLPModule._article_extract_cache.get(cache_key)
            if cached_extract is not None:
                article_extract = cached_extract.model_copy(deep=True)
            else:
                extractor = NLPModule._get_article_extractor()
                results = await extractor.aforward(article=article)
                article_extract = results.article_output
                NLPModule._article_extract_cache[cache_key] = article_extract.model_copy(
                    deep=True
                )
        except Exception as e:
            logger.warning(
                "Article LLM extraction failed for %r: %s",
                raw_article.title,
                e,
            )
            if not NLPModule._allow_rule_fallback():
                raise
            return article_from_raw_article(raw_article, [])

        return NLPModule._article_from_extract(raw_article, article_extract)

    @staticmethod
    async def create_source(raw_source: RawSource) -> Source:
        """Create a source using the response fields from the news aggregator"""
        if NLPModule._nlp_mode() == "cheap":
            return NLPModule._source_from_raw_source(raw_source)

        from app.models.sources import SourceInput

        # Convert RawSource to SourceInput
        source_input = SourceInput(
            title=raw_source.title,
            description=raw_source.description,
            language=None,  # RawSource doesn't have language, LLM will infer it
            country_code=raw_source.country_code,
        )

        extractor = NLPModule._get_source_extractor()
        results = await extractor.aforward(source=source_input)
        return results.source_output

    @staticmethod
    async def generate_all_from_article(
        raw_article: RawArticle,
    ) -> ArticlePipelineResult:
        """
        Generate all objects from article saving to database.

        Returns:
            ArticlePipelineResult containing article, source, and lists of new artists/groups
        """
        article = await NLPModule.create_article(raw_article)
        source = None
        if hasattr(raw_article, "raw_source") and raw_article.raw_source:
            source = await NLPModule.create_source(raw_article.raw_source)

        if NLPModule._nlp_mode() != "full":
            return ArticlePipelineResult(
                article=article,
                source=source,
                new_artists=[
                    NLPModule._artist_from_mention(artist_name, article, raw_article)
                    for artist_name in dict.fromkeys(article.artists_mentioned)
                ],
                new_groups=[
                    NLPModule._group_from_mention(group_name, article, raw_article)
                    for group_name in dict.fromkeys(article.groups_mentioned)
                ],
            )

        new_artists = []
        new_groups = []
        group_name_set = set()

        for group_name in article.groups_mentioned:
            if group_name not in group_name_set:
                group = await NLPModule.create_group(name=group_name)
                new_groups.append(group)
                group_name_set.add(group_name)

        for artist_name in article.artists_mentioned:
            artist = await NLPModule.create_artist(name=artist_name)
            new_artists.append(artist)

            if artist.in_groups and hasattr(artist, "group_names"):
                for group_name in artist.group_names:
                    if group_name not in group_name_set:
                        group = await NLPModule.create_group(name=group_name)
                        new_groups.append(group)
                        group_name_set.add(group_name)

        return ArticlePipelineResult(
            article=article,
            source=source,
            new_artists=new_artists,
            new_groups=new_groups,
        )
