import base64

import pytest

from visa_processor import api, config

SPECIMEN = (
    "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
    "L898902C36UTO7408122F1204159ZE184226B<<<<<10\n"
)
B64 = base64.b64encode(b"%PDF-fake").decode()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "secret")
    monkeypatch.setattr("visa_processor.ocr.ocr_file", lambda path: SPECIMEN)
    return api.create_app().test_client()


def post(client, body, key="secret"):
    return client.post("/process-passport", json=body, headers={"X-API-Key": key})


def test_health(client):
    assert client.get("/health").json["status"] == "running"


def test_requires_api_key(client):
    assert post(client, {"attachment_base64": B64}, key="wrong").status_code == 401


def test_success(client):
    r = post(client, {"attachment_base64": B64, "filename": "p.pdf", "visa_type": "Work Visa"})
    assert r.status_code == 200
    assert r.json["full_name"] == "ANNA MARIA ERIKSSON"
    assert r.json["visa_type"] == "Work Visa"
    assert r.json["extraction_method"] == "mrz"


def test_rejects_bad_extension(client):
    r = post(client, {"attachment_base64": B64, "filename": "evil.exe"})
    assert r.status_code == 400


def test_rejects_bad_base64(client):
    r = post(client, {"attachment_base64": "!!!notbase64!!!"})
    assert r.status_code == 400


def test_needs_input(client):
    assert post(client, {}).status_code == 400


def test_path_traversal_filename_is_sanitised(client):
    r = post(client, {"attachment_base64": B64, "filename": "../../etc/passwd.pdf"})
    assert r.status_code == 200
    assert r.json["pdf_filename"] == "passwd.pdf"
