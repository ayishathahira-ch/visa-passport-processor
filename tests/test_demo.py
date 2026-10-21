import io

import pytest

from visa_processor import api, config

SPECIMEN = (
    "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
    "L898902C36UTO7408122F1204159ZE184226B<<<<<10\n"
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "API_KEY", "")
    monkeypatch.setattr(config, "DEMO_RATE_LIMIT", 3)
    monkeypatch.setattr("visa_processor.ocr.ocr_file", lambda path: SPECIMEN)
    return api.create_app().test_client()


def upload(client, name="p.png", data=b"fake"):
    return client.post("/demo/process", data={"file": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_demo_page_served(client):
    r = client.get("/")
    assert r.status_code == 200 and b"Visa Passport Processor" in r.data


def test_demo_process_returns_fields_and_mrz_checks(client):
    r = upload(client)
    assert r.status_code == 200
    assert r.json["full_name"] == "ANNA MARIA ERIKSSON"
    assert all(r.json["mrz_checks"].values())
    assert "ocr_text" in r.json


def test_demo_rejects_bad_type_and_missing_file(client):
    assert upload(client, name="x.exe").status_code == 400
    assert client.post("/demo/process", data={}).status_code == 400


def test_demo_rate_limit(client):
    codes = [upload(client).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_samples_whitelist(client):
    assert client.get("/samples/sample_passport.png").status_code == 200
    assert client.get("/samples/../README.md").status_code == 404
    assert client.get("/samples/secret.png").status_code == 404


def test_n8n_endpoint_disabled_in_public_demo(client):
    assert client.post("/process-passport", json={}).status_code == 404


def test_demo_page_absent_when_not_demo_mode(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", False)
    assert api.create_app().test_client().get("/").status_code == 404
