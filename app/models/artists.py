from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional


class ArtistGenerated(BaseModel):
    """
    Data model to generate for a given artist
    """

    bio: str = Field(
        ...,
        description="One to two paragraph description of the artist. It should read like a wikipedia article or a spotify bio and include information on groups they're in.",
    )
    career_start: date = Field(
        description="Year that the artist became active, if unknown use the date of their first album"
    )
    is_active: bool = Field(
        default=True,
        description="Is this artist still actively touring or making music? or have they retired",
    )
    retirement_date: Optional[date] = Field(
        default=None,
        description="If the artist is no longer active, include the date they retired",
    )
    in_groups: bool = Field(
        default=False,
        description="Is this artist apart of any groups or bands? or have they been in the past",
    )
    group_names: List[str] = Field(
        default_factory=list,
        description="List of any groups or bands this artist has ever been a part of.",
    )

    language: str = Field(
        default="en", description="Primary language this artist performs in."
    )
    countries: List[str] = Field(
        default_factory=list,
        description="List of countries this artist is from or lives in. Justin Bieber -> ['canada', 'united states of america']",
    )
    tags: List[str] = Field(
        default_factory=list, description="List of tags associated with the artist"
    )


class Artist(ArtistGenerated):
    """
    Data model for artists
    """

    name: str
    group_ids: List[str] = Field(default_factory=list)
