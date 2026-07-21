"""
Iteration 29 - VE$ Boutique, Pixel Avatar, Task Workbench, Scheduler
Tests:
 - /api/cosmetics/catalog, /purchase, /equip, /owned, /spotlight
 - /api/avatar/user, /api/avatar/palettes
 - /api/data-api/factory tasks claim/submit (with boost), scheduler/status
 - /api/profile/customization (no profile_picture/profile_logo), customization-options (premium_chat_colors)
"""
import os
import uuid
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
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

EXISTING_USER = "sirix_1_supreme"  # ~4200 VE$, owns frame_neon, color_neon_pink, palette_neon, active boost, saved avatar


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def fresh_user(session):
    """Create a brand-new user_id with 0 balance for insufficient-balance tests."""
    uid = f"TEST_pyt_{uuid.uuid4().hex[:8]}"
    return uid


# ============ COSMETICS CATALOG ============
class TestCosmeticsCatalog:
    def test_catalog_returns_24_items_with_flags(self, session):
        r = session.get(f"{API}/cosmetics/catalog", params={"user_id": EXISTING_USER})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data or "catalog" in data, f"keys: {list(data.keys())}"
        items = data.get("items") or data.get("catalog")
        assert isinstance(items, list)
        assert len(items) == 24, f"expected 24 items got {len(items)}"
        # owned/equipped flags + balance
        assert "balance_ve" in data
        first = items[0]
        assert "owned" in first and "equipped" in first
        # Existing user should own frame_neon
        frame_neon = next((i for i in items if i.get("item_id") == "frame_neon" or i.get("id") == "frame_neon"), None)
        assert frame_neon is not None
        assert frame_neon["owned"] is True
        assert frame_neon["equipped"] is True


# ============ COSMETICS PURCHASE ============
class TestCosmeticsPurchase:
    def test_purchase_duplicate_non_consumable_blocked(self, session):
        # sirix already owns frame_neon
        r = session.post(f"{API}/cosmetics/purchase", json={
            "user_id": EXISTING_USER, "item_id": "frame_neon"
        })
        assert r.status_code == 400, r.text
        assert "already owned" in r.text.lower() or "owned" in r.text.lower()

    def test_purchase_insufficient_balance(self, session, fresh_user):
        r = session.post(f"{API}/cosmetics/purchase", json={
            "user_id": fresh_user, "item_id": "frame_gold"  # 600 VE$
        })
        assert r.status_code == 400, r.text
        assert "insufficient" in r.text.lower() or "balance" in r.text.lower()

    def test_purchase_unknown_item(self, session):
        r = session.post(f"{API}/cosmetics/purchase", json={
            "user_id": EXISTING_USER, "item_id": "bogus_item_xxx"
        })
        assert r.status_code in (400, 404)

    def test_purchase_then_owned(self, session):
        # Buy cheapest title (50 VE$)
        # First check if owned
        owned_r = session.get(f"{API}/cosmetics/owned/{EXISTING_USER}")
        assert owned_r.status_code == 200
        owned_items = owned_r.json()
        owned_list = owned_items.get("owned", []) if isinstance(owned_items, dict) else owned_items
        owned_ids = [o.get("item_id") if isinstance(o, dict) else o for o in owned_list]
        if "title_pioneer" not in owned_ids:
            r = session.post(f"{API}/cosmetics/purchase", json={
                "user_id": EXISTING_USER, "item_id": "title_pioneer"
            })
            assert r.status_code == 200, r.text
        # Re-fetch owned
        owned_r2 = session.get(f"{API}/cosmetics/owned/{EXISTING_USER}")
        owned2 = owned_r2.json()
        items2 = owned2.get("owned", []) if isinstance(owned2, dict) else owned2
        owned_ids2 = [o.get("item_id") if isinstance(o, dict) else o for o in items2]
        assert "title_pioneer" in owned_ids2


