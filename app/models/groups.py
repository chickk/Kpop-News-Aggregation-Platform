from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class GroupGenerated(BaseModel):
    bio: str
    formed: date
    disbanded: Optional[date]
    is_active: bool
    language: str
    countries: List[str]
    tags: List[str]


class Group(GroupGenerated):
    name: str
    artist_ids: List[str]
