from __future__ import annotations

import os
from types import SimpleNamespace

from dotenv import load_dotenv

from .tools import DiscordBotTool, NewsFetcherTool, SheetsLoggerTool, SlackBotTool, SummarizerTool

load_dotenv()


def run_news_pipeline(
    topics: str | None = None,
    limit_per_topic: int | None = None,
    max_articles: int | None = None,
):
    """Run the news workflow directly, without LLM-controlled tool selection.

    The LLM is used only where it adds value: producing article summaries.
    Fetching, publishing, and archiving are deterministic API operations, so
    routing them directly prevents an empty agent response from failing a run.
    """
    configured_topics = topics or os.getenv(
        "NEWS_TOPICS", "artificial intelligence,technology,finance,crypto"
    )
    configured_limit = limit_per_topic or int(os.getenv("NEWS_LIMIT_PER_TOPIC", "2"))
    configured_max_articles = max_articles or int(os.getenv("GROQ_MAX_ARTICLES", "2"))

    articles = NewsFetcherTool().run(
        topics=configured_topics,
        limit_per_topic=configured_limit,
    )
    summaries = SummarizerTool(max_articles=configured_max_articles).run(
        articles_json=articles
    )
    notification_provider = os.getenv("NOTIFICATION_PROVIDER", "slack").lower()
    publisher = DiscordBotTool() if notification_provider == "discord" else SlackBotTool()
    published = publisher.run(summaries_json=summaries)
    archived = SheetsLoggerTool().run(published_json=published)

    result = SimpleNamespace(raw=archived)
    print(f"[PIPELINE_COMPLETE] {result.raw}")
    return result
