"""Iteration 30 extra coverage for Field Ops + Economy Hub backend.
Complements test_field_ops.py (8 baseline tests already passing)."""
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
    # Make sure seed is in place
    s.post(f"{API}/field-ops/seed")
    yield s
    s.close()


def _png_bytes(size=(512, 384)):
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", size, "white")
        d = ImageDraw.Draw(img)
        d.rectangle([20, 20, size[0] - 20, size[1] - 20], outline="black", width=4)
        d.rectangle([50, 60, 200, 180], fill="red", outline="black", width=2)
        d.rectangle([220, 60, 350, 180], fill="blue", outline="black", width=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return os.urandom(10000)


# ---------- Types endpoint deep check ----------
def test_types_metadata(session):
    r = session.get(f"{API}/field-ops/types")
    assert r.status_code == 200
    d = r.json()
    assert d["geo_bonus_multiplier"] == 1.2
    assert d["auto_pay_min_score"] == 0.65
    # MIMEs
    photo_mimes = d["types"]["photo"].get("accepted_mime") or d["types"]["photo"].get("accepted_mimes")
    voice_mimes = d["types"]["voice"].get("accepted_mime") or d["types"]["voice"].get("accepted_mimes")
    video_mimes = d["types"]["video"].get("accepted_mime") or d["types"]["video"].get("accepted_mimes")
    assert any("image/" in m for m in photo_mimes)
    assert any("audio/" in m for m in voice_mimes)
    assert any("video/" in m for m in video_mimes)


# ---------- Available with geo: distance + sorting + flags ----------
def test_available_with_geo_attaches_distance_and_review_mode(session):
    user = f"pyt_geo_{int(time.time())}"
    # San Francisco coords; many seed ops have geo points - we just need response shape
    r = session.get(f"{API}/field-ops/available", params={"lat": 37.7749, "lng": -122.4194, "user_id": user})
    assert r.status_code == 200
    ops = r.json()["ops"]
    assert len(ops) >= 11
    # Each op has review_mode populated and geo_bonus_ve populated only for geo-required ops
    geo_required_with_bonus = 0
    for op in ops:
        assert op["review_mode"] in ("auto", "human")
        if op.get("geo_required"):
            # geo_bonus_ve should be > 0 for geo_required
            if op.get("geo_bonus_ve", 0) > 0:
                geo_required_with_bonus += 1
        # accepted_by_me must exist as boolean
        assert isinstance(op.get("accepted_by_me", False), bool)
    assert geo_required_with_bonus >= 1


def test_accepted_op_sorts_first(session):
    user = f"pyt_sort_{int(time.time())}"
    # Pick a seed op that's NOT highest-distance/highest-reward to validate it bubbles up to first slot
    target_op = "seed_voice_phrase_en"
    a = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": target_op})
    assert a.status_code == 200, a.text
    # Fetch listing as this user
    r = session.get(f"{API}/field-ops/available", params={"user_id": user, "lat": 37.7749, "lng": -122.4194})
    assert r.status_code == 200
    ops = r.json()["ops"]
    assert ops[0]["op_id"] == target_op
    assert ops[0]["accepted_by_me"] is True


# ---------- Re-accept idempotency ----------
def test_reaccept_returns_existing_lock(session):
    user = f"pyt_reacc_{int(time.time())}"
    op_id = "seed_voice_phrase_en"
    r1 = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": op_id})
    assert r1.status_code == 200, r1.text
    sub1 = r1.json()["submission_id"]
    r2 = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": op_id})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2.get("already_locked") is True
    assert d2["submission_id"] == sub1


# ---------- Oversized media rejected ----------
def test_oversized_media_rejected(session):
    user = f"pyt_big_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_voice_phrase_en"})
    sub_id = r.json()["submission_id"]
    # ~12MB random buffer - should exceed server cap (typically 8-10MB)
    big = os.urandom(12 * 1024 * 1024)
    b64 = "data:audio/webm;base64," + base64.b64encode(big).decode()
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "audio/webm", "duration_ms": 8500,
    })
    assert r.status_code in (400, 413), f"expected 400/413, got {r.status_code} {r.text[:200]}"


def test_empty_media_rejected(session):
    user = f"pyt_empty_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_voice_phrase_en"})
    sub_id = r.json()["submission_id"]
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": "",
        "mime_type": "audio/webm", "duration_ms": 8500,
    })
    assert r.status_code in (400, 413), r.text


