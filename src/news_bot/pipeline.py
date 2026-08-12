from __future__ import annotations

import os

from dotenv import load_dotenv

from .crew import build_crew

load_dotenv()


def run_news_pipeline(
    topics: str | None = None,
    limit_per_topic: int | None = None,
):
    """Run the required CrewAI workflow. Secrets are read from environment variables only."""
    configured_topics = topics or os.getenv(
        "NEWS_TOPICS", "artificial intelligence,technology,finance,crypto"
    )
    configured_limit = limit_per_topic or int(os.getenv("NEWS_LIMIT_PER_TOPIC", "2"))

    inputs = {"topics": configured_topics, "limit_per_topic": configured_limit}
    try:
        result = build_crew().kickoff(inputs=inputs)
    except Exception:
        # CrewAI calls the LLM to decide which tool to invoke. Retry the whole
        # sequential run on Groq when the Gemini primary is unavailable or
        # rate limited. Publisher and Sheets tools remain idempotent.
        model = os.getenv("CREWAI_MODEL", "gemini/gemini-3-flash-preview")
        if not (os.getenv("GEMINI_API_KEY") and os.getenv("GROQ_API_KEY") and not model.startswith("groq/")):
            raise
        print("[LLM_FALLBACK] Gemini unavailable; retrying CrewAI run with Groq")
        result = build_crew(provider="groq").kickoff(inputs=inputs)
    print(f"[PIPELINE_COMPLETE] {getattr(result, 'raw', result)}")
    return result
