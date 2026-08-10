from src.news_bot.utils import canonical_url, news_id, parse_json_payload


def test_canonical_url_removes_tracking_parameters():
    assert canonical_url("HTTPS://Example.com/story/?utm_source=x&id=4") == "https://example.com/story?id=4"


def test_news_id_is_stable():
    assert news_id("https://example.com/story?utm_source=x") == news_id("https://example.com/story")


def test_parse_json_payload_handles_markdown_fences():
    assert parse_json_payload("```json\n{\"items\": [1]}\n```") == {"items": [1]}

