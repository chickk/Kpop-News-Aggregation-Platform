from typing import List, Optional

from app.models.articles import Article, ArticleExtract
from app.models.artists import ArtistGenerated
from app.models.events import Event
from app.models.groups import GroupGenerated
from app.models.sources import Source, SourceInput
from app.pipeline.llm_modules.modules import (
    ArticleExtractor,
    ArtistExtractor,
    EventExtractor,
    GroupExtractor,
    SourceExtractor,
)
from app.pipeline.llm_modules.signatures import ArticleInput, ArtistInput, GroupInput

_artist_extractor = None
_article_extractor = None
_group_extractor = None
_source_extractor = None
_event_extractor = None


def get_artist_extractor() -> ArtistExtractor:
    global _artist_extractor
    if _artist_extractor is None:
        _artist_extractor = ArtistExtractor()
    return _artist_extractor


def get_article_extractor() -> ArticleExtractor:
    global _article_extractor
    if _article_extractor is None:
        _article_extractor = ArticleExtractor()
    return _article_extractor


def get_group_extractor() -> GroupExtractor:
    global _group_extractor
    if _group_extractor is None:
        _group_extractor = GroupExtractor()
    return _group_extractor


def get_source_extractor() -> SourceExtractor:
    global _source_extractor
    if _source_extractor is None:
        _source_extractor = SourceExtractor()
    return _source_extractor


def get_event_extractor() -> EventExtractor:
    global _event_extractor
    if _event_extractor is None:
        _event_extractor = EventExtractor()
    return _event_extractor


async def generate_artist(
    artist_name: str, artist_groups: List[str]
) -> ArtistGenerated:
    artist_input = ArtistInput(artist_name=artist_name, artist_groups=artist_groups)
    extractor = get_artist_extractor()
    results = await extractor.acall(artist_input=artist_input)

    return results.artist_output


async def generate_article(article_title: str, article_text: str) -> ArticleExtract:
    article_input = ArticleInput(article_title=article_title, article_text=article_text)
    extractor = get_article_extractor()
    results = await extractor.acall(article_input=article_input)

    return results.article_output


async def generate_group(
    group_name: str, artists_in_group: List[str]
) -> GroupGenerated:
    group_input = GroupInput(group_name=group_name, artists_in_group=artists_in_group)
    extractor = get_group_extractor()
    results = await extractor.acall(group_input=group_input)

    return results.group_output


async def generate_source(
    title: str,
    description: Optional[str] = None,
    language: Optional[str] = None,
    country_code: Optional[str] = None,
) -> Source:
    source_input = SourceInput(
        title=title,
        description=description,
        language=language,
        country_code=country_code,
    )
    extractor = get_source_extractor()
    results = await extractor.acall(source_input=source_input)

    return results.source_output


async def create_event(articles: List[Article], events: List[Event]):
    extractor = get_event_extractor()
    results = await extractor.acall(articles=articles, events=events)

    return results.source_output
