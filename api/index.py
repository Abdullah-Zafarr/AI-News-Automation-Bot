from __future__ import annotations

import os
import sys
from pathlib import Path

# Vercel builds runtime dependencies into this folder so CrewAI is available
# immediately instead of being installed in the function's limited /tmp disk.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VENDORED_PACKAGES = _PROJECT_ROOT / "python_packages"
if _VENDORED_PACKAGES.is_dir():
    sys.path.insert(0, str(_VENDORED_PACKAGES))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from src.news_bot.pipeline import run_news_pipeline
from src.news_bot.tools.sheets_logger import read_archive_history

load_dotenv()
app = FastAPI(title="AI News Automation Bot")
_DASHBOARD_HTML = Path(__file__).with_name("dashboard.html")
_FAVICON_SVG = Path(__file__).with_name("favicon.svg")


class DashboardRunRequest(BaseModel):
    """Safe, user-configurable options exposed by the dashboard."""

    topics: str | None = Field(default=None, max_length=200)
    limit_per_topic: int | None = Field(default=None, ge=1, le=3)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return _DASHBOARD_HTML.read_text(encoding="utf-8")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(_FAVICON_SVG, media_type="image/svg+xml")


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


@app.get("/api/history")
def history() -> dict[str, list[dict[str, str]]]:
    """Return the durable Google Sheets article archive for the History tab."""
    try:
        return {"entries": read_archive_history()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"History is unavailable: {exc}") from exc


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
