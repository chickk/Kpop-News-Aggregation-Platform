from app.article_search import (
    article_matches_primary_terms,
    build_case_insensitive_tags_filter,
    build_news_fetch_plans,
    build_article_search_filter,
    resolve_auto_process_concurrency,
    resolve_auto_process_limit,
    should_auto_fetch_articles,
    sort_articles_by_relevance,
)
from app.models.articles import RawArticle
from app.models.sources import RawSource


def test_article_search_filter_matches_title_and_text():
    search_filter = build_article_search_filter("NMIXX")

    assert search_filter == {
        "$or": [
            {"title": {"$regex": "NMIXX", "$options": "i"}},
            {"text": {"$regex": "NMIXX", "$options": "i"}},
        ]
    }


def test_case_insensitive_tags_filter_matches_exact_tags():
    assert build_case_insensitive_tags_filter(["K-pop", "tour"]) == {
        "$and": [
            {"tags": {"$regex": "^K\\-pop$", "$options": "i"}},
            {"tags": {"$regex": "^tour$", "$options": "i"}},
        ]
    }


def test_article_matches_primary_terms_case_insensitive():
    raw_article = RawArticle(
        title="Singapore concert calendar",
        text="K-pop girl group NMixx will perform at The Star Theatre.",
        url="https://example.com/nmixx",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["NMIXX"])


def test_article_matches_primary_terms_ignores_generic_kpop_term():
    raw_article = RawArticle(
        title="Tour dates announced",
        text="K-pop concerts are scheduled this month.",
        url="https://example.com/kpop",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["K-pop"])


def test_article_matches_primary_terms_accepts_late_mentions():
    raw_article = RawArticle(
        title="Singapore concert calendar",
        text=f"{'General concert listings. ' * 80}NMixx will also perform later.",
        url="https://example.com/calendar",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["NMIXX"])


