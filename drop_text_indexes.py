"""
Script to drop existing TEXT indexes so they can be recreated with new default_language="none" setting.
Run this once to fix language override errors.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os


async def drop_text_indexes():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

    client = AsyncIOMotorClient(mongo_uri)
    db = client.idolTracker

    collections = [
        "articles",
        "artists",
        "sources",
        "groups",
    ]

    for collection_name in collections:
        collection = db[collection_name]
        # collection.drop()
        # Get all indexes
        indexes = await collection.list_indexes().to_list(length=None)

        # Find and drop TEXT indexes
        for index in indexes:
            # Check if this is a TEXT index
            if any(value == "text" for value in index.get("key", {}).values()):
                index_name = index["name"]
                print(f"Dropping TEXT index '{index_name}' from {collection_name}")
                await collection.drop_index(index_name)
                print(f"  ✓ Dropped")

    print("\nDone! TEXT indexes have been dropped.")
    print(
        "They will be recreated with default_language='none' when Beanie initializes."
    )

    client.close()


if __name__ == "__main__":
    asyncio.run(drop_text_indexes())
