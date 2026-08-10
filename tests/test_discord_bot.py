import json

from src.news_bot.tools.discord_bot import DiscordBotTool


def test_discord_dry_run(monkeypatch, capsys):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
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

    result = json.loads(DiscordBotTool().run(summaries_json=json.dumps(payload)))

    assert len(result["posted"]) == 1
    assert result["dry_run"] is True
    assert "[DISCORD_DRY_RUN]" in capsys.readouterr().out

