from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from app.models.articles import Article, RawArticle
from app.models.artists import Artist
from app.models.groups import Group
from app.models.events import Event
from app.models.sources import RawSource, Source


@dataclass
class ArticlePipelineResult:
    """Result of article processing pipeline containing all generated objects"""

    article: Article
    source: Optional[Source]
    new_artists: List[Artist] = field(default_factory=list)
    new_groups: List[Group] = field(default_factory=list)


class iNLPModule(ABC):
    """Module for performing various NLP tasks needed for the IdolTracker Website"""

    @staticmethod
    @abstractmethod
    def create_artist(name: str, group_membership: List[str] = []) -> Artist:
        """Generate an Artist object using their name and a list of groups theyre apart of"""
        pass

    @staticmethod
    @abstractmethod
    def create_group(name: str, group_members: List[str] = []) -> Group:
        """Create a group using names and member artists"""
        pass

    @staticmethod
    @abstractmethod
    def create_event(articles: List[Article], events: List[Event] = []) -> Event:
        """Create an event using a list of articles or events, or both"""
        pass

    @staticmethod
    @abstractmethod
    def create_article(raw_article: RawArticle) -> Article:
        """Create an article using the response fields from the news aggregator"""
        pass

    @staticmethod
    @abstractmethod
    def create_source(raw_source: RawSource) -> Source:
        """Create a source using the response fields from the news aggregator"""
        pass

    @staticmethod
    @abstractmethod
    def generate_all_from_article(raw_article: RawArticle) -> ArticlePipelineResult:
        """
        Given an article from news aggregator, create an article,
        and where appropriate create artists, groups, events and sources
        """
        pass
