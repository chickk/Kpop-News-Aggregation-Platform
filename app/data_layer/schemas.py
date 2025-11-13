from datetime import datetime
import hashlib
from beanie import Document, Insert, Replace, Save, Update, before_event
from pydantic import model_validator
from pymongo import IndexModel, ASCENDING, TEXT

from app.models.articles import Article
from app.models.artists import Artist
from app.models.events import Event
from app.models.groups import Group
from app.models.sources import Source


class BaseDocument(Document):
    created: datetime
    modified: datetime

    @before_event(Insert)
    def set_time(self):
        self.created, self.modified = datetime.now()

    @before_event([Update, Save])
    def update_modified_time(self):
        self.modifed = datetime.now()


class Article_db(BaseDocument, Article):
    # DB needs
    article_hash: str

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


class Source_db(BaseDocument, Source):
    class Settings:
        name = "sources"


class Group_db(BaseDocument, Group):
    class Settings:
        name = "groups"


class Event_db(BaseDocument, Event):
    class Settings:
        name = "events"
