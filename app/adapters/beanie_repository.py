from typing import Generic, TypeVar, List, Optional, Dict, Any
from beanie import Document, PydanticObjectId
from pymongo.client_session import ClientSession
from app.interfaces.repository import IRepository

# TypeVar for building Beanie Document models
BeanieDocument = TypeVar("BeanieDocument", bound=Document)

class BeanieRepository(IRepository[BeanieDocument], Generic[BeanieDocument]):
    """
    A generic Beanie implementation of IRepository.
    It handles all basic CRUD operations.
    """
    
    def __init__(
        self, 
        model: type[BeanieDocument], 
        session: ClientSession = None
    ):
        self.model = model
        self.session = session

    async def get_by_id(self, id: str) -> Optional[BeanieDocument]:
        try:
            obj_id = PydanticObjectId(id)
        except:
            return None # Invalid ID format
        return await self.model.get(obj_id, session=self.session)

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[BeanieDocument]:
        query = self.model.find(filters or {}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def create(self, entity: BeanieDocument) -> BeanieDocument:
        # Beanie's insert will automatically update the entity.
        await entity.insert(session=self.session)
        return entity

    async def update(self, id: str, entity: BeanieDocument) -> Optional[BeanieDocument]:
        # Note: Beanie's 'save' (partial update) is safer than 'replace' (full replacement).
        db_doc = await self.get_by_id(id)
        if db_doc:
            update_data = entity.model_dump(exclude_unset=True)
            await db_doc.set(update_data, session=self.session)
            return db_doc
        return None

    async def delete(self, id: str) -> bool:
        doc = await self.get_by_id(id)
        if doc:
            await doc.delete(session=self.session)
            return True
        return False

    async def exists(self, id: str) -> bool:
        return await self.get_by_id(id) is not None

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        return await self.model.count(filters or {}, session=self.session)