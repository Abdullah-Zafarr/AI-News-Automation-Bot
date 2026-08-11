from datetime import datetime, timezone

from src.news_bot.utils import canonical_url, news_id, parse_json_payload, relative_published_time


def test_canonical_url_removes_tracking_parameters():
    assert canonical_url("HTTPS://Example.com/story/?utm_source=x&id=4") == "https://example.com/story?id=4"


def test_news_id_is_stable():
    assert news_id("https://example.com/story?utm_source=x") == news_id("https://example.com/story")


def test_parse_json_payload_handles_markdown_fences():
    assert parse_json_payload("```json\n{\"items\": [1]}\n```") == {"items": [1]}


def test_relative_published_time_normalizes_calendar_dates():
    now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    assert relative_published_time("2026-08-11", now=now) == "today"
    assert relative_published_time("2026-08-09", now=now) == "2 days ago"


def test_relative_published_time_uses_precise_timestamps_when_available():
    now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    assert relative_published_time("2026-08-11T11:15:00Z", now=now) == "45 minutes ago"
