"""Flask API called by the n8n workflow, plus an optional public demo page (DEMO_MODE=1)."""
import base64
import binascii
import hmac
import logging
import os
import tempfile
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from . import config
from .extract import extract_passport_info

log = logging.getLogger("visa_processor")
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEMO_SAMPLES = {"sample_passport.png", "sample_expired.png"}


def decode_attachment(data: str) -> bytes:
    """Accept standard or URL-safe base64, with or without padding or a data: prefix."""
    if data.startswith("data:") and "," in data[:100]:
        data = data.split(",", 1)[1]
    data = data.strip().replace("-", "+").replace("_", "/")
    data += "=" * (-len(data) % 4)
    try:
        return base64.b64decode(data)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("attachment_base64 is not valid base64") from exc


def run_pipeline(raw: bytes, ext: str):
    """OCR + extraction. The temp dir (and the passport inside it) is deleted even on failure."""
    from .ocr import ocr_file

    with tempfile.TemporaryDirectory(prefix="passport_") as tmp:
        path = os.path.join(tmp, f"passport{ext}")
        with open(path, "wb") as fh:
            fh.write(raw)
        text = ocr_file(path)
    if not text.strip():
        raise LookupError("OCR found no text. Is the scan clear?")
    return text, extract_passport_info(text)


def _error(message: str, status: int):
    return jsonify({"status": "error", "error": message}), status


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = int(config.MAX_UPLOAD_MB * 1.4 * 1024 * 1024)  # base64 overhead
    hits = defaultdict(deque)  # demo rate limiter: visitor -> request timestamps

    if not config.API_KEY and not config.DEMO_MODE:
        log.warning("API_KEY is not set: the API is unauthenticated. Only run it on localhost.")

    @app.errorhandler(413)
    def too_large(_):
        return _error(f"Payload too large (max {config.MAX_UPLOAD_MB} MB)", 413)

    @app.get("/health")
    def health():
        return jsonify({"status": "running", "demo_mode": config.DEMO_MODE})

    # ------------------------------------------------------------------ n8n endpoint
    @app.post("/process-passport")
    def process_passport():
        if config.DEMO_MODE and not config.API_KEY:
            return _error("Not found", 404)  # public demo hosts expose only /demo/process
        if config.API_KEY and not hmac.compare_digest(
            request.headers.get("X-API-Key", ""), config.API_KEY
        ):
            return _error("Unauthorized", 401)

        body = request.get_json(silent=True) or {}
        filename = os.path.basename(body.get("filename") or "passport.pdf")
        ext = os.path.splitext(filename)[1].lower() or ".pdf"
        if ext not in config.ALLOWED_EXTENSIONS:
            return _error(f"Unsupported file type {ext}. Allowed: pdf, jpg, jpeg, png", 400)

        email_from = body.get("email_from", "")
        email_subject = body.get("email_subject", "")

        try:
            if body.get("attachment_base64"):
                raw = decode_attachment(body["attachment_base64"])
            elif body.get("email_id"):
                from .gmail import get_passport_attachment

                email_from, email_subject, raw, filename = get_passport_attachment(body["email_id"])
                ext = os.path.splitext(filename)[1].lower() or ".pdf"
            else:
                return _error("Provide attachment_base64 or email_id", 400)

            if not raw:
                return _error("No passport attachment found (PDF/JPEG/PNG)", 400)
            if len(raw) > config.MAX_UPLOAD_MB * 1024 * 1024:
                return _error(f"File too large (max {config.MAX_UPLOAD_MB} MB)", 413)

            _, result = run_pipeline(raw, ext)
        except LookupError as exc:
            return _error(str(exc), 422)
        except ValueError as exc:
            return _error(str(exc), 400)
        except Exception:
            log.exception("passport processing failed")  # stack trace only; no passport data logged
            return _error("Internal error while processing the document", 500)

        return jsonify({
            "status": "success",
            "email_from": email_from,
            "email_subject": email_subject,
            "visa_type": body.get("visa_type", "Unknown"),
            "pdf_filename": filename,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            **result,
        })

    # ------------------------------------------------------------------ public demo
    if config.DEMO_MODE:

        @app.get("/")
        def demo_page():
            return send_from_directory(STATIC_DIR, "demo.html")

        @app.get("/samples/<name>")
        def demo_sample(name):
            if name not in DEMO_SAMPLES:
                return _error("Not found", 404)
            return send_from_directory(config.SAMPLES_DIR, name)

        @app.post("/demo/process")
        def demo_process():
            visitor = (request.headers.get("X-Forwarded-For", request.remote_addr or "") or "").split(",")[0].strip()
            now, window = time.time(), hits[visitor]
            while window and now - window[0] > 600:
                window.popleft()
            if len(window) >= config.DEMO_RATE_LIMIT:
                return _error("Demo rate limit reached. Please try again in a few minutes.", 429)
            window.append(now)

            upload = request.files.get("file")
            if upload is None or not upload.filename:
                return _error("Choose a passport image or PDF first.", 400)
            ext = os.path.splitext(os.path.basename(upload.filename))[1].lower()
            if ext not in config.ALLOWED_EXTENSIONS:
                return _error("Unsupported file type. Use PDF, JPG or PNG.", 400)
            raw = upload.read()
            if len(raw) > config.MAX_UPLOAD_MB * 1024 * 1024:
                return _error(f"File too large (max {config.MAX_UPLOAD_MB} MB)", 413)

            try:
                text, result = run_pipeline(raw, ext)
            except LookupError as exc:
                return _error(str(exc), 422)
            except Exception:
                log.exception("demo processing failed")
                return _error("Could not process this file.", 500)
            return jsonify({"status": "success", "ocr_text": text[:4000], **result})

    return app


if __name__ == "__main__":
    create_app().run(host=config.HOST, port=config.PORT, debug=False)
