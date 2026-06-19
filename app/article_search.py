import re
from typing import List

from app.models.articles import Article, RawArticle

GENERIC_SEARCH_TERMS = {"k-pop", "kpop", "idol", "idols"}
AMBIGUOUS_IDOL_TERMS = {"twice"}
IDOL_CONCEPT_TERMS = {
    "twice": "http://en.wikipedia.org/wiki/Twice_(group)",
}
IDOL_CONTEXT_PATTERNS = (
    r"\bk-?pop\b",
    r"\bkorean\b",
    r"\bgirl group\b",
    r"\bidols?\b",
    r"\bjyp\b",
    r"\balbum\b",
    r"\bconcert\b",
    r"\bmusic\b",
    r"\bstage\b",
    r"\btour\b",
)
IDOL_CONTEXT_WINDOW_CHARS = 600


def split_search_terms(search: str) -> List[str]:
    return [term.strip() for term in re.split(r"[,;]", search) if term.strip()]


def build_article_search_filter(search: str) -> dict:
    search_pattern = re.escape(search.strip())
    return {
        "$or": [
            {"title": {"$regex": search_pattern, "$options": "i"}},
            {"text": {"$regex": search_pattern, "$options": "i"}},
        ]
    }


def build_case_insensitive_tags_filter(tags: List[str]) -> dict:
    filters = [
        {"tags": {"$regex": f"^{re.escape(tag.strip())}$", "$options": "i"}}
        for tag in tags
        if tag.strip()
    ]
    return {"$and": filters} if filters else {}


def search_needs_idol_context(search_terms: List[str]) -> bool:
    return any(term.lower() in AMBIGUOUS_IDOL_TERMS for term in search_terms)


def text_has_idol_context(text: str) -> bool:
    normalized_text = text.lower()
    return any(re.search(pattern, normalized_text) for pattern in IDOL_CONTEXT_PATTERNS)


def text_has_nearby_idol_context(text: str, term: str) -> bool:
    for match in re.finditer(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
        matched_text = text[match.start() : match.end()]
        if matched_text.islower():
            continue
        start = max(0, match.start() - IDOL_CONTEXT_WINDOW_CHARS)
        end = min(len(text), match.end() + IDOL_CONTEXT_WINDOW_CHARS)
        if text_has_idol_context(text[start:end]):
            return True
    return False


def build_news_fetch_plans(search_terms: List[str]) -> List[dict]:
    concept_terms = [
        IDOL_CONCEPT_TERMS[term.lower()]
        for term in search_terms
        if term.lower() in IDOL_CONCEPT_TERMS
    ]
    keyword_terms = [
        term.lower()
        for term in primary_search_terms(search_terms)
        if term.lower() not in IDOL_CONCEPT_TERMS
    ]
    plans = []
    if concept_terms:
        plans.append(
            {
                "concepts": True,
                "query_terms": concept_terms,
                "sort_by": "rel",
            }
        )

    query_terms = keyword_terms or (
        [term.lower() for term in search_terms if term.strip()]
        if not concept_terms
        else []
    )
    if not query_terms:
        return plans

    plans.extend(
        [
            {
                "concepts": False,
                "query_terms": query_terms,
                "keyword_locs": ["title" for _ in query_terms],
                "sort_by": "rel",
            },
            {
                "concepts": False,
                "query_terms": query_terms,
                "keyword_locs": ["body" for _ in query_terms],
                "sort_by": "rel",
            },
        ]
    )
    return plans


def article_relevance_score(raw_article: RawArticle, search_terms: List[str]) -> tuple[int, int]:
    primary_terms = primary_search_terms(search_terms)
    if not primary_terms:
        return (0, 0)

    title = raw_article.title or ""
    text = raw_article.text or ""
    title_hits = sum(
        1
        for term in primary_terms
        if re.search(rf"\b{re.escape(term)}\b", title, flags=re.IGNORECASE)
    )
    body_hits = sum(
        1
        for term in primary_terms
        if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE)
    )
    if title_hits:
        return (0, -title_hits)
    if body_hits:
        return (1, -body_hits)
    return (2, 0)


