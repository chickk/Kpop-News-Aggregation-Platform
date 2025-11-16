import asyncio
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import pytest_asyncio

# 
# --- 1. Import all your DB Schemas (Models) ---
# 
# (Ensure app/__init__.py and app/data_layer/__init__.py exist)
from app.data_layer.schemas import (
    Article_db,
    Artist_db,
    Event_db,
    Group_db,
    Source_db,
)

# 
# --- 2. Important Test Settings ---
# 
# Use a *dedicated* test database, not your production "idolTracker" DB
TEST_DB_NAME = "idolTracker_test" 
TEST_URI = f"mongodb://localhost:27017/{TEST_DB_NAME}"

# List all your Beanie models
ALL_MODELS = [
    Article_db,
    Source_db,
    Artist_db,
    Group_db,
    Event_db,
]


@pytest.fixture(scope="session")
def event_loop():
    """Provides a session-scoped event loop for pytest-asyncio."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    Function-scope Pytest fixture.
    1. Create a Client and connect to the *test* DB.
    2. Initialize Beanie with the *test* DB.
    3. Run (yield) all tests.
    4. After tests are done, *drop the entire* test database to ensure a clean state.
    """
    
    # 1. Setup
    client = AsyncIOMotorClient(TEST_URI)
    
    # Force Beanie to use the test database
    await init_beanie(
        database=client.get_database(TEST_DB_NAME),
        document_models=ALL_MODELS,
    )

    # 2. Run (yield)
    yield client 

    # 3. Teardown
    await client.drop_database(TEST_DB_NAME)
    client.close()