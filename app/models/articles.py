from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.sources import RawSource


class RawArticle(BaseModel):
    """
    Raw article data from external sources (before processing).
    This is different from your Article model which has extracted/processed data.
    """

    title: str
    text: str
    url: str
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    raw_source: RawSource
    language: Optional[str] = None
    processed: bool = False
    image_urls: List[str] = []
    video_url: Optional[str] = None


class ArticleExtract(BaseModel):
    summary: str = Field(..., description="Short, one paragraph summary of the article")
    sentiment: float = Field(
        ...,
        description="Sentiment of the article, 0 for highly negative 1 for highly positive",
    )
    artists_mentioned: List[str] = Field(
        description="Pull any musical artists mentioned from the article",
        default_factory=list,
    )
    groups_mentioned: List[str] = Field(
        description="Pull any musical groups mentioned from the article",
        default_factory=list,
    )
    tags: List[str] = Field(
        description="List of potential tags for the article", default_factory=list
    )
    countries: List[str] = Field(
        description="List of countries referenced in the article", default_factory=list
    )


class Article(ArticleExtract):
    title: str
    author: Optional[str] = None
    source_id: str
    publication_date: Optional[datetime] = None
    text: str
    images: List[str] = []
    video: Optional[str] = None
    language: str
    in_event: bool = Field(default=False)
    event_id: Optional[str] = None
    groups_mentioned_ids: List[str]
    artists_mentioned_ids: List[str]
