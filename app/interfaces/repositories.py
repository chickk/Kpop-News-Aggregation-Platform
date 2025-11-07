from abc import abstractmethod
from typing import List, Optional
from datetime import datetime, date

from app.interfaces.repository import IRepository
from app.models.articles import Article
from app.models.artists import Artist
from app.models.groups import Group
from app.models.events import Event
from app.models.sources import Source


class IArticleRepository(IRepository[Article]):
    """Repository interface for Article entities."""

    @abstractmethod
    async def get_by_source(
        self, source_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Get all articles from a specific source."""
        pass

    @abstractmethod
    async def get_by_artist(
        self, artist_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Get all articles mentioning a specific artist."""
        pass

    @abstractmethod
    async def get_by_group(
        self, group_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Get all articles mentioning a specific group."""
        pass

    @abstractmethod
    async def get_by_event(
        self, event_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Get all articles associated with a specific event."""
        pass

    @abstractmethod
    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Get articles published within a date range."""
        pass

    @abstractmethod
    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Get articles with any of the specified tags."""
        pass

    @abstractmethod
    async def search_by_text(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        """Full-text search in article title and content."""
        pass


class IArtistRepository(IRepository[Artist]):
    """Repository interface for Artist entities."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Artist]:
        """Get an artist by their name."""
        pass

    @abstractmethod
    async def get_by_group(
        self, group_id: str, skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        """Get all artists in a specific group."""
        pass

    @abstractmethod
    async def get_active(self, skip: int = 0, limit: int = 100) -> List[Artist]:
        """Get all currently active artists."""
        pass

    @abstractmethod
    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        """Get artists from a specific country."""
        pass

    @abstractmethod
    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        """Get artists with any of the specified tags."""
        pass

    @abstractmethod
    async def get_by_career_period(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Artist]:
        """Get artists who were active during the specified period."""
        pass


class IGroupRepository(IRepository[Group]):
    """Repository interface for Group entities."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Group]:
        """Get a group by its name."""
        pass

    @abstractmethod
    async def get_by_artist(
        self, artist_id: str, skip: int = 0, limit: int = 100
    ) -> List[Group]:
        """Get all groups that include a specific artist."""
        pass

    @abstractmethod
    async def get_active(self, skip: int = 0, limit: int = 100) -> List[Group]:
        """Get all currently active groups."""
        pass

    @abstractmethod
    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Group]:
        """Get groups from a specific country."""
        pass

    @abstractmethod
    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Group]:
        """Get groups with any of the specified tags."""
        pass

    @abstractmethod
    async def get_by_formation_period(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Group]:
        """Get groups formed during the specified period."""
        pass


class IEventRepository(IRepository[Event]):
    """Repository interface for Event entities."""

    @abstractmethod
    async def get_by_title(self, title: str) -> Optional[Event]:
        """Get an event by its title."""
        pass

    @abstractmethod
    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        """Get events occurring within a date range."""
        pass

    @abstractmethod
    async def get_by_artist(
        self, artist_id: str, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        """Get all events involving a specific artist."""
        pass

    @abstractmethod
    async def get_by_group(
        self, group_id: str, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        """Get all events involving a specific group."""
        pass

    @abstractmethod
    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        """Get events in a specific country."""
        pass

    @abstractmethod
    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Event]:
        """Get events with any of the specified tags."""
        pass

    @abstractmethod
    async def get_by_sentiment_range(
        self,
        min_sentiment: float,
        max_sentiment: float,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """Get events with average sentiment within the specified range."""
        pass


class ISourceRepository(IRepository[Source]):
    """Repository interface for Source entities."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Source]:
        """Get a source by its name."""
        pass

    @abstractmethod
    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Source]:
        """Get sources from a specific country."""
        pass

    @abstractmethod
    async def get_by_language(
        self, language: str, skip: int = 0, limit: int = 100
    ) -> List[Source]:
        """Get sources in a specific language."""
        pass

    @abstractmethod
    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Source]:
        """Get sources with any of the specified tags."""
        pass
