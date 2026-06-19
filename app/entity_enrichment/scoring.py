from urllib.parse import quote

from app.entity_aliases import compact_entity_name, normalize_entity_name
from app.entity_enrichment.models import WikiEntity


GROUP_INSTANCE_QIDS = {
    "Q215380",  # musical group
    "Q5741069",  # girl group
    "Q641066",  # boy band
    "Q2088357",  # musical ensemble
}
GROUP_RELATED_QIDS = {
    "Q134556",  # single
    "Q482994",  # album
    "Q11424",  # film
    "Q5398426",  # television series
}
ARTIST_INSTANCE_QIDS = {
    "Q5",  # human
}
SOUTH_KOREA_QID = "Q884"
INSTANCE_OF_PID = "P31"
COUNTRY_OF_ORIGIN_PID = "P495"
COUNTRY_PID = "P17"
CITIZENSHIP_PID = "P27"
OCCUPATION_PID = "P106"
MEMBER_OF_PID = "P463"
IMAGE_PID = "P18"
MUSICBRAINZ_ARTIST_PID = "P434"
PERFORMER_OCCUPATION_QIDS = {
    "Q177220",  # singer
    "Q639669",  # musician
    "Q2252262",  # rapper
    "Q5716684",  # dancer
    "Q753110",  # songwriter
    "Q183945",  # record producer
}
PERFORMER_DESCRIPTION_TERMS = (
    "singer",
    "rapper",
    "dancer",
    "musician",
    "idol",
    "songwriter",
    "record producer",
    "k-pop",
)


def score_group_candidate(query: str, search_result: dict, entity: dict) -> float:
    label = _label(entity) or search_result.get("label", "")
    description = _description(entity) or search_result.get("description", "")
    aliases = _aliases(entity)
    candidate_names = [label, *aliases]

    query_key = compact_entity_name(query)
    score = 0.0

    if any(compact_entity_name(name) == query_key for name in candidate_names):
        score += 0.4
    elif any(query_key and query_key in compact_entity_name(name) for name in candidate_names):
        score += 0.2

    description_text = description.lower()
    instance_qids = set(_claim_entity_ids(entity, INSTANCE_OF_PID))
    group_description_terms = (
        "girl group",
        "boy band",
        "musical group",
        "music group",
        "band",
    )
    has_group_evidence = bool(instance_qids & GROUP_INSTANCE_QIDS) or any(
        phrase in description_text for phrase in group_description_terms
    )
    if not has_group_evidence:
        return 0.0

    if any(phrase in description_text for phrase in group_description_terms):
        score += 0.25

    if instance_qids & GROUP_INSTANCE_QIDS:
        score += 0.25
    if instance_qids & GROUP_RELATED_QIDS:
        score -= 0.35

    country_qids = set(_claim_entity_ids(entity, COUNTRY_OF_ORIGIN_PID))
    country_qids.update(_claim_entity_ids(entity, COUNTRY_PID))
    if SOUTH_KOREA_QID in country_qids:
        score += 0.1

    if _english_wikipedia_url(entity):
        score += 0.05

    return max(0.0, min(1.0, score))


def build_group_entity(
    *,
    search_result: dict,
    entity: dict,
    confidence: float,
    threshold: float,
) -> WikiEntity:
    label = _label(entity) or search_result.get("label") or ""
    aliases = _aliases(entity)
    wikipedia_url = _english_wikipedia_url(entity)
    image_file = _claim_string(entity, IMAGE_PID)
    external_ids = {}
    musicbrainz_id = _claim_string(entity, MUSICBRAINZ_ARTIST_PID)
    if musicbrainz_id:
        external_ids["musicbrainz"] = musicbrainz_id

    canonical_name = label.strip()
    all_aliases = [
        alias
        for alias in dict.fromkeys([*aliases, search_result.get("label", "")])
        if alias and normalize_entity_name(alias) != normalize_entity_name(canonical_name)
    ]

    return WikiEntity(
        wikidata_id=entity.get("id") or search_result.get("id") or "",
        canonical_name=canonical_name,
        aliases=all_aliases,
        description=_description(entity) or search_result.get("description", ""),
        wikipedia_url=wikipedia_url,
        image_url=_commons_image_url(image_file) if image_file else None,
        external_ids=external_ids,
        confidence=confidence,
        needs_review=confidence < threshold,
    )


