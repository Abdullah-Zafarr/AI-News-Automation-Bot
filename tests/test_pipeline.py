from src.news_bot.pipeline import run_news_pipeline


def test_pipeline_runs_tools_in_order_without_agent_llm_calls(monkeypatch):
    calls = []

    class FakeFetcher:
        def run(self, **kwargs):
            calls.append(("fetch", kwargs))
            return "articles"

    class FakeSummarizer:
        def __init__(self, *, max_articles):
            self.max_articles = max_articles

        def run(self, **kwargs):
            calls.append(("summarize", self.max_articles, kwargs))
            return "summaries"

    class FakePublisher:
        def run(self, **kwargs):
            calls.append(("publish", kwargs))
            return "published"

    class FakeLogger:
        def run(self, **kwargs):
            calls.append(("archive", kwargs))
            return "archived"

    monkeypatch.setattr("src.news_bot.pipeline.NewsFetcherTool", FakeFetcher)
    monkeypatch.setattr("src.news_bot.pipeline.SummarizerTool", FakeSummarizer)
    monkeypatch.setattr("src.news_bot.pipeline.SlackBotTool", FakePublisher)
    monkeypatch.setattr("src.news_bot.pipeline.SheetsLoggerTool", FakeLogger)

    result = run_news_pipeline(topics="AI", limit_per_topic=1, max_articles=2)

    assert result.raw == "archived"
    assert calls == [
        ("fetch", {"topics": "AI", "limit_per_topic": 1}),
        ("summarize", 2, {"articles_json": "articles"}),
        ("publish", {"summaries_json": "summaries"}),
        ("archive", {"published_json": "published"}),
    ]
