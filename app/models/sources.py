from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class RawSource(BaseModel):
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    country_code: Optional[str] = None


class SourceInput(BaseModel):
    title: str = Field(
        ..., description="Name of the publishing news org, blog, magazine etc"
    )
    description: Optional[str] = Field(description="Description of source if avaliable")
    language: Optional[str] = Field(description="Primary language of the source")
    country_code: Optional[str] = Field(
        description="Country code of primary location of source if available"
    )


class Source(BaseModel):
    name: str
    bio: str
    formed: date
    language: str
    countries: List[str]
    tags: List[str]
