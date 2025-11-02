from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    name: str
    bio: str
    formed: date
    language: str
    countries: List[str]
    tags: List[str]
