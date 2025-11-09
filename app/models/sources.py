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
        description="Description of source if avaliable,"
    )
    language: Optional[str] = Field(description="Primary language of the source")
    country_code: Optional[str] = Field(
        description="Country code of primary location of source if available"
    )


class Source(BaseModel):
    """Source Data Model"""

    name: str = Field(description="Colloquial name of the publisher: BBC, CNN, etc")
    bio: str = Field(
        description="One Paragraph description of the publisher, should read like wikipedia"
    )
    formed: Optional[date] = Field(
        description="When was the publication founded? if known"
    )
    language: str = Field(description="What is the primary language of the publication")
    countries: List[str] = Field(
        description="List of countries the publciation is active in"
    )
    tags: List[str]
