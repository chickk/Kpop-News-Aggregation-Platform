from dataclasses import dataclass, field
from typing import List, Optional

from app.interfaces.nlp_module import ArticlePipelineResult, iNLPModule
from app.interfaces.repositories import IArtistRepository, IGroupRepository
from app.models.articles import Article, RawArticle
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


class NLPModule(iNLPModule):
    """Implementation of iNLPModule for performing NLP tasks using LLM extractors"""

    _artist_extractor: Optional[ArtistExtractor] = None
    _article_extractor: Optional[ArticleExtractor] = None
    _group_extractor: Optional[GroupExtractor] = None
    _source_extractor: Optional[SourceExtractor] = None
    _event_extractor: Optional[EventExtractor] = None

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
        article = ArticleInput(
            article_title=raw_article.title, article_text=raw_article.text
        )
        extractor = NLPModule._get_article_extractor()
        results = await extractor.aforward(article=article)
        article_extract = results.article_output

        # Combine extracted NLP fields with raw article data to create full Article
        article = Article(
            # Fields from ArticleExtract
            summary=article_extract.summary,
            sentiment=article_extract.sentiment,
            artists_mentioned=article_extract.artists_mentioned,
            groups_mentioned=article_extract.groups_mentioned,
            tags=article_extract.tags,
            countries=article_extract.countries,
            # Fields from RawArticle
            title=raw_article.title,
            author=raw_article.author,
            source_id="",  # Will be set when source is saved
            publication_date=raw_article.publication_date,
            text=raw_article.text,
            images=raw_article.image_urls,
            video=raw_article.video_url,
            language=raw_article.language or "en",
            url=raw_article.url,
            # ID fields (initially empty)
            groups_mentioned_ids=[],
            artists_mentioned_ids=[],
        )
        return article

    @staticmethod
    async def create_source(raw_source: RawSource) -> Source:
        """Create a source using the response fields from the news aggregator"""
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
