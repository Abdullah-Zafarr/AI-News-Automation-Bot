# AI News Automation Bot

This project is a code-first CrewAI application that finds recent news, summarizes it with Groq, publishes it to Slack, and archives it in Google Sheets. It uses four custom tools and does not use CrewAI's built-in Serper, Slack, or Sheets tools.

## Dashboard

![AI News Automation Bot dashboard](src/screenshot%20ui/ui.PNG)

## What is implemented

- `NewsFetcherTool`: calls Serper's news endpoint directly with `requests`.
- `SummarizerTool`: calls Groq directly and validates structured JSON with Pydantic.
- `SlackBotTool`: posts messages through a Slack incoming webhook.
- `SheetsLoggerTool`: uses the Google Sheets REST API to append successfully published stories and prevents duplicate rows by URL-derived ID.
- Four specialized agents running in a sequential CrewAI crew.
- FastAPI routes at `/api/health` and `/api/cron`.
- Vercel cron schedule configured for every six hours.

## Local setup

1. Install Python 3.13 and `uv`.
2. Create and activate a virtual environment:

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.runtime.txt
   ```

4. Copy `.env.example` to `.env` and fill in the API credentials.
5. Run tests:

   ```powershell
   pytest
   ```

6. Run the pipeline manually:

   ```powershell
   python -m src.news_bot.main
   ```

7. Run the API locally:

   ```powershell
   uvicorn api.index:app --reload
   ```

Then open `http://127.0.0.1:8000/api/health`. The cron endpoint requires `Authorization: Bearer <CRON_SECRET>`.

## External configuration

### Serper

Create a Serper API key and put it in `SERPER_API_KEY`. The tool calls `https://google.serper.dev/news` directly.

### Groq

Create a Groq API key and set `GROQ_API_KEY`. `GROQ_MODEL` controls the direct `SummarizerTool` call; `CREWAI_MODEL` controls the CrewAI agents. The defaults use `llama-3.1-8b-instant`, fetch two stories per topic, summarize at most four unique stories total, cap output at 700 tokens, and retry a rate-limited request twice with exponential backoff. Agents are limited to three iterations so they can select a tool, receive its result, and complete their response without wasting calls. Adjust `GROQ_MAX_ARTICLES`, `GROQ_MAX_COMPLETION_TOKENS`, and `GROQ_RATE_LIMIT_RETRIES` if needed.

### Slack

Create a Slack app, enable Incoming Webhooks, add a webhook to a test channel, and set `SLACK_WEBHOOK_URL`. Never commit the webhook URL.

If the workspace has reached its app-installation limit, set `SLACK_DRY_RUN=true`. The Slack tool will print the exact messages it would send and the rest of the pipeline can be tested without a webhook. Set it back to `false` once a real webhook is available.

### Discord alternative

If Slack cannot be installed in your internship workspace, create an incoming webhook in a Discord channel you control, set `NOTIFICATION_PROVIDER=discord`, and set `DISCORD_WEBHOOK_URL`. Discord incoming webhooks are one-way HTTP endpoints tied to a channel and do not require a persistent bot connection. This completes the notification part of the pipeline, but confirm with your supervisor because it demonstrates Discord rather than Slack. See Discord's [Execute Webhook documentation](https://docs.discord.com/developers/resources/webhook).

### Google Sheets

Enable Google Sheets API, create a service account, download its key as `service-account.json` in the project root, and share the target spreadsheet with the service-account email as Editor. The file is gitignored and the tool loads it through `GOOGLE_SERVICE_ACCOUNT_FILE`. Alternatively, you may put the JSON object into `GOOGLE_SERVICE_ACCOUNT_JSON` as a single-line environment value. Set `GOOGLE_SHEET_ID` to the ID from the spreadsheet URL. The logger creates headers automatically:

```text
Date | Headline | Summary | Source URL | Source | Topic | News ID | Delivery Status
```

## Vercel deployment

Push this repository to GitHub and import it into Vercel. Add every variable from `.env` to Vercel Project Settings, then deploy. The Vercel build installs the CrewAI dependency set into the function bundle so it does not consume temporary runtime disk space during a request. Vercel invokes `/api/cron` with `GET` and sends `CRON_SECRET` as an Authorization bearer token.

The schedule is `0 9 * * *` and uses UTC, which runs once daily at 9:00 UTC and works on Vercel Hobby. The dashboard's manual run button remains available for on-demand briefs. A six-hour schedule requires a Vercel plan that supports more frequent cron invocations or an external scheduler that calls the protected endpoint.

## Security and reliability notes

- Do not commit `.env`, service-account JSON, or Slack webhook URLs.
- Keep `NEWS_LIMIT_PER_TOPIC` and `GROQ_MAX_ARTICLES` small to control Groq token use and function duration.
- The logger derives a stable news ID from the canonical source URL and skips existing IDs.
- Vercel does not automatically retry failed cron invocations; inspect Vercel function logs and retry failed runs after fixing the cause.
- The first version summarizes the supplied search headline and snippet. Add a separate article-content extractor only after the basic pipeline is working.
