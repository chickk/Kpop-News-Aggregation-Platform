from types import SimpleNamespace

import pytest

from app.models.articles import ArticleExtract, RawArticle
from app.models.sources import RawSource
from app.pipeline.generators import NLPModule


class FakeArticleExtractor:
    def __init__(self, sentiment: float = 0.8, groups_mentioned: list[str] | None = None):
        self.calls = 0
        self.article_text = None
        self.sentiment = sentiment
        self.groups_mentioned = groups_mentioned or ["NMIXX"]

    async def aforward(self, article):
        self.calls += 1
        self.article_text = article.article_text
        return SimpleNamespace(
            article_output=ArticleExtract(
                summary="NMIXX announced a new comeback.",
                sentiment=self.sentiment,
                artists_mentioned=["Sullyoon"],
                groups_mentioned=self.groups_mentioned,
                tags=["comeback", "k-pop"],
                countries=["KOR"],
            )
        )


class FailingArticleExtractor:
    async def aforward(self, article):
        raise RuntimeError("LLM unavailable")


@pytest.fixture(autouse=True)
def reset_nlp_module(monkeypatch):
    NLPModule._article_extract_cache.clear()
    monkeypatch.setattr(NLPModule, "_artist_extractor", None)
    monkeypatch.setattr(NLPModule, "_article_extractor", None)
    monkeypatch.setattr(NLPModule, "_group_extractor", None)
    monkeypatch.setattr(NLPModule, "_source_extractor", None)
    monkeypatch.setattr(NLPModule, "_event_extractor", None)


@pytest.mark.asyncio
async def test_cheap_mode_processes_article_once_with_placeholder_entities(monkeypatch):
    fake_extractor = FakeArticleExtractor()
    raw_article = RawArticle(
        title="NMIXX announces comeback",
        text="NMIXX will release a new single next month with a full promotion cycle.",
        url="https://example.com/nmixx-comeback",
        raw_source=RawSource(
            title="Kpop Herald",
            description="Entertainment news",
            country_code="kor",
        ),
    )

    monkeypatch.setenv("NLP_MODE", "cheap")
    monkeypatch.setenv("NLP_ARTICLE_MAX_CHARS", "20")
    monkeypatch.setattr(NLPModule, "_article_extractor", fake_extractor)

    result = await NLPModule.generate_all_from_article(raw_article)

    assert fake_extractor.calls == 1
    assert fake_extractor.article_text == raw_article.text[:20]
    assert result.article.summary == "NMIXX announced a new comeback."
    assert result.article.artists_mentioned == ["Sullyoon"]
    assert result.article.groups_mentioned == ["NMIXX"]
    assert result.source.name == "Kpop Herald"
    assert result.source.bio == "Entertainment news"
    assert result.source.countries == ["KOR"]
    assert [artist.name for artist in result.new_artists] == ["Sullyoon"]
    assert result.new_artists[0].bio == "Sullyoon was mentioned in recent music news coverage."
    assert [group.name for group in result.new_groups] == ["NMIXX"]
    assert result.new_groups[0].bio == "NMIXX was mentioned in recent music news coverage."


@pytest.mark.asyncio
async def test_cheap_mode_canonicalizes_group_aliases(monkeypatch):
    fake_extractor = FakeArticleExtractor(groups_mentioned=["(G)I-DLE", "i-dle"])
    raw_article = RawArticle(
        title="i-dle announces comeback",
        text="The group formerly known as (G)I-DLE announced a new release.",
        url="https://example.com/idle-comeback",
        raw_source=RawSource(title="Kpop Herald"),
    )

    monkeypatch.setenv("NLP_MODE", "cheap")
    monkeypatch.setattr(NLPModule, "_article_extractor", fake_extractor)

    result = await NLPModule.generate_all_from_article(raw_article)

    assert result.article.groups_mentioned == ["i-dle"]
    assert [group.name for group in result.new_groups] == ["i-dle"]


@pytest.mark.asyncio
async def test_article_extraction_uses_cache(monkeypatch):
    fake_extractor = FakeArticleExtractor()
    raw_article = RawArticle(
        title="NMIXX announces comeback",
        text="NMIXX will release a new single next month.",
        url="https://example.com/nmixx-comeback",
        raw_source=RawSource(title="Kpop Herald"),
    )

    monkeypatch.setenv("NLP_ARTICLE_MAX_CHARS", "1500")
    monkeypatch.setattr(NLPModule, "_article_extractor", fake_extractor)

    first_article = await NLPModule.create_article(raw_article)
    second_article = await NLPModule.create_article(raw_article)

    assert fake_extractor.calls == 1
    assert first_article.summary == second_article.summary


@pytest.mark.asyncio
async def test_neutral_sentiment_is_adjusted_for_negative_article(monkeypatch):
    fake_extractor = FakeArticleExtractor(sentiment=0.5)
    raw_article = RawArticle(
        title="NMIXX member reveals health condition after tears on stage",
        text="Fans expressed concern after back pain and tears during the concert.",
        url="https://example.com/nmixx-health",
        raw_source=RawSource(title="Kpop Herald"),
    )
    monkeypatch.setattr(NLPModule, "_article_extractor", fake_extractor)

    article = await NLPModule.create_article(raw_article)

    assert article.sentiment == 0.35


@pytest.mark.asyncio
async def test_article_extraction_falls_back_when_llm_fails(monkeypatch):
    raw_article = RawArticle(
        title="Concert calendar",
        text="K-pop concerts are scheduled this month. NMIXX is expected to perform.",
        url="https://example.com/concert-calendar",
        raw_source=RawSource(title="Example News", country_code="usa"),
    )

    monkeypatch.setenv("NLP_ALLOW_RULE_FALLBACK", "true")
    monkeypatch.setattr(NLPModule, "_article_extractor", FailingArticleExtractor())

    article = await NLPModule.create_article(raw_article)

    assert article.summary.startswith("K-pop concerts are scheduled")
    assert article.sentiment == 0.5
    assert article.tags == ["concert", "k-pop"]
    assert article.countries == ["usa"]


@pytest.mark.asyncio
async def test_article_extraction_raises_by_default_when_llm_fails(monkeypatch):
    raw_article = RawArticle(
        title="Concert calendar",
        text="K-pop concerts are scheduled this month. NMIXX is expected to perform.",
        url="https://example.com/concert-calendar",
        raw_source=RawSource(title="Example News", country_code="usa"),
    )

    monkeypatch.delenv("NLP_ALLOW_RULE_FALLBACK", raising=False)
    monkeypatch.setattr(NLPModule, "_article_extractor", FailingArticleExtractor())

    with pytest.raises(Exception, match="LLM unavailable"):
        await NLPModule.create_article(raw_article)
