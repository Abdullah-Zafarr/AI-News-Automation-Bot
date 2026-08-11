from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.news_bot.pipeline import run_news_pipeline

load_dotenv()
app = FastAPI(title="AI News Automation Bot")
_DASHBOARD_HTML = Path(__file__).with_name("dashboard.html")


class DashboardRunRequest(BaseModel):
    """Safe, user-configurable options exposed by the dashboard."""

    topics: str | None = Field(default=None, max_length=200)
    limit_per_topic: int | None = Field(default=None, ge=1, le=3)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return _DASHBOARD_HTML.read_text(encoding="utf-8")


@app.post("/api/run")
def run_from_dashboard(payload: DashboardRunRequest):
    """Run user-selected topics while credentials remain server-side."""
    topics = payload.topics.strip() if payload.topics else None
    if payload.topics is not None and not topics:
        raise HTTPException(status_code=422, detail="Enter at least one topic")
    if topics and len([topic for topic in topics.split(",") if topic.strip()]) > 4:
        raise HTTPException(status_code=422, detail="Choose at most four topics")
    try:
        result = run_news_pipeline(topics=topics, limit_per_topic=payload.limit_per_topic)
        return {"success": True, "result": result.raw}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cron")
def cron(request: Request):
    secret = os.getenv("CRON_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET is not configured")
    if request.headers.get("authorization") != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        result = run_news_pipeline()
        return {"success": True, "result": result.raw}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc
