from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.index import DashboardRunRequest, run_from_dashboard


def test_dashboard_run_passes_user_options_to_pipeline(monkeypatch):
    captured = {}

    def fake_run_news_pipeline(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(raw="done")

    monkeypatch.setattr("api.index.run_news_pipeline", fake_run_news_pipeline)

    response = run_from_dashboard(DashboardRunRequest(topics="AI, robotics", limit_per_topic=3))

    assert captured == {"topics": "AI, robotics", "limit_per_topic": 3}
    assert response == {"success": True, "result": "done"}


def test_dashboard_run_rejects_more_than_four_topics():
    with pytest.raises(HTTPException, match="at most four topics"):
        run_from_dashboard(DashboardRunRequest(topics="a,b,c,d,e", limit_per_topic=1))
