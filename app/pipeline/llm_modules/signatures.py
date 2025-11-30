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
    artist_groups: List[str]  # Group names that the artist is a member of
    # Maybe we can add a rag to pull k relevant documents to feed the llm for more up to date summaries??


class GroupInput(BaseModel):
    group_name: str
    artists_in_group: List[str]  # Artist names that are members of the group
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
    Generate detailed information about a musical artist based on their name.

    For the given artist name, research and provide:
    - A unique, Wikipedia-style biography specific to THIS artist
    - Career start date (if known)
    - Active status
    - Primary language and countries they're associated with
    - Relevant tags describing their music style and career

    IMPORTANT: Each artist should have a UNIQUE biography based on their actual career.
    Do NOT use generic templates. Research the specific artist mentioned.
    """

    artist: ArtistInput = InputField(desc="Artist name and their group memberships")
    artist_output: ArtistGenerated = OutputField(desc="Generated artist information with unique biography")


class GroupExtractSignature(Signature):
    """
    Generate detailed information about a musical group/band based on their name.

    For the given group name, research and provide:
    - A unique, Wikipedia-style biography specific to THIS group
    - Formation and disbandment dates (if applicable)
    - Active status
    - Primary languages and countries they're associated with
    - Relevant tags describing their music style and career

    IMPORTANT: Each group should have a UNIQUE biography based on their actual history.
    Do NOT use generic templates. Research the specific group mentioned.
    """

    group: GroupInput = InputField(desc="Group name and member names")
    group_output: GroupGenerated = OutputField(desc="Generated group information with unique biography")


class SourceExtractSignature(Signature):
    """
    Generate detailed information about a news source/publication.

    For the given source, provide:
    - Colloquial name (e.g., "BBC", "The Korea Times")
    - A Wikipedia-style biography/description
    - Formation date (if known)
    - Primary language and countries of operation
    - Relevant tags (e.g., "news", "entertainment", "K-pop")

    IMPORTANT: Generate accurate information specific to THIS publication.
    """

    source: SourceInput = InputField(desc="Source title and metadata")
    source_output: Source = OutputField(desc="Generated source information")


class InitialEventExtractSignature(Signature):
    articles: List[Article] = InputField()
    initial_event_output: EventExtraction = OutputField()


class AdditionalEventExtractSignature(Signature):
    articles: List[Article] = InputField()
    existing_events: List[Event] = InputField()
    initial_event_output: EventExtraction = OutputField()