def sort_articles_by_relevance(
    raw_articles: List[RawArticle],
    search_terms: List[str],
) -> List[RawArticle]:
    return sorted(raw_articles, key=lambda article: article_relevance_score(article, search_terms))


def should_auto_fetch_articles(
    search: str | None,
    skip: int,
    current_count: int,
    limit: int,
    has_date_range: bool,
    max_fetch_results: int,
) -> bool:
    if search is None or not search.strip() or skip != 0:
        return False
    if current_count == 0:
        return True
    return has_date_range and current_count < max(limit, max_fetch_results)


def resolve_auto_process_limit(
    page_limit: int,
    max_fetch_results: int,
    configured_limit: str | None,
) -> int:
    if configured_limit is not None and configured_limit.strip():
        return max(1, int(configured_limit))
    return max(1, min(max(page_limit, 1), max_fetch_results))


def resolve_auto_process_concurrency(configured_concurrency: str | None) -> int:
    if configured_concurrency is not None and configured_concurrency.strip():
        return max(1, int(configured_concurrency))
    return 4


def primary_search_terms(search_terms: List[str]) -> List[str]:
    return [
        term.lower()
        for term in search_terms
        if term.lower() not in GENERIC_SEARCH_TERMS
    ]


def text_matches_primary_terms(
    title: str,
    text: str,
    search_terms: List[str],
) -> bool:
    primary_terms = primary_search_terms(search_terms)
    if not primary_terms:
        return True

    normalized_title = title.lower()
    normalized_text = text.lower()
    relevant_text = f"{normalized_title} {normalized_text}"
    matching_terms = [term for term in primary_terms if term in relevant_text]
    if not matching_terms:
        return False
    if search_needs_idol_context(search_terms):
        combined_text = f"{title} {text}"
        return any(
            text_has_nearby_idol_context(combined_text, term)
            for term in matching_terms
        )
    return True


def article_matches_primary_terms(raw_article: RawArticle, search_terms: List[str]) -> bool:
    return text_matches_primary_terms(
        raw_article.title,
        raw_article.text,
        search_terms,
    )


def processed_article_matches_primary_terms(article: Article, search_terms: List[str]) -> bool:
    return text_matches_primary_terms(article.title, article.text, search_terms)


def summarize_without_llm(text: str, max_chars: int = 420) -> str:
    compact_text = " ".join(text.split())
    if len(compact_text) <= max_chars:
        return compact_text

    sentences = re.split(r"(?<=[.!?])\s+", compact_text)
    summary = ""
    for sentence in sentences:
        if not sentence:
            continue
        next_summary = f"{summary} {sentence}".strip()
        if len(next_summary) > max_chars:
            break
        summary = next_summary

    return summary or f"{compact_text[: max_chars - 1].rstrip()}..."


def tags_from_article(raw_article: RawArticle, search_terms: List[str]) -> List[str]:
    tags = {term.lower() for term in search_terms if term.strip()}
    text = f"{raw_article.title} {raw_article.text}".lower()
    keyword_tags = {
        "album": "album",
        "comeback": "comeback",
        "concert": "concert",
        "k-pop": "k-pop",
        "kpop": "k-pop",
        "tour": "tour",
    }
    for keyword, tag in keyword_tags.items():
        if keyword in text:
            tags.add(tag)
    return sorted(tags)


def article_from_raw_article(raw_article: RawArticle, search_terms: List[str]) -> Article:
    return Article(
        summary=summarize_without_llm(raw_article.text),
        sentiment=0.5,
        artists_mentioned=[],
        groups_mentioned=[],
        tags=tags_from_article(raw_article, search_terms),
        countries=(
            [raw_article.raw_source.country_code]
            if raw_article.raw_source and raw_article.raw_source.country_code
            else []
        ),
        title=raw_article.title,
        author=raw_article.author,
        source_id=raw_article.raw_source.title if raw_article.raw_source else "unknown",
        publication_date=raw_article.publication_date,
        text=raw_article.text,
        images=raw_article.image_urls,
        video=raw_article.video_url,
        language=raw_article.language or "en",
        in_event=False,
        event_id=None,
        groups_mentioned_ids=[],
        artists_mentioned_ids=[],
        url=raw_article.url,
    )
