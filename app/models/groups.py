from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class GroupGenerated(BaseModel):
    """Data to generate for the given musical group or band"""

    bio: str = Field(
        ...,
        description="One to two paragraph description of the artist. It should read like a wikipedia article or a spotify bio",
    )
    formed: date = Field(
        description="Year that the group or banded formed, if unknown use the date of their first album"
    )
    is_active: bool = Field(
        default=True,
        description="Is this group still actively touring or making music? or have they retired/disbanded",
    )
    disbanded: Optional[date] = Field(
        default=None,
        description="If the group are no longer active, include the date they disbanded",
    )

    language: List[str] = Field(
        default_factory=list,
        description="List of languages that this band performs in. List all languages if multi lingual",
    )

    countries: List[str] = Field(
        default_factory=list,
        description="List of countries this group is from. Include all if multiple,  three letter ISO code",
    )
    tags: List[str] = Field(
        default_factory=list, description="List of tags associated with the group"
    )
    member_artists: List[str] = Field(
        default_factory=list,
        description="List all current and past members of the group or band",
    )


class Group(GroupGenerated):
    name: str
    artist_ids: List[str] = Field(default_factory=list)
    canonical_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    image_url: Optional[str] = None
    external_ids: Dict[str, str] = Field(default_factory=dict)
    entity_confidence: Optional[float] = None
    needs_review: bool = False
    last_enriched_at: Optional[datetime] = None
    entity_type: Optional[str] = None
