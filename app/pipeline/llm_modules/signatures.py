from typing import List
from dspy import Signature, InputField, OutputField
from pydantic import BaseModel, Field

from app.models.articles import ArticleExtract, Article
from app.models.artists import Artist, ArtistGenerated
from app.models.events import Event, EventExtraction
from app.models.groups import Group, GroupGenerated
from app.models.sources import Source, SourceInput


# Input  Definitions
class ArticleInput(BaseModel):
    article_title: str
    article_text: str


class ArtistInput(BaseModel):
    artist_name: str
    artist_groups: List[Group]
    # Maybe we can add a rag to pull k relevant documents to feed the llm for more up to date summaries??


class GroupInput(BaseModel):
    group_name: str
    artists_in_group: List[Artist]
    # Maybe we can add a rag to pull k relevant documents to feed the llm for more up to date summaries?


# Signatures
class ArticleExtractSignature(Signature):
    """
    Params:
        article_input

        article_output
    """

    article_input: ArticleInput = InputField()
    article_output: ArticleExtract = OutputField()


class ArtistPageExtractSignature(Signature):
    """
    Params:
        artist_input

        artist_output
    """

    artist_input: ArtistInput = InputField()
    artist_output: ArtistGenerated = OutputField()


class GroupExtractSignature(Signature):
    """
    Params:
        group_input

        group_output
    """

    group_input: GroupInput = InputField()
    group_output: GroupGenerated = OutputField()


class SourceExtractSignature(Signature):
    """
    Params:
        source_input

        source_output
    """

    source_input: SourceInput = InputField()
    source_output: Source = OutputField()


class InitialEventExtractSignature(Signature):
    articles: List[Article] = InputField()
    initial_event_output: EventExtraction = OutputField()


class AdditionalEventExtractSignature(Signature):
    articles: List[Article] = InputField()
    existing_events: List[Event] = InputField()
    initial_event_output: EventExtraction = OutputField()
