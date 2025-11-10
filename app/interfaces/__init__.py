"""
Data layer interfaces for the IdolTracker application.

This package provides abstract interfaces for data access using the Repository
and Unit of Work patterns. These interfaces allow for database-agnostic business
logic that can work with any storage backend.
"""

from app.interfaces.repository import IRepository
from app.interfaces.repositories import (
    IArticleRepository,
    IArtistRepository,
    IGroupRepository,
    IEventRepository,
    ISourceRepository,
)
from app.interfaces.unit_of_work import IUnitOfWork

__all__ = [
    "IRepository",
    "IArticleRepository",
    "IArtistRepository",
    "IGroupRepository",
    "IEventRepository",
    "ISourceRepository",
    "IUnitOfWork",
]
