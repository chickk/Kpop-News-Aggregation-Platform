from pydantic import BaseModel

from app.models.articles import Article
from app.models.events import Event


class Feed(BaseModel):
    """Simple object to be returned by GET feeds"""

    feed_item: Event | Article
