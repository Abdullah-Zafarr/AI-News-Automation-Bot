import json

from src.news_bot.tools.news_fetcher import NewsFetcherTool


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "news": [
                {
                    "title": "AI launch",
                    "source": "Example",
                    "link": "https://example.com/a?utm_source=test",
                    "snippet": "A new AI launch.",
                    "date": "2 hours ago",
                },
                {
                    "title": "Duplicate AI launch",
                    "source": "Example",
                    "link": "https://example.com/a",
                    "snippet": "Duplicate.",
                },
            ]
        }


def test_fetcher_normalizes_and_deduplicates(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    monkeypatch.setattr(
        "src.news_bot.tools.news_fetcher.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    result = json.loads(NewsFetcherTool().run(topics="AI", limit_per_topic=5))

    assert len(result) == 1
    assert result[0]["headline"] == "AI launch"
    assert result[0]["topic"] == "AI"

