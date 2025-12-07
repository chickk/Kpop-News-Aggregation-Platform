from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FetchArticlesRequest(BaseModel):
    """Request model for fetching and storing articles (Stage 1)"""

    query_terms: List[str] = Field(
        ...,
        description="Search terms for fetching articles (e.g., ['K-Pop', 'NewJeans'])",
        min_length=1,
    )
    concepts: bool = Field(
        default=True, description="Whether to use concept-based search"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start date for article search (defaults to 7 days ago)",
    )
    end_date: Optional[datetime] = Field(
        default=None, description="End date for article search (defaults to now)"
    )
    language: Optional[str] = Field(
        default=None, description="Language code for articles (e.g., 'en', 'ko')"
    )
    max_results: int = Field(
        default=100, description="Maximum number of articles to fetch", ge=1, le=500
    )


class ProcessArticlesRequest(BaseModel):
    """Request model for processing stored articles (Stage 2)"""

    batch_size: int = Field(
        default=5,
        description="Number of articles to process concurrently",
        ge=1,
        le=10,
    )
    limit: int = Field(
        default=100, description="Maximum number of articles to process", ge=1, le=1000
    )


class RunFullPipelineRequest(BaseModel):
    """Request model for running both stages of the pipeline"""

    query_terms: List[str] = Field(
        ..., description="Search terms for fetching articles", min_length=1
    )
    concepts: bool = Field(default=True)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    language: Optional[str] = Field(default=None)
    max_results: int = Field(default=100, ge=1, le=500)
    batch_size: int = Field(default=5, ge=1, le=15)
    process_limit: Optional[int] = Field(
        default=None,
        description="Max articles to process (defaults to all fetched)",
        ge=1,
        le=1000,
    )


class FetchArticlesResponse(BaseModel):
    """Response model for fetch articles endpoint"""

    success: bool
    message: str
    fetched: int = Field(description="Number of articles fetched from news source")
    stored: int = Field(description="Number of new articles stored in database")
    duplicates: int = Field(description="Number of duplicate articles skipped")


class ProcessArticlesResponse(BaseModel):
    """Response model for process articles endpoint"""

    success: bool
    message: str
    processed: int = Field(description="Number of articles successfully processed")
    failed: int = Field(description="Number of articles that failed processing")
    failed_articles: List[Dict[str, str]] = Field(
        default_factory=list, description="List of failed articles with error messages"
    )


class FullPipelineResponse(BaseModel):
    """Response model for full pipeline endpoint"""

    success: bool
    message: str
    fetch_stats: Dict[str, int] = Field(
        description="Statistics from fetch stage (fetched, stored, duplicates)"
    )
    process_stats: Dict[str, Any] = Field(
        description="Statistics from processing stage (processed, failed, failed_articles)"
    )
