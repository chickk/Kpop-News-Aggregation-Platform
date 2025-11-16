from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.models.articles import Article
from app.models.artists import Artist
from app.models.groups import Group
from app.models.events import Event
from app.models.sources import Source


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
    def create_article(
        article_title: str,
        article_text: str,
        source: str,
        language: str,
        images: List[str] = [],
        video: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        author: Optional[str] = None,
    ) -> Article:
        """Create an article using the response fields from the news aggregator"""
        pass

    @staticmethod
    @abstractmethod
    def create_source(
        title: str,
        description: str,
        language: str,
        country_code: str,
    ) -> Source:
        """Create a source using the response fields from the news aggregator"""
        pass

    @staticmethod
    @abstractmethod
    def create_all_from_article(
        article_title: str,
        article_text: str,
        source_title: str,
        source_language: str,
        source_description: str,
        souce_country_code: str,
        language: str,
        images: List[str] = [],
        video: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        author: Optional[str] = None,
    ) -> List:
        """
        Given an article from news aggregator, create an article,
        and where appropriate create artists, groups, events and sources
        """
        pass
