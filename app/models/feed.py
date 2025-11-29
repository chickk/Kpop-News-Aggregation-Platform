from pydantic import BaseModel

from app.models.articles import Article
from app.models.events import Event


class Feed(BaseModel):
    """Simple object to be returned by GET feeds"""

    feed_item: Event | Article
    is_article: bool = False

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(self.feed_item, Article):
            self.is_article = True
            