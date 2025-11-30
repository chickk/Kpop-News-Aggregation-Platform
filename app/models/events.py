from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
#from beanie import PydanticObjectId


class EventExtraction(BaseModel):
    title: str = Field(
        description="Short descriptive title of the event, ie 2025 Met Gala Reactions"
    )
    summary: str = Field(
        description="One Paragraph summary of the key happenings at the event"
    )
    synthesized_text: str = Field(
        description="Longer form synthesis of all text of articles or events that make up the event."
        " Should capture all the key details without being repetive."
    )
    event_date: datetime = Field(
        description="The date the event took place, if it took place over multiple days, either select the first date or the day of highest significance to the event"
    )


class Event(EventExtraction):
    article_ids: List[str] = Field(default_factory=list)
    article_count: int = Field(default=0)
    artist_ids: List[str] = Field(default_factory=list)
    group_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    avg_sentiment: float = Field(default=0.5)