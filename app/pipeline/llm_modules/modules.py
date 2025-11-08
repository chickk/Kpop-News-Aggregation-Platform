from typing import List
from dspy import Module, ChainOfThought
from app.models.sources import SourceInput
from app.pipeline.llm_modules.signatures import (
    ArticleExtractSignature,
    ArticleInput,
    ArtistInput,
    ArtistPageExtractSignature,
    SourceExtractSignature,
)


class ArtistExtractor(Module):
    """Async DSPy module for extracting artist information using and LLM extraction."""

    def __init__(self):
        self.artist_extractor = ChainOfThought(ArtistPageExtractSignature)

    async def aforward(self, artist_name: str, artist_groups: List[str], k: int = 5):
        try:
            # We should add a tool that grabs wikipedia articles or a rag or tsomething to add context for bios
            artist_input = ArtistInput(
                artist_name=artist_name, artist_groups=artist_groups
            )
            return await self.artist_extractor.acall(artist_input=artist_input)

        except Exception as e:
            raise Exception(f"Error during artist extraction: {str(e)}")


class ArticleExtractor(Module):
    """Async DSPy module for extracting artist information using biography search and LLM extraction."""

    def __init__(self):
        self.extractor = ChainOfThought(ArticleExtractSignature)

    async def aforward(self, article: ArticleInput):
        try:
            return await self.extractor.acall(extraction_input=article)

        except Exception as e:
            raise Exception(f"Error during article extraction: {str(e)}")


class SourceExtractor(Module):
    """Async DSPy module for generating Source information using LLMs."""

    def __init__(self):
        self.extractor = ChainOfThought(SourceExtractSignature)

    async def aforward(self, source_input: SourceInput):
        try:
            return await self.extractor.acall(source=source_input)

        except Exception as e:
            raise Exception(f"Error during source generation: {str(e)}")
