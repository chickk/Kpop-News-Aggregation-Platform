import logging
import os
import re
from datetime import datetime

from app.entity_aliases import (
    canonical_group_name,
    compact_entity_name,
    group_alias_candidates,
    normalize_entity_name,
)
from app.entity_enrichment.models import WikiEntity
from app.entity_enrichment.scoring import (
    build_artist_entity,
    build_group_entity,
    score_artist_candidate,
    score_group_candidate,
)
from app.entity_enrichment.wiki_client import WikidataClient
from app.interfaces.unit_of_work import IUnitOfWork
from app.models.artists import Artist
from app.models.groups import Group


logger = logging.getLogger(__name__)


class WikiEntityResolver:
    def __init__(
        self,
        *,
        client: WikidataClient | None = None,
        enabled: bool | None = None,
        min_confidence: float | None = None,
    ):
        self.client = client or WikidataClient()
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("WIKI_ENRICHMENT_ENABLED", "false").strip().lower()
            in {"1", "true", "yes"}
        )
        self.min_confidence = (
            min_confidence
            if min_confidence is not None
            else float(os.getenv("WIKI_GROUP_MIN_CONFIDENCE", "0.65"))
        )
        self.min_artist_confidence = float(
            os.getenv("WIKI_ARTIST_MIN_CONFIDENCE", str(self.min_confidence))
        )

    async def find_existing_group(self, uow: IUnitOfWork, name: str) -> Group | None:
        aliases = group_alias_candidates(name)
        exact_name_filters = []
        for alias in aliases:
            exact_pattern = f"^{re.escape(alias)}$"
            exact_name_filters.extend(
                [
                    {"name": {"$regex": exact_pattern, "$options": "i"}},
                    {"canonical_name": {"$regex": exact_pattern, "$options": "i"}},
                    {"aliases": {"$regex": exact_pattern, "$options": "i"}},
                ]
            )

        groups = await uow.groups.get_all(filters={"$or": exact_name_filters}, limit=1)
        return groups[0] if groups else None

    async def find_existing_group_by_wikidata_id(
        self,
        uow: IUnitOfWork,
        wikidata_id: str | None,
    ) -> Group | None:
        if not wikidata_id:
            return None
        groups = await uow.groups.get_all(
            filters={"wikidata_id": wikidata_id},
            limit=1,
        )
        return groups[0] if groups else None

    async def find_existing_artist(self, uow: IUnitOfWork, name: str) -> Artist | None:
        exact_pattern = f"^{re.escape(name)}$"
        artists = await uow.artists.get_all(
            filters={
                "$or": [
                    {"name": {"$regex": exact_pattern, "$options": "i"}},
                    {"canonical_name": {"$regex": exact_pattern, "$options": "i"}},
                    {"aliases": {"$regex": exact_pattern, "$options": "i"}},
                ]
            },
            limit=1,
        )
        return artists[0] if artists else None

    async def find_existing_artist_by_wikidata_id(
        self,
        uow: IUnitOfWork,
        wikidata_id: str | None,
    ) -> Artist | None:
        if not wikidata_id:
            return None
        artists = await uow.artists.get_all(
            filters={"wikidata_id": wikidata_id},
            limit=1,
        )
        return artists[0] if artists else None

    async def enrich_group(self, group: Group, original_name: str | None = None) -> Group:
        original_name = original_name or group.name
        group.name = canonical_group_name(group.name)
        group.canonical_name = group.canonical_name or group.name

        if not self.enabled:
            return group

        wiki_entity = await self.resolve_group(original_name)
        if wiki_entity is None:
            return group

        return apply_group_enrichment(group, wiki_entity, original_name)

    def should_enrich_group(self, group: Group) -> bool:
        return self.enabled and not getattr(group, "wikidata_id", None)

    async def enrich_artist(
        self,
        artist: Artist,
        original_name: str | None = None,
    ) -> Artist:
        original_name = original_name or artist.name
        artist.canonical_name = artist.canonical_name or artist.name

        if not self.enabled:
            return artist

        wiki_entity = await self.resolve_artist(original_name)
        if wiki_entity is None:
            return artist

        return apply_artist_enrichment(artist, wiki_entity, original_name)

    def should_enrich_artist(self, artist: Artist) -> bool:
        return self.enabled and not getattr(artist, "wikidata_id", None)

    async def resolve_group(self, name: str) -> WikiEntity | None:
        return await self._resolve_entity(
            name=name,
            scorer=score_group_candidate,
            builder=build_group_entity,
            min_confidence=self.min_confidence,
            log_label="group",
        )

    async def resolve_artist(self, name: str) -> WikiEntity | None:
        return await self._resolve_entity(
            name=name,
            scorer=score_artist_candidate,
            builder=build_artist_entity,
            min_confidence=self.min_artist_confidence,
            log_label="artist",
        )

    async def _resolve_entity(
        self,
        *,
        name: str,
        scorer,
        builder,
        min_confidence: float,
        log_label: str,
    ) -> WikiEntity | None:
        try:
            search_results = await self.client.search_entities(name, limit=5)
            ids = [
                result.get("id")
                for result in search_results
                if result.get("id")
            ]
            entities = await self.client.get_entities(ids)
        except Exception as exc:
            logger.warning("Wikidata %s enrichment failed for %r: %s", log_label, name, exc)
            return None

        scored_entities = []
        for search_result in search_results:
            entity = entities.get(search_result.get("id"))
            if not entity or entity.get("missing"):
                continue
            confidence = scorer(name, search_result, entity)
            scored_entities.append((confidence, search_result, entity))

        if not scored_entities:
            return None

        confidence, search_result, entity = max(
            scored_entities,
            key=lambda item: item[0],
        )
        if confidence < min_confidence:
            return None

        return builder(
            search_result=search_result,
            entity=entity,
            confidence=confidence,
            threshold=min_confidence,
        )


