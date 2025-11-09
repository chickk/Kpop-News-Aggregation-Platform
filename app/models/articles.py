from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

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
        description="List of potential tags for the article", 
        default_factory=list
    )
    countries: List[str] = Field(
        description="List of countries referenced in the article", 
        default_factory=list
    )

class Article(ArticleExtract):
    title: str
    author: Optional[str]
    source_id: str
    publication_date: Optional[datetime]
    text: str
    language: str
    in_event: bool = Field(default=False)
    event_id: Optional[str]
    groups_mentioned_ids: List[str]
    artists_mentioned_ids: List[str]
