from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    """A search result normalized by NewsFetcherTool."""

    headline: str = Field(min_length=1)
    source: str = "Unknown"
    url: HttpUrl
    snippet: str = ""
    published_at: str | None = None
    topic: str


class NewsSummary(BaseModel):
    """The row shared by Slack and Google Sheets."""

    date: str
    headline: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_url: HttpUrl
    source: str = "Unknown"
    topic: str


class SummaryEnvelope(BaseModel):
    summaries: list[NewsSummary]