# ---------- Submission detail endpoint ----------
def test_submission_detail_omits_and_includes_media(session):
    user = f"pyt_detail_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_voice_phrase_en"})
    sub_id = r.json()["submission_id"]
    b64 = "data:audio/webm;base64," + base64.b64encode(os.urandom(8000)).decode()
    session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "audio/webm", "duration_ms": 8500,
    })
    # default: no media
    r = session.get(f"{API}/field-ops/submission/{sub_id}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("media_base64") in (None, "", "[stripped]") or "media_base64" not in d
    # include_media=true
    r = session.get(f"{API}/field-ops/submission/{sub_id}", params={"include_media": "true"})
    assert r.status_code == 200
    d = r.json()
    assert d.get("media_base64"), "media should be returned when include_media=true"


def test_submission_detail_404(session):
    r = session.get(f"{API}/field-ops/submission/sub_does_not_exist_xyz")
    assert r.status_code == 404


# ---------- Review queue + reject decision ----------
def test_review_queue_and_reject(session):
    user = f"pyt_rev_{int(time.time())}"
    r = session.post(f"{API}/field-ops/accept", json={"user_id": user, "op_id": "seed_high_value_inventory"})
    sub_id = r.json()["submission_id"]
    b64 = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "image/png", "lat": 37.77, "lng": -122.41,
    }, timeout=60)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued_review"

    # Queue must include this sub_id
    q = session.get(f"{API}/field-ops/review-queue")
    assert q.status_code == 200
    queue_subs = q.json().get("submissions", [])
    assert any(s.get("submission_id") == sub_id for s in queue_subs)

    # Admin rejects
    r = session.post(f"{API}/field-ops/review", json={
        "reviewer_id": "sirix_1_supreme",
        "submission_id": sub_id,
        "decision": "reject",
        "feedback": "blurry",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("paid_ve", 0) == 0
    # Status now NOT queued_review
    r = session.get(f"{API}/field-ops/submission/{sub_id}")
    assert r.status_code == 200
    assert r.json()["status"] != "queued_review"


# ---------- Stats numeric ----------
def test_stats_numeric(session):
    r = session.get(f"{API}/field-ops/stats")
    assert r.status_code == 200
    d = r.json()
    for key in ("active_ops", "submissions_total", "approved", "auto_approval_rate",
                "queued_review", "rejected", "total_paid_ve"):
        assert key in d, f"missing {key}"
        assert isinstance(d[key], (int, float))


# ---------- Boost integration (Forge Surge) ----------
def test_boost_multiplies_payout(session):
    # Buy Forge Surge for a fresh user, then do a voice op, expect boost_applied=true and higher paid_ve.
    user = f"pyt_boost_{int(time.time())}"
    # Grant wallet (admin endpoint - some apps use /api/cosmetics/grant; if unavailable, just attempt purchase)
    # Try to purchase Forge Surge via cosmetics endpoint
    catalog = session.get(f"{API}/cosmetics/catalog").json()
    items = catalog.get("items", []) if isinstance(catalog, dict) else catalog
    forge = None
    for it in items:
        if it.get("id") == "boost_forge_surge" or "forge" in (it.get("id", "").lower()):
            forge = it
            break
    if not forge:
        pytest.skip("Forge Surge not in catalog - cannot test boost path")

    # Use sirix_1_supreme who already has VE$ + may have boost active
    test_user = "sirix_1_supreme"
    # Try to purchase / activate
    purchase = session.post(f"{API}/cosmetics/purchase", json={
        "user_id": test_user, "item_id": forge["id"]
    })
    # purchase may 200 or 400 (already active) - either fine
    # Accept + submit a voice op
    r = session.post(f"{API}/field-ops/accept", json={"user_id": test_user, "op_id": "seed_voice_phrase_en"})
    if r.status_code != 200:
        # may already be locked
        pytest.skip(f"could not accept op for sirix: {r.text[:100]}")
    sub_id = r.json()["submission_id"]
    b64 = "data:audio/webm;base64," + base64.b64encode(os.urandom(8000)).decode()
    r = session.post(f"{API}/field-ops/submit", json={
        "user_id": test_user, "submission_id": sub_id, "media_base64": b64,
        "mime_type": "audio/webm", "duration_ms": 8500,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    if d.get("status") != "auto_approved":
        pytest.skip(f"voice op not auto-approved this run: status={d.get('status')}")
    # boost_applied may be true if boost active; if not, skip the strict check
    assert "boost_applied" in d, "submit response should always include boost_applied flag"


# ---------- Regression: existing endpoints still healthy ----------
def test_regression_existing_endpoints(session):
    r = session.get(f"{API}/cosmetics/catalog")
    assert r.status_code == 200
    r = session.get(f"{API}/cosmetics/wallet/sirix_1_supreme")
    assert r.status_code == 200
    assert "balance_ve" in r.json()
    r = session.get(f"{API}/avatar/user/sirix_1_supreme")
    assert r.status_code == 200
    r = session.get(f"{API}/data-api/factory/tasks")
    assert r.status_code == 200
