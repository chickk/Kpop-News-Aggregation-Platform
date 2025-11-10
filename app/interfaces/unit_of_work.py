from abc import ABC, abstractmethod
from typing import Optional

from app.interfaces.repositories import (
    IArticleRepository,
    IArtistRepository,
    IGroupRepository,
    IEventRepository,
    ISourceRepository,
)
from app.interfaces.raw_article_repository import IRawArticleRepository


class IUnitOfWork(ABC):
    """
    Unit of Work pattern interface for managing transactions across multiple repositories.

    This interface ensures that all operations within a transaction are committed or rolled back
    together, maintaining data consistency across multiple entities.

    Usage:
        async with unit_of_work:
            artist = await unit_of_work.artists.get_by_id("artist_id")
            artist.name = "Updated Name"
            await unit_of_work.artists.update("artist_id", artist)
            await unit_of_work.commit()
    """

    raw_articles: IRawArticleRepository
    articles: IArticleRepository
    artists: IArtistRepository
    groups: IGroupRepository
    events: IEventRepository
    sources: ISourceRepository

    @abstractmethod
    async def __aenter__(self):
        """Enter the async context manager and begin a transaction."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the async context manager.

        If an exception occurred, rollback the transaction.
        Otherwise, commit if not already committed.
        """
        pass

    @abstractmethod
    async def commit(self):
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self):
        """Rollback the current transaction."""
        pass
