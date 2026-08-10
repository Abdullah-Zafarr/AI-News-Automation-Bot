from __future__ import annotations

import json
import os
from typing import Any, ClassVar, Type

from crewai.tools import BaseTool
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from ..models import NewsSummary
from ..utils import news_id, parse_json_payload


class SheetsLoggerInput(BaseModel):
    published_json: str | list[Any] | dict[str, Any] = Field(
        description="Publisher result, as a JSON string or native JSON value"
    )


class SheetsLoggerTool(BaseTool):
    """Append successfully published news to Google Sheets using the REST client."""

    name: str = "Google Sheets News Logger"
    description: str = "Logs posted news with date, headline, summary, URL, source, topic, and ID."
    args_schema: Type[BaseModel] = SheetsLoggerInput

    HEADERS: ClassVar[list[str]] = [
        "Date",
        "Headline",
        "Summary",
        "Source URL",
        "Source",
        "Topic",
        "News ID",
        "Delivery Status",
    ]

    def _service(self):
        credential_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if credential_file:
            credentials = service_account.Credentials.from_service_account_file(
                credential_file,
                scopes=scopes,
            )
            return build("sheets", "v4", credentials=credentials, cache_discovery=False)

        raw_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not raw_credentials:
            raise RuntimeError(
                "Configure GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON"
            )
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(raw_credentials),
            scopes=scopes,
        )
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def _run(self, published_json: str | list[Any] | dict[str, Any]) -> str:
        spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not spreadsheet_id:
            raise RuntimeError("GOOGLE_SHEET_ID is not configured")

        payload = parse_json_payload(published_json)
        published = [NewsSummary.model_validate(item) for item in payload.get("posted", [])]
        if not published:
            return json.dumps({"logged": [], "skipped": 0})

        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "News")
        service = self._service()
        existing = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:H")
            .execute()
            .get("values", [])
        )

        if not existing:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1:H1",
                valueInputOption="RAW",
                body={"values": [self.HEADERS]},
            ).execute()
            existing = [self.HEADERS]

        existing_ids = set()
        for row in existing[1:]:
            if len(row) >= 7 and row[6]:
                existing_ids.add(str(row[6]))
            elif len(row) >= 4 and row[3]:
                existing_ids.add(news_id(row[3]))

        new_rows: list[list[str]] = []
        logged: list[dict] = []
        skipped = 0
        for summary in published:
            identifier = news_id(str(summary.source_url))
            if identifier in existing_ids:
                skipped += 1
                continue
            new_rows.append(
                [
                    summary.date,
                    summary.headline,
                    summary.summary,
                    str(summary.source_url),
                    summary.source,
                    summary.topic,
                    identifier,
                    "posted",
                ]
            )
            logged.append(summary.model_dump(mode="json"))
            existing_ids.add(identifier)

        if new_rows:
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:H",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": new_rows},
            ).execute()

        return json.dumps({"logged": logged, "skipped": skipped})
