from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class RawSource(BaseModel):
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    country_code: Optional[str] = None


class SourceInput(BaseModel):
    """"""

    title: str = Field(
        ..., description="Name of the publishing news org, blog, magazine etc"
    )
    description: Optional[str] = Field(
        default=None, description="Description of source if avaliable,"
    )
    language: Optional[str] = Field(
        default=None, description="Primary language of the source"
    )
    country_code: Optional[str] = Field(
        default=None,
        description="Country code of primary location of source if available",
    )


class Source(BaseModel):
    """Source Data Model"""

    name: str = Field(description="Colloquial name of the publisher: BBC, CNN, etc")
    bio: str = Field(
        description="One Paragraph description of the publisher, should read like wikipedia"
    )
    formed: Optional[date] = Field(
        default=None, description="When was the publication founded? if known"
    )
    language: str = Field(default="en", description="What is the primary language of the publication")
    countries: List[str] = Field(
        default_factory=list, description="List of countries the publciation is active in"
    )
    tags: List[str] = Field(default_factory=list)
