from pymongo.client_session import ClientSession
from typing import List, Optional
from datetime import date

from .beanie_repository import BeanieRepository
from app.interfaces.raw_article_repository import IRawArticleRepository
from app.data_layer.schemas import RawArticle_db
from app.models.articles import RawArticle

class MongoRawArticleRepository(BeanieRepository[RawArticle_db], IRawArticleRepository):
    """
    Beanie implementation of IRawArticleRepository.
    """
    
    def __init__(self, session: ClientSession = None):
        # Pass RawArticle_db (Beanie model) to the underlying storage
        super().__init__(model=RawArticle_db, session=session)

    # --- Specific methods for implementing IRawArticleRepository ---

    async def get_unprocessed(self, skip: int = 0, limit: int = 100) -> List[RawArticle]:
        """
        Retrieve the raw, unprocessed articles.
        (Based on the 'processed' index)
        """
        query = self.model.find(
            RawArticle_db.processed == False, 
            session=self.session
        )
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_url(self, url: str) -> Optional[RawArticle]:
        """
        Find the original article by URL (for deduplication).
        (Based on 'url' index)
        """
        return await self.model.find_one(
            RawArticle_db.url == url, 
            session=self.session
        )

    async def get_by_source(self, source_name: str, skip: int = 0, limit: int = 100) -> List[RawArticle]:
        """
        Retrieve articles based on their original source name.
        (Based on the 'raw_source.title' index)
        """
        query = self.model.find(
            {"raw_source.title": source_name}, 
            session=self.session
        )
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_date_range(
        self, start: date, end: date, skip: int = 0, limit: int = 100
    ) -> List[RawArticle]:
        """
        Retrieve the original article based on the publication date range.
        (Based on the 'publication_date' index)

        """
        query = self.model.find(
            RawArticle_db.publication_date >= start,
            RawArticle_db.publication_date <= end,
            session=self.session
        )
        return await query.skip(skip).limit(limit).to_list()