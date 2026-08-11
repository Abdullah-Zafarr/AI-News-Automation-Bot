from __future__ import annotations

import json
import os
from typing import Any, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..models import NewsSummary
from ..utils import parse_json_payload


class DiscordBotInput(BaseModel):
    summaries_json: str = Field(
        description="Summary JSON returned by the summarizer."
    )


class DiscordBotTool(BaseTool):
    """Post news through a Discord incoming webhook using plain HTTP."""

    name: str = "Discord News Publisher"
    description: str = "Posts each news summary to a configured Discord channel webhook."
    args_schema: Type[BaseModel] = DiscordBotInput

    def _run(self, summaries_json: str | list[Any] | dict[str, Any]) -> str:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        dry_run = os.getenv("SLACK_DRY_RUN", "false").lower() in {"1", "true", "yes"}
        if not webhook_url and not dry_run:
            raise RuntimeError("DISCORD_WEBHOOK_URL is not configured")

        payload = parse_json_payload(summaries_json)
        if isinstance(payload, list):
            payload = {"summaries": payload}
        summaries = [NewsSummary.model_validate(item) for item in payload.get("summaries", [])]
        posted: list[dict] = []
        failed: list[dict] = []

        for summary in summaries:
            message = (
                f"**{summary.headline}**\n"
                f"{summary.summary}\n"
                f"Topic: `{summary.topic}` | Source: {summary.source}\n"
                f"{summary.source_url}"
            )
            if dry_run:
                print(f"[DISCORD_DRY_RUN] {message}")
                posted.append(summary.model_dump(mode="json"))
                continue
            try:
                response = requests.post(
                    webhook_url,
                    params={"wait": "true"},
                    json={"content": message},
                    timeout=15,
                )
                response.raise_for_status()
                posted.append(summary.model_dump(mode="json"))
            except requests.RequestException as exc:
                failed.append(
                    {
                        "headline": summary.headline,
                        "source_url": str(summary.source_url),
                        "error": str(exc),
                    }
                )

        return json.dumps({"posted": posted, "failed": failed, "dry_run": dry_run})
