import pytest
import hashlib
from pymongo.errors import DuplicateKeyError
from datetime import datetime, date
import asyncio
# Import your models
# (Note: We are importing the DB Schemas)
from app.data_layer.schemas import Artist_db, Article_db, Source_db

# 
# --- Notes ---
# 
# 1. All test functions must be `async def`
# 2. Must use `@pytest.mark.asyncio`
# 3. Must pass in the `test_db` fixture (it must run for initialization even if not directly used)
#

@pytest.mark.asyncio
async def test_base_document_timestamps(test_db):
    """
    Tests if BaseDocument's 'created' and 'modified' timestamps are automatically generated.
    """
    # Create a sample Artist (you need to fill in the minimum required fields from the Pydantic model)
    artist = Artist_db(
        name="Test Artist",
        bio="Test Bio",
        career_start=date(2020, 1, 1),
        is_active=True,
        language="en",
        countries=["USA"],
        group_ids=[] # From Artist model
    )
    
    # 1. Test Insert (set_time)
    await artist.insert() #
    
    assert artist.created is not None
    assert artist.modified is not None
    assert artist.created == artist.modified # Should be equal upon creation
    
    old_modified = artist.modified
    
    # Pause briefly to ensure the timestamp changes
    await asyncio.sleep(0.01) 
    
    # 2. Test Update (update_modified_time)
    artist.name = "Updated Name"
    await artist.save() #
    
    assert artist.modified > old_modified #
    assert artist.created < artist.modified # Creation time should be earlier than modification time


@pytest.mark.asyncio
async def test_article_hash_generation(test_db):
    """
    Tests if Article_db automatically generates 'article_hash'.
    """
    test_text = "This is the article content for hashing."
    expected_hash = hashlib.sha256(test_text.encode()).hexdigest()
    
    article = Article_db(
        # Fields from your original test
        title="Hash Test",
        text=test_text,

        # ----------------------------------------------------
        # Fill in all required fields from `Article` and `ArticleExtract`
        # ----------------------------------------------------
        summary="A test summary for the article.",
        sentiment=0.5,  # 0.5 represents neutral
        source_id="dummy-source-id-123", # Required string
        language="en",
        groups_mentioned_ids=[], # Required list (empty list is valid)
        artists_mentioned_ids=[], # Required list (empty list is valid)
        
        # (Note: We removed the "url" field, as Article_db doesn't have it)
        
        # Can also fill in optional fields to make the data more complete
        publication_date=datetime.now()
    )
    
    await article.insert()
    
    # Validate if hash was correctly populated by @before_event or @model_validator
    assert article.article_hash is not None #
    assert article.article_hash == expected_hash #


@pytest.mark.asyncio
async def test_unique_constraint_source_name(test_db):
    """
    Tests if Source_db's 'name' field is correctly forced as unique (unique=True).
    """
    # 1. Insert the first record
    source1 = Source_db(
        name="Unique Source",
        bio="Test Source Bio",
        language="en",
        countries=["USA"],
        tags=[]
    )
    await source1.insert()
    
    # 2. Create the second record
    source2 = Source_db(
        name="Unique Source", #
        bio="Another Source Bio",
        language="fr",
        countries=["France"],
        tags=[]
    )
    
    # 3. Assert: Inserting a second record with the same name *must* trigger a DuplicateKeyError
    with pytest.raises(DuplicateKeyError):
        await source2.insert() #


@pytest.mark.asyncio
async def test_non_unique_constraint_artist_name(test_db):
    """
    Tests if Artist_db's 'name' field *allows* duplicates.
    """
    # 1. Insert the first record
    artist1 = Artist_db(
        name="Same Name Artist",
        bio="Bio 1",
        career_start=date(2020, 1, 1),
        language="en",
        countries=["USA"],
        group_ids=[]
    )
    await artist1.insert()
    
    # 2. Insert the second record
    artist2 = Artist_db(
        name="Same Name Artist", #
        bio="Bio 2",
        career_start=date(2022, 1, 1),
        language="ko",
        countries=["Korea"],
        group_ids=[]
    )
    
    # 3. Assert: The insert should *succeed*
    try:
        await artist2.insert()
    except DuplicateKeyError:
        # If an error occurs, the test fails
        pytest.fail("Artist name was unique, but it should not be.")
        
    # Verify there are indeed two records in the database
    count = await Artist_db.find(Artist_db.name == "Same Name Artist").count()
    assert count == 2