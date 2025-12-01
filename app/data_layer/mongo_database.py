import asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.data_layer.schemas import Article_db, Artist_db, Event_db, Group_db, Source_db, RawArticle_db

_client: AsyncIOMotorClient = None

async def init_db(URI: str = None) -> AsyncIOMotorClient:
    """
    Initializes the Beanie connection to the database.
    """
    global _client
    if not URI:
        raise ValueError("URI environment variable is not set")
    
    if _client is None:
        _client = AsyncMongoClient(URI)

        await init_beanie(
            database=_client.get_database("idolTracker"),
            document_models=[
                Article_db,
                Source_db, 
                Artist_db,
                Group_db,
                Event_db,
                RawArticle_db
            ],
        )
        print("Database initialized successfully.")
    
    return _client


async def main():
    URI = "mongodb://localhost:27017/idolTracker"
    await init_db(URI=URI)
    print("db started")


if __name__ == "__main__":
    asyncio.run(main())
