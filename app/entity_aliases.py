import re
from typing import Iterable, TypeVar


T = TypeVar("T")


GROUP_ALIASES = {
    "i-dle": {
        "(g)i-dle",
        "(g) i-dle",
        "g i-dle",
        "g-idle",
        "gidle",
        "i-dle",
    },
}


def normalize_entity_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def compact_entity_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_entity_name(name))


def canonical_group_name(name: str) -> str:
    normalized = normalize_entity_name(name)
    compact = compact_entity_name(name)
    for canonical, aliases in GROUP_ALIASES.items():
        if normalized == canonical or normalized in aliases:
            return canonical
        if compact == compact_entity_name(canonical):
            return canonical
        if compact in {compact_entity_name(alias) for alias in aliases}:
            return canonical
    return name.strip()


def group_alias_candidates(name: str) -> list[str]:
    canonical = canonical_group_name(name)
    aliases = GROUP_ALIASES.get(canonical, set())
    candidates = [canonical, *sorted(aliases), name.strip()]
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def canonicalize_group_mentions(group_names: Iterable[str]) -> list[str]:
    seen = set()
    canonical_names = []
    for group_name in group_names:
        canonical = canonical_group_name(group_name)
        key = compact_entity_name(canonical)
        if key in seen:
            continue
        seen.add(key)
        canonical_names.append(canonical)
    return canonical_names


def dedupe_groups_by_canonical_name(groups: Iterable[T]) -> list[T]:
    deduped: dict[str, T] = {}
    for group in groups:
        name = getattr(group, "name", "")
        canonical = canonical_group_name(name)
        key = compact_entity_name(canonical)
        existing = deduped.get(key)
        if existing is None or _should_replace_group(existing, group, canonical):
            setattr(group, "name", canonical)
            deduped[key] = group
    return list(deduped.values())


def dedupe_artists_by_identity(artists: Iterable[T]) -> list[T]:
    deduped: dict[str, T] = {}
    for artist in artists:
        wikidata_id = getattr(artist, "wikidata_id", None)
        canonical_name = getattr(artist, "canonical_name", None) or getattr(
            artist,
            "name",
            "",
        )
        key = f"wiki:{wikidata_id}" if wikidata_id else f"name:{compact_entity_name(canonical_name)}"
        existing = deduped.get(key)
        if existing is None or _should_replace_artist(existing, artist):
            if canonical_name:
                setattr(artist, "name", canonical_name)
            deduped[key] = artist
    return list(deduped.values())


def _should_replace_group(existing: T, candidate: T, canonical: str) -> bool:
    existing_has_wiki = bool(getattr(existing, "wikidata_id", None))
    candidate_has_wiki = bool(getattr(candidate, "wikidata_id", None))
    if candidate_has_wiki and not existing_has_wiki:
        return True
    if existing_has_wiki and not candidate_has_wiki:
        return False

    existing_exact = normalize_entity_name(getattr(existing, "name", "")) == normalize_entity_name(
        canonical
    )
    candidate_exact = normalize_entity_name(getattr(candidate, "name", "")) == normalize_entity_name(
        canonical
    )
    if candidate_exact and not existing_exact:
        return True

    existing_alias_count = len(getattr(existing, "aliases", []) or [])
    candidate_alias_count = len(getattr(candidate, "aliases", []) or [])
    return candidate_alias_count > existing_alias_count


def _should_replace_artist(existing: T, candidate: T) -> bool:
    existing_has_wiki = bool(getattr(existing, "wikidata_id", None))
    candidate_has_wiki = bool(getattr(candidate, "wikidata_id", None))
    if candidate_has_wiki and not existing_has_wiki:
        return True
    if existing_has_wiki and not candidate_has_wiki:
        return False

    existing_alias_count = len(getattr(existing, "aliases", []) or [])
    candidate_alias_count = len(getattr(candidate, "aliases", []) or [])
    if candidate_alias_count != existing_alias_count:
        return candidate_alias_count > existing_alias_count

    existing_tag_count = len(getattr(existing, "tags", []) or [])
    candidate_tag_count = len(getattr(candidate, "tags", []) or [])
    return candidate_tag_count > existing_tag_count
