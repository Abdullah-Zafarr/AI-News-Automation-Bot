# AI News Automation Bot

This project is a code-first CrewAI application that finds recent news, summarizes it with Groq, publishes it to Slack, and archives it in Google Sheets. It uses four custom tools and does not use CrewAI's built-in Serper, Slack, or Sheets tools.

## What is implemented

- `NewsFetcherTool`: calls Serper's news endpoint directly with `requests`.
- `SummarizerTool`: calls Groq directly and validates structured JSON with Pydantic.
- `SlackBotTool`: posts messages through a Slack incoming webhook.
- `SheetsLoggerTool`: appends successfully published stories using the Google Sheets API and prevents duplicate rows by URL-derived ID.
- Four specialized agents running in a sequential CrewAI crew.
- FastAPI routes at `/api/health` and `/api/cron`.
- Vercel cron schedule configured for every six hours.

## Important runtime requirement

CrewAI currently requires Python 3.10 through 3.13. The repository includes `.python-version` set to `3.13`. Python 3.14 is not supported by the current CrewAI requirement.

## Local setup

1. Install Python 3.13 and `uv`.
2. Create and activate a virtual environment:

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in the API credentials.
5. Run tests:

   ```powershell
   pytest
   ```

6. Run the crew manually:

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

Create a Groq API key and set `GROQ_API_KEY`. `GROQ_MODEL` controls the model used by `SummarizerTool`; `CREWAI_MODEL` controls the model used by CrewAI agents.

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

Push this repository to GitHub and import it into Vercel. Add every variable from `.env` to Vercel Project Settings, then deploy. Vercel invokes `/api/cron` with `GET` and sends `CRON_SECRET` as an Authorization bearer token.

The schedule is `0 */6 * * *` and uses UTC. Vercel Hobby accounts restrict cron jobs to once per day; a six-hour schedule therefore requires a plan that supports more frequent cron invocations or an external scheduler that calls the protected endpoint.

## Security and reliability notes

- Do not commit `.env`, service-account JSON, or Slack webhook URLs.
- Keep the Serper result count small to control LLM cost and function duration.
- The logger derives a stable news ID from the canonical source URL and skips existing IDs.
- Vercel does not automatically retry failed cron invocations; inspect Vercel function logs and retry failed runs after fixing the cause.
- The first version summarizes the supplied search headline and snippet. Add a separate article-content extractor only after the basic pipeline is working.
