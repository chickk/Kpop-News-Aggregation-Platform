from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.models.articles import RawArticle


class INewsAggregator(ABC):
    """
    Interface for fetching articles from external news sources.

    Implementations might include:
    - NewsAPI
    - Google News RSS
    - Custom web scrapers
    - RSS feed readers
    """

    @abstractmethod
    async def fetch_articles(
        self,
        query_terms: List[str],
        concepts: bool,
        start_date: datetime = None,
        end_date: datetime = None,
        language: Optional[str] = None,
        max_results: int = 100,
    ) -> List[RawArticle]:
        """
        Fetch articles from the external source.

        Args:
            query_terms: Search terms to filter articles (e.g., ["IU", "K-pop"])
            concepts: Are the query terms concepts or keywords
            start_date: Earliest publication date to fetch
            end_date: Latest publication date to fetch
            language: Optional language filter (e.g., "en", "ko")
            max_results: Maximum number of articles to return

        Returns:
            List of raw articles from the source
        """
        pass

    @abstractmethod
    async def get_source_info(self) -> str:
        """
        Get information about this news source.

        Returns:
            Name/description of the news aggregator
        """
        pass
