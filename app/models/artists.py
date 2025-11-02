from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional


class ArtistGenerated(BaseModel):
    """
    Data model for artists
    """

    bio: str
    career_start: date
    retirement_date: Optional[date]
    is_active: bool
    language: str
    countries: List[str]
    tags: List[str]


class Artist(ArtistGenerated):
    """
    Data model for artists
    """

    name: str
    group_ids: List[str]
