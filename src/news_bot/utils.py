from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def canonical_url(url: str) -> str:
    """Remove common tracking query parameters before comparing URLs."""
    parts = urlsplit(str(url).strip())
    query = urlencode(
        [(key, value) for key, value in parse_qsl(parts.query) if key not in TRACKING_PARAMETERS]
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def news_id(url: str) -> str:
    return sha256(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def relative_published_time(value: str | None, *, now: datetime | None = None) -> str:
    """Render Serper publication dates consistently for Slack and the archive."""
    if not value or not value.strip():
        return "Recently"

    raw = value.strip()
    lowered = raw.lower()
    if "ago" in lowered or lowered in {"just now", "today", "yesterday", "recently"}:
        return raw

    current = now or datetime.now(timezone.utc)
    try:
        if "t" in raw.lower() or " " in raw:
            published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            seconds = max(0, int((current - published.astimezone(timezone.utc)).total_seconds()))
            if seconds < 60:
                return "just now"
            if seconds < 3600:
                minutes = seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            if seconds < 86400:
                hours = seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            days = seconds // 86400
        else:
            published_date = date.fromisoformat(raw)
            days = max(0, (current.date() - published_date).days)
    except ValueError:
        # Preserve an unfamiliar but still useful publisher-provided string.
        return raw

    if days == 0:
        return "today"
    return f"{days} day{'s' if days != 1 else ''} ago"


def parse_json_payload(value: str | list[Any] | dict[str, Any]) -> Any:
    """Parse JSON returned by a preceding pipeline tool."""
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Some LLMs add explanatory text. Extract the outermost JSON object/array.
        starts = [index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0]
        if not starts:
            raise
        start = min(starts)
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        return json.loads(cleaned[start : end + 1])
