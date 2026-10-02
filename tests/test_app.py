"""
Tests for the CleanCity web app.  Run with:  python -m pytest
The CNN is replaced by a fake result so tests are fast and don't need TensorFlow.
"""

import io
import json
import re

import pytest
from PIL import Image

import app as app_module
from app import create_app

FAKE_RESULT = {
    "is_garbage": True, "garbage_type": "Plastic", "confidence": 91.5, "uncertain": False,
    "danger_level": "High", "recommended_action": "Collect and send to plastic recycling",
    "all_predictions": {"Plastic": 91.5, "Paper": 8.5},
}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "predict_garbage", lambda image_bytes, model: dict(FAKE_RESULT))
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "LOAD_MODEL": False,
        "TEAM_PASSWORD": "secret",
        "DATABASE": str(tmp_path / "test.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "LEGACY_JSON": str(tmp_path / "reports.json"),
    })


@pytest.fixture
def client(app):
    return app.test_client()


def image_file(fmt="PNG", name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "red").save(buf, fmt)
    buf.seek(0)
    return buf, name


def submit(client, **extra):
    data = {"photo": image_file(), "description": "Pile near gate"}
    data.update(extra)
    return client.post("/submit", data=data, content_type="multipart/form-data")


def csrf(client, page="/team"):
    html = client.get(page).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def login(client, password="secret"):
    token = csrf(client, "/team/login")
    return client.post("/team/login", data={"password": password, "csrf_token": token})


# ── User side ─────────────────────────────────────────────────────────────────
def test_home_page_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Sir Syed University" in res.data


def test_submit_saves_report_and_photo(client, app):
    res = submit(client)
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    assert data["ai_result"]["garbage_type"] == "Plastic"

    login(client)
    reports = client.get("/api/reports").get_json()
    assert len(reports) == 1
    assert reports[0]["description"] == "Pile near gate"
    assert reports[0]["status"] == "pending"
    photo = reports[0]["photo"]
    assert photo.endswith(".jpg")
    assert (app.config["UPLOAD_FOLDER"] and __import__("os").path.exists(
        __import__("os").path.join(app.config["UPLOAD_FOLDER"], photo)))


def test_submit_ids_are_unique(client):
    ids = [submit(client).get_json()["report_id"] for _ in range(3)]
    assert len(set(ids)) == 3


def test_submit_rejects_missing_photo(client):
    res = client.post("/submit", data={"description": "x"})
    assert res.status_code == 400


def test_submit_rejects_fake_image(client):
    res = submit(client, photo=(io.BytesIO(b"not really an image"), "evil.png"))
    assert res.status_code == 400
    assert "not a valid image" in res.get_json()["error"]


def test_submit_rejects_wrong_extension(client):
    res = submit(client, photo=image_file(name="photo.exe"))
    assert res.status_code == 400


def test_description_is_trimmed_to_limit(client):
    submit(client, description="a" * 2000)
    login(client)
    assert len(client.get("/api/reports").get_json()[0]["description"]) == 500


# ── Team side ─────────────────────────────────────────────────────────────────
def test_team_pages_require_login(client):
    assert client.get("/team").status_code == 302
    assert client.get("/api/reports").status_code == 401


def test_wrong_password_rejected(client):
    res = login(client, "wrong")
    assert b"Wrong password" in res.data
    assert client.get("/team").status_code == 302


def test_login_and_dashboard(client):
    submit(client)
    login(client)
    res = client.get("/team")
    assert res.status_code == 200
    assert b"Report #1" in res.data
    assert b"Plastic" in res.data


def test_update_status(client):
    submit(client)
    login(client)
    token = csrf(client)
    res = client.post("/update_status", data={"report_id": 1, "status": "in_progress", "csrf_token": token})
    assert res.status_code == 302
    report = client.get("/api/reports").get_json()[0]
    assert report["status"] == "in_progress"
    assert report["updated_at"]


def test_update_status_validation(client):
    submit(client)
    login(client)
    token = csrf(client)
    assert client.post("/update_status", data={"report_id": 1, "status": "hacked", "csrf_token": token}).status_code == 400
    assert client.post("/update_status", data={"report_id": "abc", "status": "done", "csrf_token": token}).status_code == 400
    assert client.post("/update_status", data={"report_id": 99, "status": "done", "csrf_token": token}).status_code == 404


def test_post_without_csrf_token_is_blocked(client):
    submit(client)
    login(client)
    res = client.post("/update_status", data={"report_id": 1, "status": "done"})
    assert res.status_code == 400


def test_delete_report_removes_photo(client, app):
    import os
    submit(client)
    login(client)
    photo = client.get("/api/reports").get_json()[0]["photo"]
    token = csrf(client)
    client.post("/delete_report", data={"report_id": 1, "csrf_token": token})
    assert client.get("/api/reports").get_json() == []
    assert not os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], photo))


def test_login_redirect_stays_on_site(client):
    token = csrf(client, "/team/login")
    res = client.post("/team/login?next=//evil.com", data={"password": "secret", "csrf_token": token})
    assert res.headers["Location"] == "/team"


# ── Old reports.json import ───────────────────────────────────────────────────
def test_legacy_json_is_imported(tmp_path, monkeypatch):
    legacy = tmp_path / "reports.json"
    legacy.write_text(json.dumps([{
        "id": 1, "photo": "old.png", "latitude": "1", "longitude": "2", "address": "A",
        "description": "old report", "status": "done", "submitted_at": "2026-01-01 10:00:00",
        "updated_at": None, "ai_result": FAKE_RESULT,
    }]))
    app = create_app({"TESTING": True, "SECRET_KEY": "t", "LOAD_MODEL": False, "TEAM_PASSWORD": "secret",
                      "DATABASE": str(tmp_path / "db.sqlite"), "UPLOAD_FOLDER": str(tmp_path / "up"),
                      "LEGACY_JSON": str(legacy)})
    client = app.test_client()
    login(client)
    reports = client.get("/api/reports").get_json()
    assert reports[0]["description"] == "old report" and reports[0]["status"] == "done"
    assert not legacy.exists()   # renamed to reports.json.imported
