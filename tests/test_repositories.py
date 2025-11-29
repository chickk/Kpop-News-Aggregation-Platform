import pytest
from datetime import date
from pymongo.errors import DuplicateKeyError

from app.models.artists import Artist
from app.data_layer.schemas import Artist_db
from app.adapters.mongo_unit_of_work import MongoUnitOfWork
# Assuming the test_db fixture is in conftest.py


@pytest.mark.skip(reason="The local MongoDB is not configured as a duplicate set.")
@pytest.mark.asyncio
async def test_unit_of_work_commit(test_db):
    """
    Test: Verify that the 'commit()' method of the Unit of Work was successful.
    "Happy Path": Check if the data has been saved correctly.
    """
    # Preparation: Create a Unit of Work instance
    # (the test_db fixture is the client provided by conftest.py)
    uow = MongoUnitOfWork(client=test_db)
    
    # Preparation: Create a test database (must include all required fields for all Artist models).
    new_artist_data = Artist(
        name="IU",
        bio="Test bio for IU",
        career_start=date(2008, 9, 18),
        is_active=True,
        language="Korean",
        countries=["South Korea"],
        group_ids=[]
    )
    # Convert the Pydantic model to a Beanie DB model
    new_artist_db = Artist_db(**new_artist_data.model_dump())
    
    # Execution: Perform the create operation in UoW
    async with uow:
        created_artist = await uow.artists.create(new_artist_db)
        
    # Validation:
    # 1. Check if the data can be read externally from UoW (indicating a successful commit).
    assert created_artist.id is not None
    
    # Establish a new UoW (new session) for authentication.
    async with MongoUnitOfWork(client=test_db) as new_uow:
        fetched_artist = await new_uow.artists.get_by_id(str(created_artist.id))
        
    assert fetched_artist is not None
    assert fetched_artist.name == "IU"
    
    # Clean up
    await fetched_artist.delete()

@pytest.mark.skip(reason="The local MongoDB is not configured as a duplicate set.")
@pytest.mark.asyncio
async def test_unit_of_work_rollback(test_db):
    """
    Test: Verify that the Unit of Work's rollback() function succeeds.
    "Sad Path": Throws an error midway through the transaction, checking if data *was* not saved.
    """
    uow = MongoUnitOfWork(client=test_db)
    
    # Preparation: Establish test data
    new_artist_data = Artist(
        name="BTS",
        bio="Test bio for BTS",
        career_start=date(2013, 6, 13),
        is_active=True,
        language="Korean",
        countries=["South Korea"],
        group_ids=[]
    )

    new_artist_db = Artist_db(**new_artist_data.model_dump())
    
    # implement:
    created_artist_id = None
    try:
        async with uow:
            created_artist = await uow.artists.create(new_artist_db)
            created_artist_id = str(created_artist.id)
            # Intentionally causing an error to trigger a rollback
            raise ValueError("Something went wrong during the transaction")
            
    except ValueError as e:
        assert "Something went wrong" in str(e) # Make sure it's the error we expected. Make sure it's the error we expected.
    
    # Verification:
    # Check if data cannot be read from outside the UoW (indicating successful rollback)
    assert created_artist_id is not None # Ensure that the ID is assigned a value at least within the try block.
    
    async with MongoUnitOfWork(client=test_db) as new_uow:
        fetched_artist = await new_uow.artists.get_by_id(created_artist_id)
        
    assert fetched_artist is None # Key verification: The data should not exist.


@pytest.mark.asyncio
async def test_artist_repository_get_by_name(test_db):
    """
    Test: Verify that the specific method get_by_name in MongoArtistRepository works correctly.
    """
    # (修復) 傳入 use_transaction=False
    # 我們不在乎這個測試的交易，我們只想測試 get_by_name
    uow = MongoUnitOfWork(client=test_db, use_transaction=False)
    
    # 準備：先建立一筆資料並 commit
    new_artist_data = Artist(
        name="BLACKPINK",
        bio="Test bio for BLACKPINK",
        career_start=date(2016, 8, 8),
        is_active=True,
        language="Korean",
        countries=["South Korea"],
        group_ids=[]
    )
    # (修復)
    new_artist_db = Artist_db(**new_artist_data.model_dump())
    
    created_artist_id = None # 用於清理
    
    async with uow:
        created_artist = await uow.artists.create(new_artist_db)
        created_artist_id = str(created_artist.id) # 儲存 ID
        
    # 執行：
    # 建立一個新的 UoW 來執行 get_by_name
    found_artist = None
    # (修復) 建立一個新的 UoW，同樣停用交易
    async with MongoUnitOfWork(client=test_db, use_transaction=False) as new_uow:
        found_artist = await new_uow.artists.get_by_name("BLACKPINK")
        
    # 驗證：
    assert found_artist is not None
    assert found_artist.name == "BLACKPINK"
    assert found_artist.bio == "Test bio for BLACKPINK"
    
    # 清理
    # (修復) 使用一個新的 UoW 來執行刪除，確保 session 是
    assert created_artist_id is not None
    async with MongoUnitOfWork(client=test_db, use_transaction=False) as clean_uow:
        await clean_uow.artists.delete(created_artist_id)