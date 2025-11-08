from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field


class Event(BaseModel):
    title: str
    description: str
    event_date: datetime
    article_ids: List[str]
    article_count: int = 0
    artist_ids: List[str]
    group_ids: List[str]
    tags: List[str]
    countries: List[str]
    avg_sentiment: float