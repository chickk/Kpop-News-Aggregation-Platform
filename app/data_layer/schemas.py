from datetime import datetime
import hashlib
from beanie import Document, Insert, Replace, Save, Update, before_event
from pydantic import model_validator
from pymongo import IndexModel, ASCENDING, TEXT
from typing import Optional
from pydantic import Field

from app.models.articles import Article
from app.models.artists import Artist
from app.models.events import Event
from app.models.groups import Group
from app.models.sources import Source


class BaseDocument(Document):

    # Updated to Optional, cause documents won't include these fields at the beginning, this will lead Pydantic ValidationError
    created: Optional[datetime] = Field(default=None)
    modified: Optional[datetime] = Field(default=None)

    @before_event(Insert)
    def set_time(self):
        # Still can cover "None" before inserting a document
        now = datetime.now()
        self.created = now
        self.modified = now

    @before_event([Update, Save])
    def update_modified_time(self):
        self.modified = datetime.now()


class Article_db(BaseDocument, Article):
    # DB needs
    article_hash: Optional[str] = Field(default=None) # Same issue as "created" and "modified"

    @model_validator(mode="after")
    def generate_hash_on_creation(self):
        """Generate article hash after model creation"""
        if not self.article_hash and self.text:
            self.article_hash = hashlib.sha256(self.text.encode()).hexdigest()
        return self

    @before_event([Insert, Replace])
    def generate_hash(self):
        """Generate article hash before saving"""
        if self.text:
            self.article_hash = hashlib.sha256(self.text.encode()).hexdigest()

    class Settings:
        name = "articles"
        indexes = [
            IndexModel([("title", ASCENDING)]),
            IndexModel([("url", ASCENDING)], unique=True),
            IndexModel([("article_hash", ASCENDING)], unique=True),
            IndexModel([("text", TEXT)]),
        ]


class Artist_db(BaseDocument, Artist):
    class Settings:
        name = "artists"
        indexes = [
            IndexModel([("name", ASCENDING)]), # Different artists may have same names
            IndexModel([("group_ids", ASCENDING)]), 
            IndexModel([("tags", ASCENDING)]), 
        ]


class Source_db(BaseDocument, Source):
    class Settings:
        name = "sources"
        indexes = [
            IndexModel([("name", ASCENDING)], unique=True), # Source name should be unique
            IndexModel([("language", ASCENDING)]),
            IndexModel([("countries", ASCENDING)]),
        ]



class Group_db(BaseDocument, Group):
    class Settings:
        name = "groups"
        indexes = [
            IndexModel([("name", ASCENDING)]), # Different groups may have same names
            IndexModel([("artist_ids", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
        ]


class Event_db(BaseDocument, Event):
    class Settings:
        name = "events"
        indexes = [
            IndexModel([("title", ASCENDING)]),
            IndexModel([("event_date", ASCENDING)]),
            IndexModel([("artist_ids", ASCENDING)]),
            IndexModel([("group_ids", ASCENDING)]),
            IndexModel([("article_ids", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("avg_sentiment", ASCENDING)]),
        ]
