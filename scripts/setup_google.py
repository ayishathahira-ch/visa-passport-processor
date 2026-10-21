#!/usr/bin/env python3
"""One-time Google setup: authorise Gmail (read-only) + Sheets, optionally create the results sheet.

    python scripts/setup_google.py                 # just authorise (writes token.json)
    python scripts/setup_google.py --create-sheet  # authorise + create the sheet + sheet_config.json

The sheet stays PRIVATE to your Google account. It holds passport data, so never share it publicly.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.auth.transport.requests import Request  # noqa: E402
from google.oauth2.credentials import Credentials  # noqa: E402
from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

from visa_processor import config  # noqa: E402

HEADERS = [
    "Email From", "Email Subject", "Visa Type", "Full Name", "Passport Number",
    "Nationality", "Date of Birth", "Expiry Date", "Gender", "Is Valid",
    "PDF Filename", "Processed At",
]


def get_credentials() -> Credentials:
    if config.TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(config.TOKEN_FILE), config.SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            config.TOKEN_FILE.write_text(creds.to_json())
            return creds
    if not config.CREDENTIALS_FILE.exists():
        sys.exit(f"Missing {config.CREDENTIALS_FILE}. Download an OAuth client file from Google Cloud Console.")
    flow = InstalledAppFlow.from_client_secrets_file(str(config.CREDENTIALS_FILE), config.SCOPES)
    creds = flow.run_local_server(port=0)
    config.TOKEN_FILE.write_text(creds.to_json())
    return creds


def create_sheet(creds: Credentials) -> dict:
    if config.SHEET_CONFIG_FILE.exists():
        existing = json.loads(config.SHEET_CONFIG_FILE.read_text())
        if existing.get("spreadsheet_id"):
            return existing
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheet = sheets.spreadsheets().create(
        body={"properties": {"title": "Visa Passport Applications"},
              "sheets": [{"properties": {"title": "Sheet1"}}]}
    ).execute()
    sid = sheet["spreadsheetId"]
    sheets.spreadsheets().values().update(
        spreadsheetId=sid, range="Sheet1!A1", valueInputOption="RAW", body={"values": [HEADERS]}
    ).execute()
    cfg = {"spreadsheet_id": sid, "sheet_name": "Sheet1",
           "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{sid}"}
    config.SHEET_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    return cfg


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--create-sheet", action="store_true")
    args = ap.parse_args()
    creds = get_credentials()
    print(f"Authorised. Token saved to {config.TOKEN_FILE}")
    if args.create_sheet:
        print(json.dumps(create_sheet(creds), indent=2))
