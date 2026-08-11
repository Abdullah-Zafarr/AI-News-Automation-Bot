from src.news_bot.pipeline import run_news_pipeline


class FakeCrew:
    def kickoff(self, *, inputs):
        assert inputs == {"topics": "AI", "limit_per_topic": 2}
        return "crew result"


def test_pipeline_kicks_off_the_crewai_workflow(monkeypatch):
    monkeypatch.setattr("src.news_bot.pipeline.build_crew", lambda: FakeCrew())

    result = run_news_pipeline(topics="AI", limit_per_topic=2)

    assert result == "crew result"