def apply_group_enrichment(
    group: Group,
    wiki_entity: WikiEntity,
    original_name: str,
) -> Group:
    previous_names = [original_name, group.name, group.canonical_name or ""]
    manual_canonical_name = canonical_group_name(original_name)
    wiki_canonical_name = wiki_entity.canonical_name or group.name
    canonical_name = (
        manual_canonical_name
        if compact_entity_name(manual_canonical_name)
        == compact_entity_name(wiki_canonical_name)
        else wiki_canonical_name
    )
    group.name = canonical_name
    group.canonical_name = canonical_name
    group.wikidata_id = wiki_entity.wikidata_id or group.wikidata_id
    group.wikipedia_url = wiki_entity.wikipedia_url or group.wikipedia_url
    group.image_url = wiki_entity.image_url or group.image_url
    group.entity_type = "group"
    group.entity_confidence = wiki_entity.confidence
    group.needs_review = wiki_entity.needs_review
    group.last_enriched_at = datetime.now()

    merged_aliases = [
        alias
        for alias in [
            *group.aliases,
            *wiki_entity.aliases,
            *previous_names,
        ]
        if alias and normalize_entity_name(alias) != normalize_entity_name(group.name)
    ]
    group.aliases = list(dict.fromkeys(merged_aliases))
    group.external_ids.update(wiki_entity.external_ids)

    if wiki_entity.description and (
        not group.bio
        or "was mentioned in recent music news coverage" in group.bio
    ):
        group.bio = wiki_entity.description

    return group


def apply_artist_enrichment(
    artist: Artist,
    wiki_entity: WikiEntity,
    original_name: str,
) -> Artist:
    previous_names = [original_name, artist.name, artist.canonical_name or ""]
    artist.name = wiki_entity.canonical_name or artist.name
    artist.canonical_name = wiki_entity.canonical_name or artist.name
    artist.wikidata_id = wiki_entity.wikidata_id or artist.wikidata_id
    artist.wikipedia_url = wiki_entity.wikipedia_url or artist.wikipedia_url
    artist.image_url = wiki_entity.image_url or artist.image_url
    artist.entity_type = "artist"
    artist.member_of_wikidata_ids = wiki_entity.related_wikidata_ids.get("member_of", [])
    artist.entity_confidence = wiki_entity.confidence
    artist.needs_review = wiki_entity.needs_review
    artist.last_enriched_at = datetime.now()

    merged_aliases = [
        alias
        for alias in [
            *artist.aliases,
            *wiki_entity.aliases,
            *previous_names,
        ]
        if alias and normalize_entity_name(alias) != normalize_entity_name(artist.name)
    ]
    artist.aliases = list(dict.fromkeys(merged_aliases))
    artist.external_ids.update(wiki_entity.external_ids)

    if wiki_entity.description and (
        not artist.bio
        or "was mentioned in recent music news coverage" in artist.bio
    ):
        artist.bio = wiki_entity.description

    return artist
