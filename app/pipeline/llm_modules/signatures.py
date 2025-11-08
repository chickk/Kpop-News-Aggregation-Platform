from typing import List
from dspy import Signature, InputField, OutputField
from pydantic import BaseModel, Field

from app.models.articles import ArticleExtract
from app.models.artists import Artist, ArtistGenerated
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
    extraction_input: ArticleInput = InputField()
    extracted_information: ArticleExtract = OutputField()


class ArtistPageExtractSignature(Signature):
    artist_input: ArtistInput = InputField()
    artist_output: ArtistGenerated = OutputField()


class GroupExtractSignature(Signature):
    group_input: GroupInput = InputField()
    group_output: GroupGenerated = OutputField()


class SourceExtractSignature(Signature):
    source: SourceInput = InputField()
    source_output: Source = OutputField()
