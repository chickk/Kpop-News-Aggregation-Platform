from types import SimpleNamespace

from app.entity_aliases import (
    canonical_group_name,
    canonicalize_group_mentions,
    dedupe_artists_by_identity,
    dedupe_groups_by_canonical_name,
    group_alias_candidates,
)


def test_canonical_group_name_maps_gidle_aliases_to_idle():
    assert canonical_group_name("(G)I-DLE") == "i-dle"
    assert canonical_group_name("GIDLE") == "i-dle"
    assert canonical_group_name("i-dle") == "i-dle"


def test_group_alias_candidates_include_old_and_new_names():
    assert "i-dle" in group_alias_candidates("(G)I-DLE")
    assert "(g)i-dle" in group_alias_candidates("(G)I-DLE")


def test_canonicalize_group_mentions_dedupes_aliases():
    assert canonicalize_group_mentions(["(G)I-DLE", "i-dle", "NMIXX"]) == [
        "i-dle",
        "NMIXX",
    ]


def test_dedupe_groups_by_canonical_name_prefers_canonical_name():
    groups = [
        SimpleNamespace(name="(G)I-DLE"),
        SimpleNamespace(name="i-dle"),
        SimpleNamespace(name="NMIXX"),
    ]

    deduped = dedupe_groups_by_canonical_name(groups)

    assert [group.name for group in deduped] == ["i-dle", "NMIXX"]


def test_dedupe_groups_by_canonical_name_prefers_enriched_group():
    groups = [
        SimpleNamespace(name="i-dle", wikidata_id=None, aliases=[]),
        SimpleNamespace(name="(G)I-DLE", wikidata_id="Q51885404", aliases=["(G)I-DLE"]),
    ]

    deduped = dedupe_groups_by_canonical_name(groups)

    assert len(deduped) == 1
    assert deduped[0].name == "i-dle"
    assert deduped[0].wikidata_id == "Q51885404"


def test_dedupe_artists_by_identity_prefers_single_wikidata_entity():
    artists = [
        SimpleNamespace(
            name="SULLYOON",
            canonical_name="Sullyoon",
            wikidata_id="Q109307956",
            aliases=[],
            tags=["K-pop"],
        ),
        SimpleNamespace(
            name="Sullyoon",
            canonical_name="Sullyoon",
            wikidata_id="Q109307956",
            aliases=["Seol Yun-a"],
            tags=["K-pop", "NMIXX"],
        ),
    ]

    deduped = dedupe_artists_by_identity(artists)

    assert len(deduped) == 1
    assert deduped[0].name == "Sullyoon"
    assert deduped[0].aliases == ["Seol Yun-a"]
