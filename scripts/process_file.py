#!/usr/bin/env python3
"""Run the full OCR + extraction pipeline on a local file (no n8n / Gmail needed).

    python scripts/process_file.py samples/specimen_passport.png
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visa_processor.extract import extract_passport_info  # noqa: E402
from visa_processor.ocr import ocr_file  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(extract_passport_info(ocr_file(sys.argv[1])), indent=2))