def test_ambiguous_idol_term_requires_context():
    raw_article = RawArticle(
        title="Scores twice in the second half",
        text="The striker scored twice in a comeback win once the second half started.",
        url="https://example.com/sports",
        raw_source=RawSource(title="Example"),
    )

    assert not article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_rejects_once_as_context():
    raw_article = RawArticle(
        title="Take this medication twice daily",
        text="Patients should take one tablet once in the morning and once at night.",
        url="https://example.com/medicine",
        raw_source=RawSource(title="Example"),
    )

    assert not article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_accepts_kpop_context():
    raw_article = RawArticle(
        title="TWICE announces new tour dates",
        text="The K-pop group will begin a new world tour this summer.",
        url="https://example.com/twice",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_accepts_mixed_case_title_with_music_context():
    raw_article = RawArticle(
        title="Twice announces new concert dates",
        text="Fans are preparing for the group's next stage.",
        url="https://example.com/twice-concert",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_rejects_lowercase_usage_even_with_kpop_context():
    raw_article = RawArticle(
        title='"Big 4" Girl Group Suffers Catastrophic Drop In Album Sales',
        text='The K-pop girl group sold almost twice as many copies on a previous release.',
        url="https://example.com/lowercase-twice",
        raw_source=RawSource(title="Example"),
    )

    assert not article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_accepts_named_group_usage_in_body():
    raw_article = RawArticle(
        title="KPop Demon Hunters era winds down",
        text="The real-life KPop group Twice wrapped up its tour this week.",
        url="https://example.com/group-twice",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_rejects_uppercase_non_music_title():
    raw_article = RawArticle(
        title="Striker Scores TWICE In Comeback Win",
        text="The football match changed in the second half.",
        url="https://example.com/twice-sports",
        raw_source=RawSource(title="Example"),
    )

    assert not article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_rejects_non_music_fan_context():
    raw_article = RawArticle(
        title='Twice the Love, Twice the Joy',
        text="The actor thanked fans after becoming a mother to twins via surrogacy.",
        url="https://example.com/twice-family",
        raw_source=RawSource(title="Example"),
    )

    assert not article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_accepts_exact_body_name_near_context():
    raw_article = RawArticle(
        title="K-pop awards announced",
        text="Several K-pop artists were nominated, including TWICE and BTS.",
        url="https://example.com/kpop-awards",
        raw_source=RawSource(title="Example"),
    )

    assert article_matches_primary_terms(raw_article, ["TWICE"])


def test_ambiguous_idol_term_rejects_distant_page_context():
    raw_article = RawArticle(
        title="My nan taught me to knit at 18 and now I'm in Vogue",
        text=f"She tried the pattern twice before finishing it. {'Filler text. ' * 80} Related K-pop headlines appear below.",
        url="https://example.com/knitting",
        raw_source=RawSource(title="Example"),
    )

    assert not article_matches_primary_terms(raw_article, ["TWICE"])


def test_news_fetch_plans_do_not_add_generic_kpop_or_for_ambiguous_terms():
    plans = build_news_fetch_plans(["TWICE"])

    assert plans == [
        {
            "concepts": True,
            "query_terms": ["http://en.wikipedia.org/wiki/Twice_(group)"],
            "sort_by": "rel",
        },
    ]


def test_news_fetch_plans_mix_known_concepts_and_keyword_terms():
    plans = build_news_fetch_plans(["TWICE", "NMIXX"])

    assert plans == [
        {
            "concepts": True,
            "query_terms": ["http://en.wikipedia.org/wiki/Twice_(group)"],
            "sort_by": "rel",
        },
        {"concepts": False, "query_terms": ["nmixx"], "keyword_locs": ["title"], "sort_by": "rel"},
        {"concepts": False, "query_terms": ["nmixx"], "keyword_locs": ["body"], "sort_by": "rel"},
    ]


def test_news_fetch_plans_use_primary_terms_for_mixed_search():
    plans = build_news_fetch_plans(["NMIXX", "K-pop"])

    assert plans == [
        {"concepts": False, "query_terms": ["nmixx"], "keyword_locs": ["title"], "sort_by": "rel"},
        {"concepts": False, "query_terms": ["nmixx"], "keyword_locs": ["body"], "sort_by": "rel"},
    ]


def test_sort_articles_by_relevance_prioritizes_title_hits():
    body_match = RawArticle(
        title="Concert calendar",
        text="NMIXX will perform on Friday.",
        url="https://example.com/body",
        raw_source=RawSource(title="Example"),
    )
    title_match = RawArticle(
        title="NMIXX confirms festival appearance",
        text="The group will perform on Friday.",
        url="https://example.com/title",
        raw_source=RawSource(title="Example"),
    )

    assert sort_articles_by_relevance([body_match, title_match], ["NMIXX"]) == [
        title_match,
        body_match,
    ]


def test_auto_fetches_date_range_when_first_page_is_not_full():
    assert should_auto_fetch_articles(
        search="NMIXX",
        skip=0,
        current_count=3,
        limit=25,
        has_date_range=True,
        max_fetch_results=100,
    )


def test_does_not_auto_fetch_partial_page_without_date_range():
    assert not should_auto_fetch_articles(
        search="NMIXX",
        skip=0,
        current_count=3,
        limit=25,
        has_date_range=False,
        max_fetch_results=100,
    )


def test_auto_fetches_date_range_when_page_is_full_but_below_fetch_limit():
    assert should_auto_fetch_articles(
        search="TWICE",
        skip=0,
        current_count=25,
        limit=25,
        has_date_range=True,
        max_fetch_results=100,
    )


def test_auto_process_limit_defaults_to_page_and_fetch_limit():
    assert resolve_auto_process_limit(
        page_limit=25,
        max_fetch_results=25,
        configured_limit=None,
    ) == 25


def test_auto_process_limit_respects_configured_value():
    assert resolve_auto_process_limit(
        page_limit=25,
        max_fetch_results=25,
        configured_limit="3",
    ) == 3


def test_auto_process_concurrency_defaults_to_four():
    assert resolve_auto_process_concurrency(None) == 4


def test_auto_process_concurrency_respects_configured_value():
    assert resolve_auto_process_concurrency("8") == 8
