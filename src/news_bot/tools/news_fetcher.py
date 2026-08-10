from __future__ import annotations

import json
import os
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..models import Article
from ..utils import canonical_url


class NewsFetcherInput(BaseModel):
    topics: str = Field(
        description="Comma-separated topics, for example 'AI, technology, finance'."
    )
    limit_per_topic: int = Field(default=5, ge=1, le=10)


class NewsFetcherTool(BaseTool):
    """Search Serper directly instead of using CrewAI's built-in search tools."""

    name: str = "Custom News Fetcher"
    description: str = (
        "Searches Serper's news endpoint for recent stories and returns normalized JSON "
        "with headline, source, snippet, publication date, URL, and topic."
    )
    args_schema: Type[BaseModel] = NewsFetcherInput

    def _run(self, topics: str, limit_per_topic: int = 5) -> str:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise RuntimeError("SERPER_API_KEY is not configured")

        normalized_topics = [topic.strip() for topic in topics.split(",") if topic.strip()]
        if not normalized_topics:
            raise ValueError("At least one news topic is required")

        articles: list[Article] = []
        seen_urls: set[str] = set()

        for topic in normalized_topics:
            response = requests.post(
                "https://google.serper.dev/news",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": topic, "num": limit_per_topic, "gl": "us", "hl": "en"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()

            for item in payload.get("news", []):
                url = item.get("link")
                headline = (item.get("title") or "").strip()
                if not url or not headline:
                    continue
                key = canonical_url(url)
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                articles.append(
                    Article(
                        headline=headline,
                        source=item.get("source") or "Unknown",
                        url=url,
                        snippet=(item.get("snippet") or "").strip(),
                        published_at=item.get("date"),
                        topic=topic,
                    )
                )

        return json.dumps([article.model_dump(mode="json") for article in articles])

