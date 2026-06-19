from dataclasses import dataclass, field


@dataclass(frozen=True)
class WikiEntity:
    wikidata_id: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    wikipedia_url: str | None = None
    image_url: str | None = None
    external_ids: dict[str, str] = field(default_factory=dict)
    related_wikidata_ids: dict[str, list[str]] = field(default_factory=dict)
    confidence: float = 0.0
    needs_review: bool = False
