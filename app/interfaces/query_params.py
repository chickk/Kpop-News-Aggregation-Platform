from datetime import date, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class Filter(BaseModel):
    # Pagination
    limit: int = Field(default=25, gt=0, le=100)
    skip: int = Field(default=0, ge=0)


class CommonFilters(Filter):
    name: Optional[str] = Field(default=None, description="Name to filter to")
    country: Optional[str] = Field(
        default=None, description="Three letter ISO code of relavent countries"
    )
    tags: List[str] = Field(
        default_factory=list, description="List of tags to filter by"
    )


class ContentFilters(Filter):
    source_id: Optional[str] = Field(default=None, description="ObjectID of source")
    artist_id: Optional[str] = Field(default=None, description="ObjectID of artist")
    group_id: Optional[str] = Field(default=None, description="ObjectID of group")
    event_id: Optional[str] = Field(default=None, description="ObjectID of event")

    tags: List[str] = Field(
        default_factory=list, description="List of tags to filter by"
    )

    from_date: Optional[date] = Field(
        default=None, description="Filter to content published after this date"
    )
    to_date: Optional[date] = Field(
        default=None, description="Filter to content published before this date"
    )

    search: Optional[str] = Field(
        default=None, description="Search the article title and content"
    )


class ArtistFilters(CommonFilters):
    group_id: Optional[str] = Field(default=None, description="ObjectID of group")
    get_active: Optional[bool] = Field(
        default=None, description="filter to active arists only"
    )


class GroupFilters(CommonFilters):
    artist_id: Optional[str] = Field(default=None, description="ObjectID of artist")
    get_active: Optional[bool] = Field(
        default=None, description="filter to active groups only"
    )


class SourceFilters(CommonFilters):
    language: str = Field(
        default=None, description="Get sources in a specific language"
    )
