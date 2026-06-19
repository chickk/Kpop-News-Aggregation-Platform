from datetime import date

import pytest

from app.entity_enrichment.resolver import WikiEntityResolver
from app.models.artists import Artist
from app.models.groups import Group


class FakeWikiClient:
    async def search_entities(self, query, *, language="en", limit=5):
        return [
            {
                "id": "Q49219519",
                "label": "I-dle",
                "description": "South Korean girl group",
            }
        ]

    async def get_entities(self, ids, *, languages="en|ko|zh"):
        return {
            "Q49219519": {
                "id": "Q49219519",
                "labels": {"en": {"value": "I-dle"}},
                "descriptions": {"en": {"value": "South Korean girl group"}},
                "aliases": {
                    "en": [
                        {"value": "(G)I-DLE"},
                        {"value": "GIDLE"},
                    ]
                },
                "claims": {
                    "P31": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q5741069"},
                                }
                            }
                        }
                    ],
                    "P495": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q884"},
                                }
                            }
                        }
                    ],
                    "P434": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": "musicbrainz-id",
                                }
                            }
                        }
                    ],
                },
                "sitelinks": {"enwiki": {"title": "I-dle"}},
            }
        }


class UnrelatedWikiClient:
    async def search_entities(self, query, *, language="en", limit=5):
        return [
            {
                "id": "Q1",
                "label": "Twice",
                "description": "concept in mathematics",
            }
        ]

    async def get_entities(self, ids, *, languages="en|ko|zh"):
        return {
            "Q1": {
                "id": "Q1",
                "labels": {"en": {"value": "Twice"}},
                "descriptions": {"en": {"value": "concept in mathematics"}},
                "aliases": {"en": []},
                "claims": {},
                "sitelinks": {},
            }
        }


class FakeArtistWikiClient:
    async def search_entities(self, query, *, language="en", limit=5):
        return [
            {
                "id": "Q999",
                "label": "Sullyoon",
                "description": "South Korean singer",
            }
        ]

    async def get_entities(self, ids, *, languages="en|ko|zh"):
        return {
            "Q999": {
                "id": "Q999",
                "labels": {"en": {"value": "Sullyoon"}},
                "descriptions": {"en": {"value": "South Korean singer"}},
                "aliases": {"en": [{"value": "Seol Yoon-a"}]},
                "claims": {
                    "P31": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q5"},
                                }
                            }
                        }
                    ],
                    "P106": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q177220"},
                                }
                            }
                        }
                    ],
                    "P27": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q884"},
                                }
                            }
                        }
                    ],
                    "P463": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q109307762"},
                                }
                            }
                        }
                    ],
                },
                "sitelinks": {"enwiki": {"title": "Sullyoon"}},
            }
        }


class FakeNonPerformerHumanWikiClient:
    async def search_entities(self, query, *, language="en", limit=5):
        return [
            {
                "id": "Q302",
                "label": "Jesus Christ",
                "description": "central figure of Christianity",
            }
        ]

    async def get_entities(self, ids, *, languages="en|ko|zh"):
        return {
            "Q302": {
                "id": "Q302",
                "labels": {"en": {"value": "Jesus Christ"}},
                "descriptions": {"en": {"value": "central figure of Christianity"}},
                "aliases": {"en": [{"value": "Jesus of Nazareth"}]},
                "claims": {
                    "P31": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q5"},
                                }
                            }
                        }
                    ],
                },
                "sitelinks": {"enwiki": {"title": "Jesus"}},
            }
        }


class FakeGroupAsArtistWikiClient(FakeWikiClient):
    pass


def group(name: str) -> Group:
    return Group(
        name=name,
        bio=f"{name} was mentioned in recent music news coverage.",
        formed=date(2026, 1, 1),
        is_active=True,
        language=["en"],
        countries=[],
        tags=[],
        member_artists=[],
        artist_ids=[],
    )


def artist(name: str) -> Artist:
    return Artist(
        name=name,
        bio=f"{name} was mentioned in recent music news coverage.",
        career_start=date(2026, 1, 1),
        is_active=True,
        language="en",
        countries=[],
        tags=[],
        group_ids=[],
    )


@pytest.mark.asyncio
async def test_resolver_enriches_group_from_wikidata():
    resolver = WikiEntityResolver(
        client=FakeWikiClient(),
        enabled=True,
        min_confidence=0.65,
    )

    enriched = await resolver.enrich_group(group("(G)I-DLE"))

    assert enriched.name == "i-dle"
    assert enriched.canonical_name == "i-dle"
    assert enriched.wikidata_id == "Q49219519"
    assert enriched.wikipedia_url == "https://en.wikipedia.org/wiki/I-dle"
    assert "(G)I-DLE" in enriched.aliases
    assert enriched.external_ids["musicbrainz"] == "musicbrainz-id"
    assert enriched.needs_review is False


@pytest.mark.asyncio
async def test_resolver_ignores_low_confidence_group_candidate():
    resolver = WikiEntityResolver(
        client=UnrelatedWikiClient(),
        enabled=True,
        min_confidence=0.65,
    )

    enriched = await resolver.enrich_group(group("Twice"))

    assert enriched.name == "Twice"
    assert enriched.wikidata_id is None


@pytest.mark.asyncio
async def test_resolver_enriches_artist_from_wikidata():
    resolver = WikiEntityResolver(
        client=FakeArtistWikiClient(),
        enabled=True,
        min_confidence=0.65,
    )

    enriched = await resolver.enrich_artist(artist("Sullyoon"))

    assert enriched.name == "Sullyoon"
    assert enriched.canonical_name == "Sullyoon"
    assert enriched.wikidata_id == "Q999"
    assert enriched.wikipedia_url == "https://en.wikipedia.org/wiki/Sullyoon"
    assert "Seol Yoon-a" in enriched.aliases
    assert enriched.member_of_wikidata_ids == ["Q109307762"]


@pytest.mark.asyncio
async def test_resolver_rejects_non_performer_human_as_artist():
    resolver = WikiEntityResolver(
        client=FakeNonPerformerHumanWikiClient(),
        enabled=True,
        min_confidence=0.65,
    )

    enriched = await resolver.enrich_artist(artist("Jesus Christ"))

    assert enriched.name == "Jesus Christ"
    assert enriched.wikidata_id is None


@pytest.mark.asyncio
async def test_resolver_rejects_group_as_artist():
    resolver = WikiEntityResolver(
        client=FakeGroupAsArtistWikiClient(),
        enabled=True,
        min_confidence=0.65,
    )

    enriched = await resolver.enrich_artist(artist("(G)I-DLE"))

    assert enriched.name == "(G)I-DLE"
    assert enriched.wikidata_id is None


@pytest.mark.asyncio
async def test_resolver_rejects_solo_singer_as_group():
    resolver = WikiEntityResolver(
        client=FakeArtistWikiClient(),
        enabled=True,
        min_confidence=0.65,
    )

    entity = await resolver.resolve_group("Sullyoon")

    assert entity is None
