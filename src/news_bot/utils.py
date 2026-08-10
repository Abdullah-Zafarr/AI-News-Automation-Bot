from __future__ import annotations

import json
import re
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


def parse_json_payload(value: str | list[Any] | dict[str, Any]) -> Any:
    """Parse JSON returned by a preceding CrewAI task or tool."""
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

