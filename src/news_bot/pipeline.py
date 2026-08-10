from __future__ import annotations

import os

from dotenv import load_dotenv

from .crew import build_crew

load_dotenv()


def run_news_pipeline(
    topics: str | None = None,
    limit_per_topic: int | None = None,
):
    """Run the full crew. Secrets are read from environment variables only."""
    configured_topics = topics or os.getenv(
        "NEWS_TOPICS", "artificial intelligence,technology,finance,crypto"
    )
    configured_limit = limit_per_topic or int(os.getenv("NEWS_LIMIT_PER_TOPIC", "5"))
    return build_crew().kickoff(
        inputs={
            "topics": configured_topics,
            "limit_per_topic": configured_limit,
        }
    )

