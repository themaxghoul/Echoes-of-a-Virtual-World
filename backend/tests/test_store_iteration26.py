# Store System Tests - Iteration 26
# Tests for Currency conversion, Compute subscriptions, Civilization structures

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com')

class TestStoreStatus:
    """Store status endpoint tests"""
    
    def test_store_status_returns_enabled(self):
        """GET /api/store/status - Store should be enabled"""
        response = requests.get(f"{BASE_URL}/api/store/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["enabled"] == True
        assert "stripe_configured" in data
        assert data["stripe_configured"] == True
        assert data["exchange_rate"] == 1.0
        assert data["currency_symbol"] == "VE$"
        print(f"Store status: enabled={data['enabled']}, stripe_configured={data['stripe_configured']}")


class TestCurrencyPresets:
    """Currency preset purchase tests"""
    
    def test_presets_returns_5_packages(self):
        """GET /api/store/presets - Should return 5 preset packages"""
        response = requests.get(f"{BASE_URL}/api/store/presets")
        assert response.status_code == 200
        
        data = response.json()
        assert "presets" in data
        presets = data["presets"]
        assert len(presets) == 5
        print(f"Found {len(presets)} preset packages")
    
    def test_presets_have_correct_structure(self):
        """Each preset should have required fields"""
        response = requests.get(f"{BASE_URL}/api/store/presets")
        data = response.json()
        
        required_fields = ["id", "amount_usd", "ve_received", "bonus", "label", "popular"]
        for preset in data["presets"]:
            for field in required_fields:
                assert field in preset, f"Missing field: {field} in preset {preset.get('id')}"
        print("All presets have correct structure")
    
    def test_presets_have_bonus_scaling(self):
        """Higher packages should have higher bonus percentages"""
        response = requests.get(f"{BASE_URL}/api/store/presets")
        data = response.json()
        
        presets = data["presets"]
        # Verify bonus increases with price
        expected_bonuses = [0, 5, 10, 15, 20]  # starter, adventurer, explorer, champion, legend
        for i, preset in enumerate(presets):
            assert preset["bonus"] == expected_bonuses[i], f"Preset {preset['id']} has wrong bonus"
        print("Bonus scaling verified: 0%, 5%, 10%, 15%, 20%")
    
    def test_explorer_pack_is_popular(self):
        """Explorer pack should be marked as popular"""
        response = requests.get(f"{BASE_URL}/api/store/presets")
        data = response.json()
        
        explorer = next((p for p in data["presets"] if p["id"] == "explorer"), None)
        assert explorer is not None
        assert explorer["popular"] == True
        print("Explorer pack correctly marked as popular")


class TestComputeSubscriptions:
    """Compute power subscription tests"""
    
    def test_subscriptions_returns_6_tiers(self):
        """GET /api/store/compute-subscriptions - Should return 6 tiers"""
        response = requests.get(f"{BASE_URL}/api/store/compute-subscriptions")
        assert response.status_code == 200
        
        data = response.json()
        assert "subscriptions" in data
        subs = data["subscriptions"]
        assert len(subs) == 6
        print(f"Found {len(subs)} subscription tiers")
    
    def test_subscriptions_have_exponential_scaling(self):
        """Compute units should scale exponentially"""
        response = requests.get(f"{BASE_URL}/api/store/compute-subscriptions")
        data = response.json()
        
        subs = data["subscriptions"]
        # Expected compute units: 100, 250, 600, 1500, 4000, 12000
        expected_units = {
            "spark": 100,
            "flame": 250,
            "inferno": 600,
            "nova": 1500,
            "supernova": 4000,
            "cosmic": 12000
        }
        
        for tier_id, expected in expected_units.items():
            assert subs[tier_id]["compute_units"] == expected, f"Tier {tier_id} has wrong compute units"
        print("Exponential scaling verified: 100 → 250 → 600 → 1500 → 4000 → 12000")
    
    def test_subscriptions_have_ai_slots(self):
        """Each tier should have AI program slots"""
        response = requests.get(f"{BASE_URL}/api/store/compute-subscriptions")
        data = response.json()
        
        subs = data["subscriptions"]
        expected_slots = {
            "spark": 1,
            "flame": 2,
            "inferno": 4,
            "nova": 8,
            "supernova": 16,
            "cosmic": 32
        }
        
        for tier_id, expected in expected_slots.items():
            assert subs[tier_id]["ai_program_slots"] == expected
        print("AI slots verified: 1 → 2 → 4 → 8 → 16 → 32")
    
    def test_subscriptions_have_multipliers(self):
        """Each tier should have power multiplier"""
        response = requests.get(f"{BASE_URL}/api/store/compute-subscriptions")
        data = response.json()
        
        subs = data["subscriptions"]
        expected_multipliers = {
            "spark": 1.0,
            "flame": 2.5,
            "inferno": 6.0,
            "nova": 15.0,
            "supernova": 40.0,
            "cosmic": 120.0
        }
        
        for tier_id, expected in expected_multipliers.items():
            assert subs[tier_id]["multiplier"] == expected
        print("Multipliers verified: 1x → 2.5x → 6x → 15x → 40x → 120x")


class TestCivilizationStructures:
    """Civilization structures tests"""
    
    def test_structures_returns_4_categories(self):
        """GET /api/store/structures - Should return 4 categories"""
        response = requests.get(f"{BASE_URL}/api/store/structures")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data
        categories = data["categories"]
        assert len(categories) == 4
        assert "essential" in categories
        assert "defense" in categories
        assert "production" in categories
        assert "community" in categories
        print(f"Found {len(categories)} categories: {categories}")
    
    def test_structures_grouped_by_category(self):
        """Structures should be grouped by category"""
        response = requests.get(f"{BASE_URL}/api/store/structures")
        data = response.json()
        
        by_category = data["by_category"]
        assert "essential" in by_category
        assert "defense" in by_category
        assert "production" in by_category
        assert "community" in by_category
        
        # Verify counts
        assert len(by_category["essential"]) == 3  # campfire, shelter, well
        assert len(by_category["defense"]) == 6    # palisade, wooden_gate, stone_wall, iron_gate, watchtower, guard_post
        assert len(by_category["production"]) == 3 # farm, workshop, forge
        assert len(by_category["community"]) == 3  # gathering_hall, tavern, temple
        print(f"Structure counts: essential={len(by_category['essential'])}, defense={len(by_category['defense'])}, production={len(by_category['production'])}, community={len(by_category['community'])}")
    
    def test_structures_have_dual_pricing(self):
        """Each structure should have VE$ and USD pricing"""
        response = requests.get(f"{BASE_URL}/api/store/structures")
        data = response.json()
        
        for struct_id, struct in data["structures"].items():
            assert "cost_ve" in struct, f"Missing cost_ve in {struct_id}"
            assert "cost_usd" in struct, f"Missing cost_usd in {struct_id}"
            # VE$ and USD should be equal (1:1 conversion)
            assert struct["cost_ve"] == struct["cost_usd"], f"Pricing mismatch in {struct_id}"
        print("All structures have dual pricing (VE$ = USD)")
    
    def test_defense_structures_have_defense_stat(self):
        """Defense structures should have defense stat > 0"""
        response = requests.get(f"{BASE_URL}/api/store/structures")
        data = response.json()
        
        defense_structures = data["by_category"]["defense"]
        for struct in defense_structures:
            assert struct["defense"] > 0, f"Defense structure {struct['id']} has no defense"
        print("All defense structures have defense stat > 0")
    
    def test_philosophy_mentions_gates_defense(self):
        """Philosophy should mention gates defense concept"""
        response = requests.get(f"{BASE_URL}/api/store/structures")
        data = response.json()
        
        assert "philosophy" in data
        philosophy = data["philosophy"].lower()
        assert "gates" in philosophy or "guard" in philosophy
        print(f"Philosophy: {data['philosophy']}")


class TestStructurePurchaseVE:
    """Structure purchase with VE$ tests"""
    
    def test_purchase_structure_insufficient_balance(self):
        """POST /api/store/purchase-structure - Should fail with insufficient balance"""
        response = requests.post(f"{BASE_URL}/api/store/purchase-structure", json={
            "user_id": "test_user_no_balance",
            "structure_id": "campfire",
            "payment_method": "ve"
        })
        
        # Should return 400 for insufficient balance
        assert response.status_code == 400
        data = response.json()
        assert "Insufficient" in data.get("detail", "")
        print("Insufficient balance check working")
    
    def test_purchase_structure_invalid_structure(self):
        """POST /api/store/purchase-structure - Should fail with invalid structure"""
        response = requests.post(f"{BASE_URL}/api/store/purchase-structure", json={
            "user_id": "test_user",
            "structure_id": "invalid_structure_xyz",
            "payment_method": "ve"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "Unknown structure" in data.get("detail", "")
        print("Invalid structure check working")


class TestUserSubscription:
    """User subscription status tests"""
    
    def test_user_subscription_no_active(self):
        """GET /api/store/user/{user_id}/subscription - Should return inactive for new user"""
        response = requests.get(f"{BASE_URL}/api/store/user/test_new_user_xyz/subscription")
        assert response.status_code == 200
        
        data = response.json()
        assert data["active"] == False
        assert data["tier"] is None
        assert data["compute_units"] == 0
        print("New user has no active subscription")


class TestOwnedStructures:
    """Owned structures tests"""
    
    def test_owned_structures_empty_for_new_user(self):
        """GET /api/store/my-structures/{user_id} - Should return empty for new user"""
        response = requests.get(f"{BASE_URL}/api/store/my-structures/test_new_user_xyz")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 0
        assert len(data["owned"]) == 0
        print("New user has no owned structures")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
