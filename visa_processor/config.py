"""Central configuration. Everything is read from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("VISA_PROCESSOR_HOME", Path(__file__).resolve().parent.parent))
CREDENTIALS_FILE = BASE_DIR / "credentials.json"   # Google OAuth client file (never commit)
TOKEN_FILE = BASE_DIR / "token.json"               # saved OAuth token (never commit)
SHEET_CONFIG_FILE = BASE_DIR / "sheet_config.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Shared secret the caller (n8n) must send in the X-API-Key header. Empty = auth disabled.
API_KEY = os.environ.get("API_KEY", "")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))

# Public demo mode: serves a web page where anyone can try the pipeline with a fictional passport.
DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")
SAMPLES_DIR = BASE_DIR / "samples"
DEMO_RATE_LIMIT = int(os.environ.get("DEMO_RATE_LIMIT", "20"))  # requests per 10 min per visitor

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))
MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "5"))
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
