from abc import abstractmethod
from typing import List, Optional
from datetime import datetime

from app.interfaces.repository import IRepository
from app.interfaces.news_aggregator import RawArticle


class IRawArticleRepository(IRepository[RawArticle]):
    """
    Repository interface for raw (unprocessed) articles.

    This is a staging area for articles fetched from external sources
    before they're processed by LLMs and converted to full Article objects.
    """

    @abstractmethod
    async def get_unprocessed(self, skip: int = 0, limit: int = 100) -> List[RawArticle]:
        """
        Get all articles that haven't been processed yet.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of unprocessed raw articles
        """
        pass

    @abstractmethod
    async def get_by_source(
        self, source_name: str, skip: int = 0, limit: int = 100
    ) -> List[RawArticle]:
        """Get raw articles from a specific source."""
        pass

    @abstractmethod
    async def get_by_url(self, url: str) -> Optional[RawArticle]:
        """Get a raw article by its URL (for duplicate detection)."""
        pass

    @abstractmethod
    async def mark_as_processed(self, id: str) -> bool:
        """
        Mark a raw article as processed.

        Args:
            id: The ID of the raw article

        Returns:
            True if marked successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100
    ) -> List[RawArticle]:
        """Get raw articles within a date range."""
        pass
