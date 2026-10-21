"""Parser for the machine-readable zone (MRZ) of TD3 passports (ICAO Doc 9303).

The MRZ has check digits, so a successful parse can be *verified*, which is far more
reliable than regexing free OCR text.
"""
import re
from datetime import date

_WEIGHTS = (7, 3, 1)


def _char_value(c: str) -> int:
    if c.isdigit():
        return int(c)
    if c == "<":
        return 0
    return ord(c) - 55  # A=10 ... Z=35


def check_digit(field: str) -> int:
    return sum(_char_value(c) * _WEIGHTS[i % 3] for i, c in enumerate(field)) % 10


def _digit_ok(field: str, digit: str) -> bool:
    if digit == "<":  # optional field left empty
        return set(field) <= {"<"}
    return digit.isdigit() and check_digit(field) == int(digit)


def _to_iso(yymmdd: str, *, birth: bool) -> str:
    if not re.fullmatch(r"\d{6}", yymmdd):
        return ""
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])
    century = 2000
    if birth and yy > date.today().year % 100:
        century = 1900
    try:
        return date(century + yy, mm, dd).isoformat()
    except ValueError:
        return ""


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", "", line).upper().replace("«", "<").replace("‹", "<")


_TO_DIGIT = str.maketrans("OQDILZSGB", "001112568")
_TO_LETTER = str.maketrans("012568", "OIZSGB")


def _fix(segment: str, *, digits: bool) -> str:
    return segment.translate(_TO_DIGIT if digits else _TO_LETTER)


def repair_td3(line1: str, line2: str):
    """Fix typical Tesseract mistakes using the MRZ field layout (digits vs letters).

    Safe by design: the result is still validated with the check digits afterwards, so a wrong
    "repair" cannot silently produce an accepted record.
    """
    names = _fix(line1[5:], digits=False)
    cut = names.find("<<<")  # anything after the first long filler run is padding, not name
    if cut != -1:
        names = names[:cut]
    names = names[:39].ljust(39, "<")  # OCR often adds/drops filler chars; line 1 ends in padding
    l1 = line1[:2] + _fix(line1[2:5], digits=False) + names

    l2 = (
        line2[0:9]
        + _fix(line2[9], digits=True)
        + _fix(line2[10:13], digits=False)
        + _fix(line2[13:20], digits=True)
        + line2[20]
        + _fix(line2[21:28], digits=True)
        + line2[28:42]
        + _fix(line2[42:44], digits=True)
    )
    return l1, l2


def find_mrz(text: str):
    """Return (line1, line2) if two consecutive 44-char MRZ lines are found, else None."""
    lines = [_clean_line(l) for l in text.splitlines()]
    line1_like = re.compile(r"P[A-Z0-9<]{39,47}")  # length tolerant: it ends in filler
    line2_like = re.compile(r"[A-Z0-9<]{44}")      # positional fields: must be exact
    for i in range(len(lines) - 1):
        a, b = lines[i], lines[i + 1]
        if line1_like.fullmatch(a) and line2_like.fullmatch(b):
            return repair_td3(a, b)
    return None


def parse_td3(line1: str, line2: str) -> dict:
    names = line1[5:44].split("<<", 1)
    surname = names[0].replace("<", " ").strip()
    given = names[1].replace("<", " ").strip() if len(names) > 1 else ""

    number = line2[0:9]
    checks = {
        "passport_number": _digit_ok(number, line2[9]),
        "date_of_birth": _digit_ok(line2[13:19], line2[19]),
        "expiry_date": _digit_ok(line2[21:27], line2[27]),
        "personal_number": _digit_ok(line2[28:42], line2[42]),
        "composite": _digit_ok(line2[0:10] + line2[13:20] + line2[21:43], line2[43]),
    }
    return {
        "full_name": f"{given} {surname}".strip(),
        "passport_number": number.rstrip("<"),
        "nationality": line2[10:13].replace("<", ""),
        "issuing_country": line1[2:5].replace("<", ""),
        "date_of_birth": _to_iso(line2[13:19], birth=True),
        "expiry_date": _to_iso(line2[21:27], birth=False),
        "gender": line2[20] if line2[20] in ("M", "F", "X") else "",
        "checks": checks,
        "checks_ok": all(checks.values()),
    }


def parse_mrz_from_text(text: str):
    found = find_mrz(text)
    return parse_td3(*found) if found else None
