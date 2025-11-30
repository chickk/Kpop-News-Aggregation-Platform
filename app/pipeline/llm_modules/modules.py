from typing import List
from dspy import Module, ChainOfThought
from app.models.articles import Article
from app.models.events import Event
from app.models.sources import SourceInput
from app.pipeline.llm_modules.signatures import (
    AdditionalEventExtractSignature,
    ArticleExtractSignature,
    ArticleInput,
    ArtistInput,
    ArtistPageExtractSignature,
    GroupExtractSignature,
    GroupInput,
    InitialEventExtractSignature,
    SourceExtractSignature,
)


class ArtistExtractor(Module):
    """
    Async DSPy module for extracting artist information using and LLM extraction.
    returns:
        Prediction object with artist_output
    """

    def __init__(self):
        self.artist_extractor = ChainOfThought(ArtistPageExtractSignature)

    async def aforward(self, artist: ArtistInput):
        try:
            # We should add a tool that grabs wikipedia articles or a rag or something to add context for bios
            return await self.artist_extractor.acall(artist=artist)

        except Exception as e:
            raise Exception(f"Error during artist extraction: {str(e)}")


class ArticleExtractor(Module):
    """
    Async DSPy module for extracting artist information using biography search and LLM extraction.
    Returns:
        prediction object with article_output
    """

    def __init__(self):
        self.extractor = ChainOfThought(ArticleExtractSignature)

    async def aforward(self, article: ArticleInput):
        try:
            return await self.extractor.acall(article=article)

        except Exception as e:
            raise Exception(f"Error during article extraction: {str(e)}")


class GroupExtractor(Module):
    """
    Returns:
        prediction object with group_output
    """

    def __init__(self):
        self.extractor = ChainOfThought(GroupExtractSignature)

    async def aforward(self, group: GroupInput):
        try:
            return await self.extractor.acall(group=group)

        except Exception as e:
            raise Exception(f"Error during group extraction: {str(e)}")


class SourceExtractor(Module):
    """Async DSPy module for generating Source information using LLMs.
    Returns:
        prediction object with source_output
    """

    def __init__(self):
        self.extractor = ChainOfThought(SourceExtractSignature)

    async def aforward(self, source: SourceInput):
        try:
            return await self.extractor.acall(source=source)

        except Exception as e:
            raise Exception(f"Error during source generation: {str(e)}")


class EventExtractor(Module):
    """Async DSPy module for generating Source information using LLMs.
    Returns:
        prediction object with source_output
    """

    def __init__(self):
        self.eventInit = ChainOfThought(InitialEventExtractSignature)
        self.eventAddition = ChainOfThought(AdditionalEventExtractSignature)

    async def aforward(self, articles: List[Article], events: List[Event]):
        try:
            if events.length != 0:
                return await self.eventAddition.acall(
                    articles=articles, existing_events=events
                )
            else:
                return await self.eventInit.acall(articles=articles)

        except Exception as e:
            raise Exception(f"Error during source generation: {str(e)}")
