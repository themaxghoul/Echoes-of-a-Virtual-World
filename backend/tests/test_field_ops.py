"""Regression tests for Field Ops + Economy Hub backend (June 2026).
Uses requests + REACT_APP_BACKEND_URL to match existing test conventions."""
import os
import io
import base64
import time
import pytest
import requests


def _load_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)
_load_env()
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    s.close()


def _png_bytes():
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (512, 384), "white")
        d = ImageDraw.Draw(img)
        d.rectangle([20, 20, 490, 360], outline="black", width=4)
        d.rectangle([50, 60, 200, 180], fill="red", outline="black", width=2)
        d.rectangle([220, 60, 350, 180], fill="blue", outline="black", width=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return os.urandom(10000)


def test_types_and_seed(session):
    r = session.get(f"{API}/field-ops/types")
    assert r.status_code == 200
    d = r.json()
    assert set(d["types"].keys()) == {"photo", "voice", "video"}
    assert d["auto_pay_threshold_ve"] == 5.0
    r = session.post(f"{API}/field-ops/seed")
    assert r.status_code == 200
    assert r.json()["total_ops"] >= 11


def test_available_listing(session):
    r = session.get(f"{API}/field-ops/available")
    assert r.status_code == 200
    ops = r.json()["ops"]
    assert len(ops) >= 11
    for op in ops:
        assert op["review_mode"] in ("auto", "human")


def test_voice_auto_approved_pays_wallet(session):
    user = f"pyt_voice_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_voice_phrase_en"})
    assert r.status_code == 200, r.text
    sub_id = r.json()["submission_id"]
    b64 = "data:audio/webm;base64," + base64.b64encode(os.urandom(8000)).decode()
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "audio/webm", "duration_ms": 8500,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "auto_approved"
    assert d["paid_ve"] > 0
    w = session.get(f"{API}/cosmetics/wallet/{user}")
    assert w.json()["balance_ve"] >= d["paid_ve"]


def test_high_value_routes_to_review_and_admin_approves(session):
    user = f"pyt_review_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_high_value_inventory"})
    assert r.status_code == 200, r.text
    sub_id = r.json()["submission_id"]

    b64 = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "image/png", "lat": 37.77, "lng": -122.41,
    }, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["requires_review"] is True
    assert d["status"] == "queued_review"
    assert d["paid_ve"] == 0.0

    r = session.post(f"{API}/field-ops/review", json={
        "reviewer_id": "sirix_1_supreme", "submission_id": sub_id,
        "decision": "approve", "feedback": "ok",
    })
    assert r.status_code == 200, r.text
    review = r.json()
    assert review["paid_ve"] > 0
    w = session.get(f"{API}/cosmetics/wallet/{user}")
    assert w.json()["balance_ve"] >= review["paid_ve"]


def test_non_admin_cannot_review(session):
    r = session.post(f"{API}/field-ops/review", json={
        "reviewer_id": "random_nobody",
        "submission_id": "sub_nonexistent",
        "decision": "approve",
    })
    assert r.status_code == 403, r.text


def test_bad_mime_rejected(session):
    user = f"pyt_mime_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_voice_phrase_en"})
    sub_id = r.json()["submission_id"]
    b64 = "data:image/png;base64," + base64.b64encode(os.urandom(5000)).decode()
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "image/png",
    })
    assert r.status_code == 400


def test_stats_endpoint(session):
    r = session.get(f"{API}/field-ops/stats")
    assert r.status_code == 200
    d = r.json()
    for key in ("active_ops", "submissions_total", "approved", "queued_review", "rejected", "total_paid_ve"):
        assert key in d


def test_my_submissions(session):
    user = f"pyt_subs_{int(time.time())}"
    # Accept + auto-submit one voice op
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_voice_phrase_en"})
    sub_id = r.json()["submission_id"]
    b64 = "data:audio/webm;base64," + base64.b64encode(os.urandom(8000)).decode()
    session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "audio/webm", "duration_ms": 8500,
    })
    r = session.get(f"{API}/field-ops/my-submissions/{user}")
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 1
    assert d["submissions"][0]["op_title"]
    # media_base64 stripped
    assert "media_base64" not in d["submissions"][0]
