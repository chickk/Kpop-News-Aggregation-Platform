from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.client_session import ClientSession
from beanie import init_beanie
from typing import Optional 

from app.interfaces.unit_of_work import IUnitOfWork
from app.interfaces.repositories import (
    IArticleRepository, IArtistRepository, IGroupRepository, IEventRepository, ISourceRepository
)
from app.interfaces.raw_article_repository import IRawArticleRepository

from .mongo_repositories import (
    MongoArticleRepository, 
    MongoArtistRepository, 
    MongoGroupRepository, 
    MongoEventRepository,   
    MongoSourceRepository
)
from .mongo_raw_article_repo import MongoRawArticleRepository 

class MongoUnitOfWork(IUnitOfWork):
    """
    A MongoDB/Beanie implementation of IUnitOfWork.
    It uses AsyncIOMotorClient to manage transactions.
    """
    
    def __init__(self, client: AsyncIOMotorClient, use_transaction: bool = True):
        self.client = client
        self.session: Optional[ClientSession] = None
        self.use_transaction = use_transaction
        self._transaction_started = False
        
        # Added type hints for raw_articles
        self.articles: IArticleRepository
        self.artists: IArtistRepository
        self.groups: IGroupRepository
        self.events: IEventRepository
        self.sources: ISourceRepository
        #self.raw_articles: IRawArticleRepository

    async def __aenter__(self):
        """Enter the context manager and start a transaction session."""
        self.session = self.client.start_session()
        
        if self.use_transaction:
            try:
                self.session.start_transaction()
                self._transaction_started = True
            except Exception as e:
                print(f"Warning: Could not start transaction (expected in standalone mode). Running without it. Error: {e}")
                self._transaction_started = False
        
        # Create all repositories and pass them to the same session.
        self.articles = MongoArticleRepository(session=self.session)
        self.artists = MongoArtistRepository(session=self.session)
        self.groups = MongoGroupRepository(session=self.session)
        self.events = MongoEventRepository(session=self.session)
        self.sources = MongoSourceRepository(session=self.session)
        # Initialize raw_articles
        #self.raw_articles = MongoRawArticleRepository(session=self.session)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the async context manager.
        If an exception occurs (exc_type is not None), roll back the transaction.
        Otherwise, commit the transaction.
        """
        if self.session:
            if self._transaction_started:
                if exc_type:
                    await self.rollback()
                else:
                    await self.commit()
            
            await self.session.end_session()
            self.session = None
            self._transaction_started = False

    async def commit(self):
        """Submit the current MongoDB transaction."""
        if self.session and self.session.in_transaction:
            await self.session.commit_transaction()

    async def rollback(self):
        """Roll back the current MongoDB transaction."""
        if self.session and self.session.in_transaction:
            await self.session.abort_transaction()