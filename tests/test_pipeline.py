from src.news_bot.pipeline import run_news_pipeline


class FakeCrew:
    def kickoff(self, *, inputs):
        assert inputs == {"topics": "AI", "limit_per_topic": 2}
        return "crew result"


def test_pipeline_kicks_off_the_crewai_workflow(monkeypatch):
    monkeypatch.setattr("src.news_bot.pipeline.build_crew", lambda: FakeCrew())

    result = run_news_pipeline(topics="AI", limit_per_topic=2)

    assert result == "crew result"


def test_pipeline_retries_with_groq_when_gemini_crew_fails(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("CREWAI_MODEL", "gemini/gemini-3-flash-preview")
    providers = []

    class PrimaryCrew:
        def kickoff(self, *, inputs):
            raise RuntimeError("Gemini rate limited")

    class FallbackCrew:
        def kickoff(self, *, inputs):
            return "groq result"

    def fake_build_crew(provider=None):
        providers.append(provider)
        return FallbackCrew() if provider == "groq" else PrimaryCrew()

    monkeypatch.setattr("src.news_bot.pipeline.build_crew", fake_build_crew)

    assert run_news_pipeline(topics="AI", limit_per_topic=1) == "groq result"
    assert providers == [None, "groq"]