# ============ COSMETICS EQUIP ============
class TestCosmeticsEquip:
    def test_equip_unowned_returns_403(self, session):
        r = session.post(f"{API}/cosmetics/equip", json={
            "user_id": EXISTING_USER, "item_id": "frame_prismatic"  # legendary, prob unowned
        })
        # Could be 403 if not owned
        if r.status_code == 200:
            # already owned somehow - skip
            pytest.skip("frame_prismatic is owned; can't test unowned-equip")
        assert r.status_code == 403, r.text

    def test_equip_title_then_unequip_frame(self, session):
        # Equip owned title_pioneer
        r = session.post(f"{API}/cosmetics/equip", json={
            "user_id": EXISTING_USER, "item_id": "title_pioneer"
        })
        assert r.status_code == 200, r.text
        # Unequip frame: 'none:frame'
        r2 = session.post(f"{API}/cosmetics/equip", json={
            "user_id": EXISTING_USER, "item_id": "none:frame"
        })
        assert r2.status_code == 200, r2.text
        # Re-equip frame_neon for cleanliness
        session.post(f"{API}/cosmetics/equip", json={"user_id": EXISTING_USER, "item_id": "frame_neon"})


# ============ BOOSTS ============
class TestBoosts:
    def test_owned_shows_active_boosts(self, session):
        r = session.get(f"{API}/cosmetics/owned/{EXISTING_USER}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "active_boosts" in data, f"keys: {list(data.keys())}"
        assert isinstance(data["active_boosts"], list)


# ============ AVATAR ============
class TestAvatar:
    def test_get_avatar_returns_saved(self, session):
        r = session.get(f"{API}/avatar/user/{EXISTING_USER}")
        assert r.status_code == 200, r.text
        data = r.json()
        # Existing user has saved avatar
        assert data.get("pixels") is not None or data.get("data_url") is not None or data.get("avatar") is not None

    def test_save_avatar_valid_4096_pixels(self, session):
        pixels = [-1] * 4096
        pixels[0] = 0
        pixels[1] = 1
        payload = {
            "pixels": pixels,
            "palette": ["#000000", "#FFFFFF"],
            "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgAAIAAAUAAen63NgAAAAASUVORK5CYII="
        }
        r = session.put(f"{API}/avatar/user/{EXISTING_USER}", json=payload)
        assert r.status_code == 200, r.text

    def test_save_avatar_wrong_pixel_count_returns_400(self, session):
        payload = {
            "pixels": [0] * 100,  # wrong size
            "palette": ["#000000"],
            "data_url": "data:image/png;base64,xxx"
        }
        r = session.put(f"{API}/avatar/user/{EXISTING_USER}", json=payload)
        assert r.status_code == 400, r.text

    def test_palettes_returns_base_plus_packs(self, session):
        r = session.get(f"{API}/avatar/palettes", params={"user_id": EXISTING_USER})
        assert r.status_code == 200, r.text
        data = r.json()
        # Expect base palette (32 colors) + 4 packs
        assert "base" in data or "base_palette" in data or "colors" in data
        assert "packs" in data
        packs = data["packs"]
        assert isinstance(packs, list)
        assert len(packs) >= 4
        # owned flag on palette_neon
        neon = next((p for p in packs if p.get("item_id") == "palette_neon" or p.get("id") == "palette_neon"), None)
        if neon:
            assert neon.get("owned") is True


# ============ SPOTLIGHT ============
class TestSpotlight:
    def test_spotlight_purchase_requires_avatar(self, session, fresh_user):
        # First give the fresh user enough balance via direct? Skip if no admin endpoint.
        # Actually if balance check happens first, we'd get insufficient. So let's check error path:
        # Use EXISTING_USER to test that with avatar saved, spotlight purchase works.
        # But spotlight_24h is consumable so duplicate not blocked.
        # Test path: fresh user without avatar - expect 400 with refund OR insufficient balance.
        r = session.post(f"{API}/cosmetics/purchase", json={
            "user_id": fresh_user, "item_id": "spotlight_24h"
        })
        # Either insufficient balance OR no-avatar error
        assert r.status_code == 400, r.text

    def test_spotlight_list(self, session):
        r = session.get(f"{API}/cosmetics/spotlight")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "featured" in data or isinstance(data, list)


# ============ FACTORY / WORKBENCH ============
class TestFactoryWorker:
    def test_available_tasks(self, session):
        r = session.get(f"{API}/data-api/factory/tasks", params={"status": "available"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) or "tasks" in data

    def test_worker_tasks_filtered(self, session):
        r = session.get(f"{API}/data-api/factory/tasks", params={"worker_id": EXISTING_USER, "status": "all"})
        assert r.status_code == 200, r.text

    def test_scheduler_status_has_last_repeat_at(self, session):
        r = session.get(f"{API}/data-api/scheduler/status")
        assert r.status_code == 200, r.text
        data = r.json()
        # Should expose auto_repeat templates with last_repeat_at
        # Accept any shape that contains 'templates' or 'auto_repeat' list
        body = str(data).lower()
        assert "last_repeat_at" in body or "auto_repeat" in body, f"payload: {data}"


# ============ PROFILE CUSTOMIZATION ============
class TestProfileCustomization:
    def test_customization_excludes_old_fields(self, session):
        r = session.get(f"{API}/profile/customization/{EXISTING_USER}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "profile_picture" not in data, f"old profile_picture still present: {data}"
        assert "profile_logo" not in data, f"old profile_logo still present: {data}"
        assert "pixel_avatar_url" in data, f"missing pixel_avatar_url: {list(data.keys())}"

    def test_customization_options_has_premium_chat_colors(self, session):
        r = session.get(f"{API}/profile/customization-options")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "premium_chat_colors" in data, f"keys: {list(data.keys())}"
        assert isinstance(data["premium_chat_colors"], dict)
        assert len(data["premium_chat_colors"]) >= 1


# ============ FACTORY E2E CLAIM + SUBMIT WITH BOOST ============
class TestFactoryClaimSubmit:
    def test_claim_submit_with_boost_multiplier(self, session):
        # Get an available task
        r = session.get(f"{API}/data-api/factory/tasks", params={"status": "available"})
        assert r.status_code == 200
        body = r.json()
        tasks = body if isinstance(body, list) else body.get("tasks", [])
        if not tasks:
            pytest.skip("No available tasks")
        # Pick a sentiment task for easy submission
        sentiment = [t for t in tasks if "sentiment" in (t.get("title", "").lower())]
        task = sentiment[0] if sentiment else tasks[0]
        instance_id = task.get("instance_id") or task.get("id")
        base_reward = task.get("reward_ve", 0)

        # Claim
        c = session.post(f"{API}/data-api/factory/task/{instance_id}/claim",
                         params={"worker_id": EXISTING_USER})
        assert c.status_code == 200, c.text

        # Submit a valid output
        out_spec = task.get("output_spec", {})
        required = out_spec.get("required_fields", [])
        output = {f: "positive" if f == "sentiment" else "test_value" for f in required}
        s = session.post(f"{API}/data-api/factory/task/{instance_id}/submit",
                         json={"worker_id": EXISTING_USER, "output": output})
        assert s.status_code == 200, s.text
        sub = s.json()
        # If user has active task_reward boost, boost_applied should be True and reward = 1.5 * base
        if sub.get("boost_applied"):
            assert sub.get("reward_ve") == pytest.approx(base_reward * 1.5, abs=0.001), sub
        # Either way the submission must have succeeded
        assert sub.get("status") in ("validated", "submitted", "completed") or sub.get("validated") is True

    def test_submit_invalid_output_fails_validation(self, session):
        # Get available
        r = session.get(f"{API}/data-api/factory/tasks", params={"status": "available"})
        tasks = r.json() if isinstance(r.json(), list) else r.json().get("tasks", [])
        if not tasks:
            pytest.skip("No tasks")
        task = tasks[0]
        instance_id = task.get("instance_id") or task.get("id")
        c = session.post(f"{API}/data-api/factory/task/{instance_id}/claim",
                        params={"worker_id": EXISTING_USER})
        if c.status_code != 200:
            pytest.skip(f"claim failed: {c.text}")
        # Submit empty output (should fail not_empty validation)
        s = session.post(f"{API}/data-api/factory/task/{instance_id}/submit",
                       json={"worker_id": EXISTING_USER, "output": {}})
        # Should fail validation - either 400 or status reflecting failure
        if s.status_code == 200:
            body = s.json()
            assert body.get("validated") is False or body.get("status") in ("rejected", "failed", "invalid"), body
        else:
            assert s.status_code in (400, 422), s.text
