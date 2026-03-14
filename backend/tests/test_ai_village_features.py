"""
Backend API Tests for AI Village: The Echoes
Testing: ObjectId serialization fixes, AI professions, Villagers, World/Land system

Endpoints covered:
- POST /api/build (ObjectId fix)
- POST /api/trade/offer (ObjectId fix)
- GET /api/professions
- GET /api/villagers
- POST /api/villagers/{id}/work
- POST /api/villagers/trade
- GET /api/world/seedling
- GET /api/world/lands
- GET /api/world/houses
- POST /api/world/build-house
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestBuildEndpointObjectIdFix:
    """Test /api/build endpoint - ObjectId serialization fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test user for building tests"""
        self.test_username = f"test_builder_{uuid.uuid4().hex[:8]}"
        # Create user
        response = requests.post(f"{BASE_URL}/api/users", json={
            "username": self.test_username,
            "display_name": "Test Builder"
        })
        if response.status_code == 200:
            self.user = response.json()
            self.user_id = self.user["id"]
        else:
            pytest.skip("Could not create test user")
        yield
        # No cleanup needed for MongoDB

    def test_build_torch_returns_valid_json(self):
        """Build a torch - should return valid JSON without ObjectId errors"""
        # Torch requires 2 wood, user starts with 10 wood
        response = requests.post(f"{BASE_URL}/api/build", json={
            "schematic_id": "torch",
            "user_id": self.user_id,
            "location_id": "village_square",
            "position_x": 50.0,
            "position_y": 50.0
        })
        
        print(f"Build response status: {response.status_code}")
        
        # Critical: This should NOT be 500 (ObjectId serialization error)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "building" in data
        assert "status" in data
        assert data["status"] == "success"
        assert "id" in data["building"]
        print(f"Successfully built torch with id: {data['building']['id']}")

    def test_build_insufficient_contribution(self):
        """Build should fail when lacking contribution points"""
        # Wall requires 50 contribution points, new user starts with 0
        response = requests.post(f"{BASE_URL}/api/build", json={
            "schematic_id": "wall",
            "user_id": self.user_id,
            "location_id": "village_square",
            "position_x": 50.0,
            "position_y": 50.0
        })
        
        # Wall requires 50 contribution, new user has 0
        assert response.status_code == 403
        data = response.json()
        assert "contribution" in data.get("detail", "").lower()


class TestTradeOfferObjectIdFix:
    """Test /api/trade/offer endpoint - ObjectId serialization fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test user for trading tests"""
        self.test_username = f"test_trader_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={
            "username": self.test_username,
            "display_name": "Test Trader"
        })
        if response.status_code == 200:
            self.user = response.json()
            self.user_id = self.user["id"]
        else:
            pytest.skip("Could not create test user")
        yield

    def test_create_trade_offer_returns_valid_json(self):
        """Create trade offer - should return valid JSON without ObjectId errors"""
        # User starts with 10 wood, 5 stone
        response = requests.post(f"{BASE_URL}/api/trade/offer", json={
            "seller_id": self.user_id,
            "offering": {"wood": 2},
            "requesting": {"stone": 1}
        })
        
        print(f"Trade offer response status: {response.status_code}")
        
        # Critical: This should NOT be 500 (ObjectId serialization error)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "seller_id" in data
        assert data["seller_id"] == self.user_id
        assert data["status"] == "open"
        print(f"Successfully created trade offer with id: {data['id']}")

    def test_create_trade_insufficient_materials(self):
        """Trade offer should fail when lacking materials"""
        response = requests.post(f"{BASE_URL}/api/trade/offer", json={
            "seller_id": self.user_id,
            "offering": {"iron": 100},  # User starts with 0 iron
            "requesting": {"wood": 1}
        })
        
        assert response.status_code == 400


class TestProfessionsAPI:
    """Test AI Professions endpoints"""
    
    def test_get_all_professions(self):
        """GET /api/professions - returns all AI professions"""
        response = requests.get(f"{BASE_URL}/api/professions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "professions" in data
        assert "tiers" in data
        
        professions = data["professions"]
        # Check that expected professions exist
        expected_professions = ["chef", "miner", "court_mage", "serf", "baron", 
                               "swordsman", "archer", "butcher", "guildmaster"]
        for prof in expected_professions:
            assert prof in professions, f"Missing profession: {prof}"
            assert "tier" in professions[prof]
            assert "abilities" in professions[prof]
            assert "daily_output" in professions[prof]
        
        # Check profession count (should be 18 based on server.py)
        assert len(professions) >= 18, f"Expected 18 professions, got {len(professions)}"
        print(f"Found {len(professions)} professions: {list(professions.keys())}")

    def test_get_specific_profession(self):
        """GET /api/professions/{profession_id} - get profession details"""
        response = requests.get(f"{BASE_URL}/api/professions/blacksmith")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Blacksmith"
        assert data["tier"] == "craftsman"
        assert "forge" in data["abilities"]
        assert "profession_id" in data
        assert "tier_info" in data

    def test_get_invalid_profession(self):
        """GET /api/professions/{invalid} - returns 404"""
        response = requests.get(f"{BASE_URL}/api/professions/invalid_profession")
        assert response.status_code == 404


class TestVillagersAPI:
    """Test AI Villagers endpoints"""
    
    def test_get_all_villagers(self):
        """GET /api/villagers - returns all AI villagers with professions"""
        response = requests.get(f"{BASE_URL}/api/villagers")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have starter villagers (12 initialized in startup)
        assert len(data) >= 1, "No villagers found"
        
        # Check villager structure
        if len(data) > 0:
            villager = data[0]
            assert "id" in villager
            assert "name" in villager
            assert "profession" in villager
            assert "tier" in villager
            assert "profession_details" in villager
            print(f"Found {len(data)} villagers")
            for v in data[:3]:  # Print first 3
                print(f"  - {v['name']} ({v['profession']})")

    def test_get_villagers_by_location(self):
        """GET /api/villagers/location/{location_id} - filter villagers by location"""
        response = requests.get(f"{BASE_URL}/api/villagers/location/village_square")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned villagers should be at village_square
        for v in data:
            assert v["current_location"] == "village_square"


class TestVillagerWork:
    """Test villager work functionality"""
    
    def test_villager_daily_work(self):
        """POST /api/villagers/{id}/work - villager performs daily work"""
        # First get a villager
        response = requests.get(f"{BASE_URL}/api/villagers")
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No villagers available")
        
        villagers = response.json()
        
        # Find a villager who hasn't worked today
        villager = None
        for v in villagers:
            if not v.get("daily_work_done"):
                villager = v
                break
        
        if not villager:
            # Reset daily work for testing
            reset_response = requests.post(f"{BASE_URL}/api/villagers/reset-daily")
            if reset_response.status_code == 200:
                response = requests.get(f"{BASE_URL}/api/villagers")
                villagers = response.json()
                if len(villagers) > 0:
                    villager = villagers[0]
        
        if not villager:
            pytest.skip("No available villager for work test")
        
        villager_id = villager["id"]
        
        # Perform work
        work_response = requests.post(f"{BASE_URL}/api/villagers/{villager_id}/work")
        
        assert work_response.status_code == 200, f"Work failed: {work_response.text}"
        data = work_response.json()
        
        assert data["status"] == "success"
        assert "output" in data
        assert "xp_gained" in data
        assert "villager_name" in data
        print(f"Villager {data['villager_name']} worked: {data['output']}")

    def test_villager_cannot_work_twice(self):
        """POST /api/villagers/{id}/work - cannot work twice in a day"""
        # Get a villager who has worked
        response = requests.get(f"{BASE_URL}/api/villagers")
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No villagers available")
        
        villagers = response.json()
        worked_villager = None
        for v in villagers:
            if v.get("daily_work_done"):
                worked_villager = v
                break
        
        if not worked_villager:
            pytest.skip("No villager has worked yet")
        
        # Try to work again
        response = requests.post(f"{BASE_URL}/api/villagers/{worked_villager['id']}/work")
        assert response.status_code == 400
        assert "already worked" in response.json().get("detail", "").lower()


class TestVillagerTrade:
    """Test AI villager trading functionality"""
    
    def test_villager_trade_between_villagers(self):
        """POST /api/villagers/trade - AI villagers can trade with each other"""
        # Get villagers who can trade
        response = requests.get(f"{BASE_URL}/api/villagers")
        if response.status_code != 200:
            pytest.skip("Cannot fetch villagers")
        
        villagers = response.json()
        
        # Find two villagers who can trade and have inventory
        traders = []
        for v in villagers:
            prof_details = v.get("profession_details", {})
            if prof_details.get("can_trade", False):
                traders.append(v)
                if len(traders) >= 2:
                    break
        
        if len(traders) < 2:
            pytest.skip("Not enough trading villagers available")
        
        villager1, villager2 = traders[0], traders[1]
        
        # Attempt trade (may fail due to inventory, but should not be 500)
        trade_response = requests.post(f"{BASE_URL}/api/villagers/trade", json={
            "villager_id": villager1["id"],
            "target_id": villager2["id"],
            "target_type": "villager",
            "offering": {"gold": 1},
            "requesting": {"gold": 1}
        })
        
        # Should be 200 (success) or 400 (insufficient resources), NOT 500
        assert trade_response.status_code in [200, 400], f"Unexpected status: {trade_response.status_code}"
        print(f"Trade response: {trade_response.status_code} - {trade_response.json()}")


class TestWorldSeedlingAPI:
    """Test World/Land System endpoints"""
    
    def test_get_world_seedling(self):
        """GET /api/world/seedling - returns origin village data"""
        response = requests.get(f"{BASE_URL}/api/world/seedling")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "origin_village" in data
        origin = data["origin_village"]
        assert origin["name"] == "The First Echo"
        assert origin["discovered"] == True
        assert "locations" in origin
        print(f"World seedling: {origin['name']} with {len(origin['locations'])} locations")

    def test_get_discoverable_lands(self):
        """GET /api/world/lands - returns all discoverable lands"""
        response = requests.get(f"{BASE_URL}/api/world/lands")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected lands exist (5 based on server.py)
        expected_lands = ["eastern_plains", "northern_mountains", "western_forest", 
                         "southern_coast", "underground_realm"]
        for land in expected_lands:
            assert land in data, f"Missing land: {land}"
            assert "name" in data[land]
            assert "travel_distance" in data[land] or "required_building" in data[land]
            assert "new_locations" in data[land]
        
        print(f"Found {len(data)} discoverable lands: {list(data.keys())}")

    def test_get_house_schematics(self):
        """GET /api/world/houses - returns house building options"""
        response = requests.get(f"{BASE_URL}/api/world/houses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected house types (5 based on server.py)
        expected_houses = ["campsite", "cottage", "house", "manor", "guild_hall"]
        for house in expected_houses:
            assert house in data, f"Missing house type: {house}"
            assert "materials" in data[house]
            assert "capacity" in data[house]
            assert "land_claim" in data[house]
        
        print(f"Found {len(data)} house types: {list(data.keys())}")


class TestBuildHouse:
    """Test house building functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test user for house building"""
        self.test_username = f"test_homeowner_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={
            "username": self.test_username,
            "display_name": "Test Homeowner"
        })
        if response.status_code == 200:
            self.user = response.json()
            self.user_id = self.user["id"]
        else:
            pytest.skip("Could not create test user")
        yield

    def test_build_campsite_in_origin_village(self):
        """POST /api/world/build-house - build campsite in origin village"""
        # Campsite requires 5 wood, user starts with 10
        response = requests.post(
            f"{BASE_URL}/api/world/build-house",
            params={
                "user_id": self.user_id,
                "house_type": "campsite",
                "land_id": "origin_village",
                "x": 100.0,
                "y": 200.0
            }
        )
        
        print(f"Build house response: {response.status_code}")
        
        assert response.status_code == 200, f"Build house failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "success"
        assert "house" in data
        assert data["house"]["house_type"] == "campsite"
        assert data["house"]["owner_id"] == self.user_id
        assert "contribution_gained" in data
        print(f"Built house: {data['house']}")

    def test_build_house_insufficient_materials(self):
        """POST /api/world/build-house - fails with insufficient materials"""
        # Manor requires 50 wood, 60 stone, etc - way more than starting resources
        response = requests.post(
            f"{BASE_URL}/api/world/build-house",
            params={
                "user_id": self.user_id,
                "house_type": "manor",
                "land_id": "origin_village",
                "x": 100.0,
                "y": 200.0
            }
        )
        
        assert response.status_code == 400
        assert "Not enough" in response.json().get("detail", "")

    def test_build_house_in_undiscovered_land(self):
        """POST /api/world/build-house - fails in undiscovered land"""
        response = requests.post(
            f"{BASE_URL}/api/world/build-house",
            params={
                "user_id": self.user_id,
                "house_type": "campsite",
                "land_id": "eastern_plains",  # Not discovered by new user
                "x": 100.0,
                "y": 200.0
            }
        )
        
        assert response.status_code == 400
        assert "haven't discovered" in response.json().get("detail", "")


class TestHealthAndBasicEndpoints:
    """Basic sanity checks for API health"""
    
    def test_api_root(self):
        """GET /api/ - API is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        assert "Welcome" in response.json().get("message", "")
    
    def test_materials_endpoint(self):
        """GET /api/materials - returns building materials"""
        response = requests.get(f"{BASE_URL}/api/materials")
        assert response.status_code == 200
        data = response.json()
        assert "wood" in data
        assert "stone" in data
    
    def test_schematics_endpoint(self):
        """GET /api/schematics - returns building schematics"""
        response = requests.get(f"{BASE_URL}/api/schematics")
        assert response.status_code == 200
        data = response.json()
        assert "torch" in data
        assert "wall" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
