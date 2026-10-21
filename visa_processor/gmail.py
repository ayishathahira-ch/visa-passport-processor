"""Fallback path: fetch a passport attachment straight from Gmail when n8n only sends an email_id."""
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from . import config


def get_credentials() -> Credentials:
    if not config.TOKEN_FILE.exists():
        raise RuntimeError("No token.json found. Run: python scripts/setup_google.py")
    creds = Credentials.from_authorized_user_file(str(config.TOKEN_FILE), config.SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        config.TOKEN_FILE.write_text(creds.to_json())
    return creds


def _is_passport_file(part: dict) -> bool:
    name = (part.get("filename") or "").lower()
    return bool(name) and name.endswith(tuple(config.ALLOWED_EXTENSIONS))


def _walk(parts):
    for part in parts:
        yield part
        yield from _walk(part.get("parts", []))


def get_passport_attachment(email_id: str):
    """Return (from, subject, raw_bytes, filename). raw_bytes is None if nothing suitable found."""
    service = build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)
    msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}

    for part in _walk([msg["payload"]]):
        if not _is_passport_file(part):
            continue
        body = part.get("body", {})
        data = body.get("data")
        if not data and body.get("attachmentId"):
            att = service.users().messages().attachments().get(
                userId="me", messageId=email_id, id=body["attachmentId"]
            ).execute()
            data = att["data"]
        if data:
            data += "=" * (-len(data) % 4)
            return headers.get("from", ""), headers.get("subject", ""), base64.urlsafe_b64decode(data), part["filename"]
    return headers.get("from", ""), headers.get("subject", ""), None, ""
