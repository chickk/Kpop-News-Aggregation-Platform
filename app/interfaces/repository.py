from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Base repository interface defining CRUD operations.
    All specific repositories should inherit from this interface.
    """

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Retrieve a single entity by its ID.

        Args:
            id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """
        Retrieve all entities with optional pagination and filtering.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            filters: Optional dictionary of field-value pairs to filter by

        Returns:
            List of entities matching the criteria
        """
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Create a new entity.

        Args:
            entity: The entity to create

        Returns:
            The created entity with any generated fields populated
        """
        pass

    @abstractmethod
    async def update(self, id: str, entity: T) -> Optional[T]:
        """
        Update an existing entity.

        Args:
            id: The unique identifier of the entity to update
            entity: The updated entity data

        Returns:
            The updated entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete an entity by its ID.

        Args:
            id: The unique identifier of the entity to delete

        Returns:
            True if the entity was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """
        Check if an entity exists by its ID.

        Args:
            id: The unique identifier to check

        Returns:
            True if the entity exists, False otherwise
        """
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching the given filters.

        Args:
            filters: Optional dictionary of field-value pairs to filter by

        Returns:
            Number of entities matching the criteria
        """
        pass
