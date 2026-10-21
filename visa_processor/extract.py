"""Turn OCR text into structured passport fields.

Strategy, best to worst:
  1. MRZ    - parsed and check-digit verified (deterministic, no API needed)
  2. Gemini - LLM extraction when an API key is configured
  3. Regex  - labelled-field fallback
"""
import json
import re
from datetime import date, datetime

from . import config
from .mrz import parse_mrz_from_text

REQUIRED = ("full_name", "passport_number", "nationality", "date_of_birth", "expiry_date")
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y")


def _find(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def extract_with_regex(text: str) -> dict:
    given = _find(r"Given\s+Names?\s*[:.]\s*([^\n]+)", text)
    surname = _find(r"Surname\s*[:.]\s*([^\n]+)", text)
    return {
        "full_name": f"{given} {surname}".strip(),
        # needs a "No/Number" label and 6-9 alphanumerics; the old pattern captured stray words
        "passport_number": _find(r"Passport\s*(?:No\.?|Number|#)\s*[:.]?\s*([A-Z0-9]{6,9})\b", text),
        "nationality": _find(r"Nationality\s*[:.]\s*([^\n]+)", text),
        "date_of_birth": _find(r"Date\s+of\s+Birth\s*[:.]\s*([^\n]+)", text),
        "expiry_date": _find(r"Date\s+of\s+Expiry\s*[:.]\s*([^\n]+)", text),
        "gender": _find(r"\bSex\s*[:.]\s*([MFX])\b", text).upper(),
        "issuing_country": _find(r"(?:Issuing\s+(?:Country|State)|Country\s+of\s+Issue)\s*[:.]\s*([^\n]+)", text),
    }


def extract_with_gemini(text: str, api_key: str, model: str) -> dict:
    from google import genai  # lazy import: only needed when a key is configured

    prompt = (
        "Extract passport fields from this OCR text. Use an empty string for anything not "
        "present; never guess. Dates must be YYYY-MM-DD. Return JSON with exactly these keys: "
        "full_name, passport_number, nationality, date_of_birth, expiry_date, gender, "
        f"issuing_country.\n\nOCR TEXT:\n{text}"
    )
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model, contents=prompt, config={"response_mime_type": "application/json"}
    )
    data = json.loads(resp.text)
    return {k: str(data.get(k, "") or "").strip() for k in (*REQUIRED, "gender", "issuing_country")}


def _parse_date(value: str):
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _finalise(fields: dict, method: str, warnings: list) -> dict:
    missing = [f for f in REQUIRED if not fields.get(f)]
    expiry = _parse_date(fields.get("expiry_date", ""))
    if expiry and expiry < date.today():
        warnings.append("passport is expired")
    return {
        **fields,
        "missing_fields": missing,
        "warnings": warnings,
        "extraction_method": method,
        # strict on purpose: every required field present and not expired
        "is_valid": not missing and "passport is expired" not in warnings,
    }


def extract_passport_info(ocr_text: str, api_key: str = "", model: str = "") -> dict:
    api_key = api_key or config.GEMINI_API_KEY
    model = model or config.GEMINI_MODEL
    warnings: list = []

    mrz = parse_mrz_from_text(ocr_text)
    checks = {"mrz_checks": mrz["checks"]} if mrz else {}
    if mrz:
        if mrz["checks_ok"]:
            fields = {k: v for k, v in mrz.items() if k not in ("checks", "checks_ok")}
            return {**_finalise(fields, "mrz", warnings), **checks}
        warnings.append("MRZ found but check digits failed; falling back")

    if api_key:
        try:
            return {**_finalise(extract_with_gemini(ocr_text, api_key, model), "gemini", warnings), **checks}
        except Exception as exc:  # network, quota, bad JSON ... never lose the document over it
            warnings.append(f"gemini failed ({type(exc).__name__}); used regex fallback")

    return {**_finalise(extract_with_regex(ocr_text), "regex", warnings), **checks}
