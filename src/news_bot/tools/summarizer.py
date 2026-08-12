from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Type

from crewai.tools import BaseTool
from groq import Groq, RateLimitError
from pydantic import BaseModel, Field
import requests

from ..models import Article, NewsSummary, SummaryEnvelope
from ..utils import canonical_url, parse_json_payload, relative_published_time


class SummarizerInput(BaseModel):
    articles_json: str = Field(
        description="JSON array returned by NewsFetcherTool."
    )


class SummarizerTool(BaseTool):
    """Use Gemini for structured summaries, with Groq as the fallback."""

    name: str = "Intelligent News Summarizer"
    description: str = (
        "Deduplicates article JSON and creates concise factual summaries using Gemini. "
        "Returns a JSON object with a summaries array."
    )
    args_schema: Type[BaseModel] = SummarizerInput
    max_articles: int = 2

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

        # Keep a single prompt comfortably below provider token limits.
        unique_articles = unique_articles[: self.max_articles]

        prompt = {
            "instructions": [
                "You are a factual news editor.",
                "Summarize only the supplied headline and snippet; do not invent facts.",
                "Write one concise sentence per article.",
                "Remove duplicate or substantially identical stories.",
                "Return only valid JSON with a top-level 'summaries' array.",
                "Each summary must contain date, headline, summary, source_url, source, and topic.",
            ],
            "articles": [article.model_dump(mode="json") for article in unique_articles],
        }
        groq_request_args = {
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "messages": [
                {
                    "role": "system",
                    "content": "You return strict JSON and never include markdown fences.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            "temperature": 0.1,
            "max_completion_tokens": int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "700")),
            "response_format": {"type": "json_object"},
        }
        raw: str | None = None
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": gemini_key},
                    json={
                        "system_instruction": {"parts": [{"text": "You return strict JSON and never include markdown fences."}]},
                        "contents": [{"role": "user", "parts": [{"text": json.dumps(prompt)}]}],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "700")),
                            "responseMimeType": "application/json",
                        },
                    },
                    timeout=45,
                )
                response.raise_for_status()
                raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                # A provider failure should not stop the brief when Groq is available.
                raw = None

        if raw is None:
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            retries = int(os.getenv("GROQ_RATE_LIMIT_RETRIES", "2"))
            for attempt in range(retries + 1):
                try:
                    response = client.chat.completions.create(**groq_request_args)
                    raw = response.choices[0].message.content
                    break
                except RateLimitError:
                    if attempt == retries:
                        raise
                    time.sleep((2**attempt) + random.uniform(0, 0.5))

        raw = raw or "{\"summaries\": []}"
        envelope = SummaryEnvelope.model_validate(parse_json_payload(raw))
        source_dates = {
            canonical_url(str(article.url)): relative_published_time(article.published_at)
            for article in unique_articles
        }
        normalized: list[NewsSummary] = []
        for summary in envelope.summaries:
            # The model writes the summary, but Serper is the source of truth
            # for publication time. This prevents mixed ISO and relative dates.
            summary.date = source_dates.get(
                canonical_url(str(summary.source_url)),
                relative_published_time(summary.date),
            )
            normalized.append(summary)

        return json.dumps({"summaries": [item.model_dump(mode="json") for item in normalized]})
