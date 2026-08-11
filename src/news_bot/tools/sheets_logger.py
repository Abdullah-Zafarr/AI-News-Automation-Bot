from __future__ import annotations

import json
import os
from typing import Any, ClassVar, Type
from urllib.parse import quote

from crewai.tools import BaseTool
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from pydantic import BaseModel, Field

from ..models import NewsSummary
from ..utils import news_id, parse_json_payload


class SheetsLoggerInput(BaseModel):
    published_json: str = Field(
        description="Publisher result JSON returned by the notification tool."
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

    def _session(self) -> AuthorizedSession:
        credential_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if credential_file:
            credentials = service_account.Credentials.from_service_account_file(
                credential_file,
                scopes=scopes,
            )
            return AuthorizedSession(credentials)

        raw_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not raw_credentials:
            raise RuntimeError(
                "Configure GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON"
            )
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(raw_credentials),
            scopes=scopes,
        )
        return AuthorizedSession(credentials)

    @staticmethod
    def _values_url(spreadsheet_id: str, cell_range: str) -> str:
        encoded_range = quote(cell_range, safe="")
        return f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}"

    def _run(self, published_json: str | list[Any] | dict[str, Any]) -> str:
        spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not spreadsheet_id:
            raise RuntimeError("GOOGLE_SHEET_ID is not configured")

        payload = parse_json_payload(published_json)
        published = [NewsSummary.model_validate(item) for item in payload.get("posted", [])]
        if not published:
            return json.dumps({"logged": [], "skipped": 0})

        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "News")
        session = self._session()
        range_name = f"{sheet_name}!A:H"
        response = session.get(self._values_url(spreadsheet_id, range_name), timeout=20)
        response.raise_for_status()
        existing = response.json().get("values", [])

        if not existing:
            response = session.put(
                self._values_url(spreadsheet_id, f"{sheet_name}!A1:H1"),
                params={"valueInputOption": "RAW"},
                json={"values": [self.HEADERS]},
                timeout=20,
            )
            response.raise_for_status()
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
            response = session.post(
                f"{self._values_url(spreadsheet_id, range_name)}:append",
                params={
                    "valueInputOption": "RAW",
                    "insertDataOption": "INSERT_ROWS",
                },
                json={"values": new_rows},
                timeout=20,
            )
            response.raise_for_status()

        return json.dumps({"logged": logged, "skipped": skipped})
