from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Type

from crewai.tools import BaseTool
from groq import Groq
from pydantic import BaseModel, Field

from ..models import Article, NewsSummary, SummaryEnvelope
from ..utils import parse_json_payload


class SummarizerInput(BaseModel):
    articles_json: str | list[Any] | dict[str, Any] = Field(
        description="JSON array returned by NewsFetcherTool, as a JSON string or native JSON value"
    )


class SummarizerTool(BaseTool):
    """Use Groq directly for structured summaries and local deduplication."""

    name: str = "Intelligent News Summarizer"
    description: str = (
        "Deduplicates article JSON and creates concise factual summaries using Groq. "
        "Returns a JSON object with a summaries array."
    )
    args_schema: Type[BaseModel] = SummarizerInput

    def _run(self, articles_json: str | list[Any] | dict[str, Any]) -> str:
        articles_payload = parse_json_payload(articles_json)
        if isinstance(articles_payload, dict):
            articles_payload = articles_payload.get("articles", [])
        articles = [Article.model_validate(article) for article in articles_payload]
        if not articles:
            return json.dumps({"summaries": []})

        # Remove exact duplicate URLs before spending tokens.
        unique_articles: list[Article] = []
        seen_urls: set[str] = set()
        for article in articles:
            url = str(article.url)
            if url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        prompt = {
            "instructions": [
                "You are a factual news editor.",
                "Summarize only the supplied headline and snippet; do not invent facts.",
                "Write two concise sentences per article.",
                "Remove duplicate or substantially identical stories.",
                "Return only valid JSON with a top-level 'summaries' array.",
                "Each summary must contain date, headline, summary, source_url, source, and topic.",
            ],
            "articles": [article.model_dump(mode="json") for article in unique_articles],
        }
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {
                    "role": "system",
                    "content": "You return strict JSON and never include markdown fences.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{\"summaries\": []}"
        envelope = SummaryEnvelope.model_validate(parse_json_payload(raw))
        today = datetime.now(timezone.utc).date().isoformat()
        normalized: list[NewsSummary] = []
        for summary in envelope.summaries:
            if not summary.date:
                summary.date = today
            normalized.append(summary)

        return json.dumps({"summaries": [item.model_dump(mode="json") for item in normalized]})