def score_artist_candidate(query: str, search_result: dict, entity: dict) -> float:
    label = _label(entity) or search_result.get("label", "")
    description = _description(entity) or search_result.get("description", "")
    aliases = _aliases(entity)
    candidate_names = [label, *aliases]

    query_key = compact_entity_name(query)
    score = 0.0

    if any(compact_entity_name(name) == query_key for name in candidate_names):
        score += 0.4
    elif any(query_key and query_key in compact_entity_name(name) for name in candidate_names):
        score += 0.2

    description_text = description.lower()
    instance_qids = set(_claim_entity_ids(entity, INSTANCE_OF_PID))
    if instance_qids & GROUP_INSTANCE_QIDS:
        return 0.0

    occupation_qids = set(_claim_entity_ids(entity, OCCUPATION_PID))
    has_performer_evidence = bool(occupation_qids & PERFORMER_OCCUPATION_QIDS) or any(
        phrase in description_text for phrase in PERFORMER_DESCRIPTION_TERMS
    )
    if not has_performer_evidence:
        return 0.0

    if any(
        phrase in description_text
        for phrase in (
            "singer",
            "rapper",
            "dancer",
            "musician",
            "idol",
            "south korean",
            "k-pop",
            "korean",
        )
    ):
        score += 0.25

    if instance_qids & ARTIST_INSTANCE_QIDS:
        score += 0.2
    if instance_qids & GROUP_RELATED_QIDS:
        score -= 0.35

    if occupation_qids & PERFORMER_OCCUPATION_QIDS:
        score += 0.15

    country_qids = set(_claim_entity_ids(entity, COUNTRY_OF_ORIGIN_PID))
    country_qids.update(_claim_entity_ids(entity, COUNTRY_PID))
    country_qids.update(_claim_entity_ids(entity, CITIZENSHIP_PID))
    if SOUTH_KOREA_QID in country_qids:
        score += 0.1

    if _english_wikipedia_url(entity):
        score += 0.05

    return max(0.0, min(1.0, score))


def build_artist_entity(
    *,
    search_result: dict,
    entity: dict,
    confidence: float,
    threshold: float,
) -> WikiEntity:
    return _build_wiki_entity(
        search_result=search_result,
        entity=entity,
        confidence=confidence,
        threshold=threshold,
        related_wikidata_ids={
            "member_of": _claim_entity_ids(entity, MEMBER_OF_PID),
        },
    )


def _build_wiki_entity(
    *,
    search_result: dict,
    entity: dict,
    confidence: float,
    threshold: float,
    related_wikidata_ids: dict[str, list[str]] | None = None,
) -> WikiEntity:
    label = _label(entity) or search_result.get("label") or ""
    aliases = _aliases(entity)
    wikipedia_url = _english_wikipedia_url(entity)
    image_file = _claim_string(entity, IMAGE_PID)
    external_ids = {}
    musicbrainz_id = _claim_string(entity, MUSICBRAINZ_ARTIST_PID)
    if musicbrainz_id:
        external_ids["musicbrainz"] = musicbrainz_id

    canonical_name = label.strip()
    all_aliases = [
        alias
        for alias in dict.fromkeys([*aliases, search_result.get("label", "")])
        if alias and normalize_entity_name(alias) != normalize_entity_name(canonical_name)
    ]

    return WikiEntity(
        wikidata_id=entity.get("id") or search_result.get("id") or "",
        canonical_name=canonical_name,
        aliases=all_aliases,
        description=_description(entity) or search_result.get("description", ""),
        wikipedia_url=wikipedia_url,
        image_url=_commons_image_url(image_file) if image_file else None,
        external_ids=external_ids,
        related_wikidata_ids=related_wikidata_ids or {},
        confidence=confidence,
        needs_review=confidence < threshold,
    )


def _label(entity: dict, language: str = "en") -> str:
    return entity.get("labels", {}).get(language, {}).get("value", "")


def _description(entity: dict, language: str = "en") -> str:
    return entity.get("descriptions", {}).get(language, {}).get("value", "")


def _aliases(entity: dict, language: str = "en") -> list[str]:
    return [
        alias.get("value", "")
        for alias in entity.get("aliases", {}).get(language, [])
        if alias.get("value")
    ]


def _claim_entity_ids(entity: dict, property_id: str) -> list[str]:
    ids = []
    for claim in entity.get("claims", {}).get(property_id, []):
        value = (
            claim.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
        )
        qid = value.get("id") if isinstance(value, dict) else None
        if qid:
            ids.append(qid)
    return ids


def _claim_string(entity: dict, property_id: str) -> str | None:
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, str) and value:
            return value
    return None


def _english_wikipedia_url(entity: dict) -> str | None:
    title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    if not title:
        return None
    return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def _commons_image_url(filename: str) -> str:
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}"
