from typing import List, Optional

from app.interfaces.nlp_module import iNLPModule
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
    def create_artist(name: str, group_membership: List[str] = []) -> Artist:
        """Generate an Artist object using their name and a list of groups they're apart of"""
        artist_input = ArtistInput(artist_name=name, artist_groups=group_membership)
        extractor = NLPModule._get_artist_extractor()
        results = extractor.forward(artist_input=artist_input)
        return results.artist_output

    @staticmethod
    def create_group(name: str, group_members: List[str] = []) -> Group:
        """Create a group using names and member artists"""
        group_input = GroupInput(group_name=name, artists_in_group=group_members)
        extractor = NLPModule._get_group_extractor()
        results = extractor.forward(group_input=group_input)
        return results.group_output

    @staticmethod
    def create_event(articles: List[Article], events: List[Event] = []) -> Event:
        """Create an event using a list of articles or events, or both"""
        extractor = NLPModule._get_event_extractor()
        results = extractor.forward(articles=articles, events=events)
        return results.event_output

    @staticmethod
    async def create_article(raw_article: RawArticle) -> Article:
        """Create an article using the response fields from the news aggregator"""
        article_input = ArticleInput(
            article_title=raw_article.title, article_text=raw_article.content
        )
        extractor = NLPModule._get_article_extractor()
        results = extractor.forward(article_input=article_input)
        article = results.article_output
        if isinstance(article, Article):
            return article

    @staticmethod
    def create_source(raw_source: RawSource) -> Source:
        """Create a source using the response fields from the news aggregator"""
        extractor = NLPModule._get_source_extractor()
        results = extractor.forward(source_input=raw_source)
        return results.source_output

    @staticmethod
    async def create_all_from_article(raw_article: RawArticle) -> List:
        """
        Given an article from news aggregator, create an article,
        and where appropriate create artists, groups, events and sources
        """
        results = []
        article = await NLPModule.create_article(raw_article)
        results.append({"article": article})

        if hasattr(raw_article, "source") and raw_article.source:
            source = NLPModule.create_source(raw_article.source)
        else:
            source = None

        results.append({"source": source})

        artists_mentioned = article.artists_mentioned
        groups_mentioned = article.groups_mentioned

        artist_db = IArtistRepository()
        group_db = IGroupRepository()
        created_groups = []
        for group_name in groups_mentioned:
            group_store = await group_db.get_by_name(group_name)
            if not group_store:
                group = NLPModule.create_group(name=group_name)
                group_store = await group_db.create(group)
                created_groups.append(group_store)

            article.group_mentioned_ids.append(group_store._id)
        i = 0
        for group in created_groups:
            results.append({f"group_{i}": group})
            i += 1

        created_artists = []
        created_groups = []

        for artist_name in artists_mentioned:
            artist_store = await artist_db.get_by_name(artist_name)
            if not artist_store:
                artist = NLPModule.create_artist(name=artist_name)
                artist_store = await artist_db.create(artist)
                created_artists.append(artist_store)
            article.artist_mentioned_ids.append(artist_store._id)
            if artist_store.in_groups:
                for group_name in artist_store.group_names:
                    group_store = await group_db.get_by_name(group_name)
                    if not group_store:
                        group = NLPModule.create_group(name=group_name)
                        group_store = await group_db.create(group)
                        created_groups.append(group_store)

                    if group_store._id not in artist_store.group_ids:
                        artist_store.group_ids.append(group_store._id)
                await artist_db.update(artist_store._id, artist_store)
        j = 0
        for artist in created_artists:
            results.append({f"artist_{j}": artist})
            j += 1
        for group in created_groups:
            results.append({f"group_{i}": group})
            i += 1
        return results
