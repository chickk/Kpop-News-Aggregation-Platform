import hashlib
from pymongo.client_session import ClientSession
from typing import List, Optional
from datetime import date, datetime
from beanie import PydanticObjectId
from bson.errors import InvalidId

from app.interfaces.repositories import (
    IArtistRepository,
    IArticleRepository,
    IGroupRepository,
    IEventRepository,
    ISourceRepository,
)
from app.data_layer.schemas import Artist_db, Article_db, Group_db, Event_db, Source_db
from app.models.artists import Artist
from app.models.articles import Article
from app.models.groups import Group
from app.models.events import Event
from app.models.sources import Source
from .beanie_repository import BeanieRepository


def _validate_id(id_str: str) -> Optional[PydanticObjectId]:
    """Tries to convert a string ID to PydanticObjectId, returns None on failure."""
    try:
        return PydanticObjectId(id_str)
    except InvalidId:
        return None


#
# --- Artist Repository Implementation ---
#
class MongoArtistRepository(BeanieRepository[Artist_db], IArtistRepository):
    """
    Beanie implementation of IArtistRepository.
    It inherits all CRUD methods from BeanieRepository.
    """

    def __init__(self, session: ClientSession = None):
        # Pass the Artist_db (Beanie model) to the base repository
        super().__init__(model=Artist_db, session=session)

    async def create(self, entity: Artist) -> Artist_db:
        """Override create to accept Artist and convert to Artist_db"""
        artist_db = Artist_db(**entity.model_dump())
        await artist_db.insert(session=self.session)
        return artist_db

    # --- Implementation of IArtistRepository specific methods ---

    async def get_by_name(self, name: str) -> Optional[Artist]:
        # Use Beanie's model query syntax
        return await self.model.find_one(Artist_db.name == name, session=self.session)

    async def get_by_group(
        self, group_id: str, skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        # Note: This assumes group_ids is a List[PydanticObjectId]
        # or that the string representation is valid for matching.
        # For PydanticObjectId list, a more robust query might be needed
        # if the input `group_id` isn't already an ObjectId.
        try:
            pyd_id = PydanticObjectId(group_id)
        except InvalidId:
            return []  # Invalid ID format

        query = self.model.find(
            {"group_ids": pyd_id},  # Use dict query for items in a list
            session=self.session,
        )
        return await query.skip(skip).limit(limit).to_list()

    async def get_active(self, skip: int = 0, limit: int = 100) -> List[Artist]:
        query = self.model.find(Artist_db.is_active == True, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    # --- (Implementation) Fill in missing abstract methods ---
    async def get_by_country(
        self, country_code: str, skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        # Assumes Artist_db.countries is a List[str]
        query = self.model.find({"countries": country_code}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        # Finds artists that have at least one of the tags in the list
        query = self.model.find(Artist_db.tags.in_(tags), session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_career_period(
        self, start: date, end: date, skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        # Finds artists whose career_start date is within the range
        query = self.model.find(
            Artist_db.career_start >= start,
            Artist_db.career_start <= end,
            session=self.session,
        )
        return await query.skip(skip).limit(limit).to_list()


#
# --- Article Repository Implementation ---
#
class MongoArticleRepository(BeanieRepository[Article_db], IArticleRepository):
    """Beanie implementation of IArticleRepository."""

    def __init__(self, session: ClientSession = None):
        super().__init__(model=Article_db, session=session)

    async def create(self, entity: Article) -> Article_db:
        """Override create to accept Article and convert to Article_db"""
        article_db = Article_db(**entity.model_dump())
        await article_db.insert(session=self.session)
        return article_db

    # --- Implementation of IArticleRepository specific methods ---

    async def search_by_text(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        # (This requires you to have set up a TEXT index in Article_db's Settings)
        query = self.model.find({"$text": {"$search": query}}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_source(
        self, source_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        try:
            pyd_id = PydanticObjectId(source_id)
        except InvalidId:
            return []

        # Assumes Article_db.source_id is a PydanticObjectId or Link
        query = self.model.find(Article_db.source_id.id == pyd_id, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_artist(
        self, artist_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        pyd_id = _validate_id(artist_id)
        if not pyd_id:
            return []

        query = self.model.find({"artists_mentioned_ids": pyd_id}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_group(
        self, group_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        pyd_id = _validate_id(group_id)
        if not pyd_id:
            return []

        query = self.model.find({"groups_mentioned_ids": pyd_id}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_event(
        self, event_id: str, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        pyd_id = _validate_id(event_id)
        if not pyd_id:
            return []

        query = self.model.find({"event_id": pyd_id}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_date_range(
        self, start: date, end: date, skip: int = 0, limit: int = 100
    ) -> List[Article]:
        # Finds articles whose published_at date is within the range
        query = self.model.find(
            Article_db.publication_date >= start,
            Article_db.publication_date <= end,
            session=self.session,
        )
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Article]:
        # Finds articles that have at least one of the tags in the list
        query = self.model.find(Article_db.tags.in_(tags), session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def exact_article_exists(self, article: str) -> bool:
        hashed_text = hashlib.sha256(article.encode()).hexdigest()
        result = await self.model.find_one(Article_db.article_hash == hashed_text)
        return result is not None


#
# --- Group Repository Implementation ---
#
class MongoGroupRepository(BeanieRepository[Group_db], IGroupRepository):
    """Beanie implementation of IGroupRepository."""

    def __init__(self, session: ClientSession = None):
        super().__init__(model=Group_db, session=session)

    async def create(self, entity: Group) -> Group_db:
        """Override create to accept Group and convert to Group_db"""
        group_db = Group_db(**entity.model_dump())
        await group_db.insert(session=self.session)
        return group_db

    async def get_by_name(self, name: str) -> Optional[Group]:
        return await self.model.find_one(Group_db.name == name, session=self.session)

    async def get_by_artist(
        self, artist_id: str, skip: int = 0, limit: int = 100
    ) -> List[Group]:
        pyd_id = _validate_id(artist_id)
        if not pyd_id:
            return []

        # Assumes Group_db.artist_ids is a List[PydanticObjectId]
        query = self.model.find({"artist_ids": pyd_id}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_active(self, skip: int = 0, limit: int = 100) -> List[Group]:
        query = self.model.find(Group_db.is_active == True, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Group]:
        query = self.model.find({"countries": country}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Group]:
        query = self.model.find(Group_db.tags.in_(tags), session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_formation_period(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Group]:
        filters = {}
        if start_date:
            filters[Group_db.formed >= start_date]  # 假設欄位名為 formed
        if end_date:
            filters[Group_db.disbanded <= end_date]  # 假設欄位名為 disbanded

        query = self.model.find(filters, session=self.session)
        return await query.skip(skip).limit(limit).to_list()


#
# --- Event Repository Implementation ---
#
class MongoEventRepository(BeanieRepository[Event_db], IEventRepository):
    """Beanie implementation of IEventRepository."""

    def __init__(self, session: ClientSession = None):
        super().__init__(model=Event_db, session=session)

    async def get_by_title(self, title: str) -> Optional[Event]:
        return await self.model.find_one(Event_db.title == title, session=self.session)

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        query = self.model.find(
            Event_db.event_date >= start_date,
            Event_db.event_date <= end_date,
            session=self.session,
        )
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_artist(
        self, artist_id: str, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        pyd_id = _validate_id(artist_id)
        if not pyd_id:
            return []

        query = self.model.find({"artist_ids": pyd_id}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_group(
        self, group_id: str, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        pyd_id = _validate_id(group_id)
        if not pyd_id:
            return []

        query = self.model.find({"group_ids": pyd_id}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        query = self.model.find({"countries": country}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Event]:
        query = self.model.find(Event_db.tags.in_(tags), session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_sentiment_range(
        self,
        min_sentiment: float,
        max_sentiment: float,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        query = self.model.find(
            Event_db.avg_sentiment >= min_sentiment,
            Event_db.avg_sentiment <= max_sentiment,
            session=self.session,
        )
        return await query.skip(skip).limit(limit).to_list()


#
# --- Source Repository Implementation ---
#
class MongoSourceRepository(BeanieRepository[Source_db], ISourceRepository):
    """Beanie implementation of ISourceRepository."""

    def __init__(self, session: ClientSession = None):
        super().__init__(model=Source_db, session=session)

    async def create(self, entity: Source) -> Source_db:
        """Override create to accept Source and convert to Source_db"""
        source_db = Source_db(**entity.model_dump())
        await source_db.insert(session=self.session)
        return source_db

    async def get_by_name(self, name: str) -> Optional[Source]:
        return await self.model.find_one(Source_db.name == name, session=self.session)

    async def get_by_country(
        self, country: str, skip: int = 0, limit: int = 100
    ) -> List[Source]:
        query = self.model.find({"countries": country}, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_language(
        self, language: str, skip: int = 0, limit: int = 100
    ) -> List[Source]:
        query = self.model.find(Source_db.language == language, session=self.session)
        return await query.skip(skip).limit(limit).to_list()

    async def get_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Source]:
        query = self.model.find(Source_db.tags.in_(tags), session=self.session)
        return await query.skip(skip).limit(limit).to_list()
