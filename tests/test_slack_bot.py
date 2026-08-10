import json

from src.news_bot.tools.slack_bot import SlackBotTool


def test_slack_dry_run_does_not_require_webhook(monkeypatch, capsys):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("SLACK_DRY_RUN", "true")
    payload = {
        "summaries": [
            {
                "date": "2026-08-09",
                "headline": "AI launch",
                "summary": "A concise update.",
                "source_url": "https://example.com/news",
                "source": "Example",
                "topic": "AI",
            }
        ]
    }

    result = json.loads(SlackBotTool().run(summaries_json=json.dumps(payload)))

    assert len(result["posted"]) == 1
    assert result["dry_run"] is True
    assert "[SLACK_DRY_RUN]" in capsys.readouterr().out

