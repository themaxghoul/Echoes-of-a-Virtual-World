"""
Building System API Tests - Iteration 16
Tests for grid-based building placement, movement, and demolition
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user with existing wallet
TEST_USER_ID = "test_user_456"
TEST_WORLD_ID = "main-story-realm"
TEST_REGION_ID = "hollow_square"


class TestBuildingCatalog:
    """Test building catalog endpoint"""
    
    def test_get_catalog_returns_5_categories(self):
        """Verify catalog has all 5 building categories"""
        response = requests.get(f"{BASE_URL}/api/building/catalog")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data
        categories = data["categories"]
        
        # Verify all 5 categories exist
        expected_categories = ["basic_structures", "functional_buildings", "decorative", "paths", "special"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        assert len(categories) == 5, f"Expected 5 categories, got {len(categories)}"
        
    def test_catalog_has_grid_settings(self):
        """Verify catalog includes grid size and cell size"""
        response = requests.get(f"{BASE_URL}/api/building/catalog")
        assert response.status_code == 200
        
        data = response.json()
        assert data["grid_size"] == 100, "Grid size should be 100x100"
        assert data["cell_size"] == 32, "Cell size should be 32 pixels"
        
    def test_catalog_building_items_have_required_fields(self):
        """Verify building items have name, size, cost, materials"""
        response = requests.get(f"{BASE_URL}/api/building/catalog")
        assert response.status_code == 200
        
        data = response.json()
        categories = data["categories"]
        
        # Check a sample building from each category
        sample_buildings = [
            ("basic_structures", "wooden_house"),
            ("functional_buildings", "forge"),
            ("decorative", "flower_bed"),
            ("paths", "dirt_path"),
            ("special", "portal")
        ]
        
        for cat_id, building_id in sample_buildings:
            building = categories[cat_id]["items"][building_id]
            assert "name" in building, f"{building_id} missing name"
            assert "size" in building, f"{building_id} missing size"
            assert "cost" in building, f"{building_id} missing cost"
            assert "materials" in building, f"{building_id} missing materials"
            assert len(building["size"]) == 2, f"{building_id} size should be [w, h]"


class TestBuildingGrid:
    """Test building grid endpoint"""
    
    def test_get_grid_returns_100x100(self):
        """Verify grid is 100x100"""
        response = requests.get(f"{BASE_URL}/api/building/grid/{TEST_WORLD_ID}/{TEST_REGION_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "grid" in data
        assert "grid_size" in data
        assert data["grid_size"] == 100
        
        grid = data["grid"]
        assert grid["size"] == [100, 100], "Grid size should be [100, 100]"
        
    def test_grid_shows_existing_buildings(self):
        """Verify grid shows existing Flower Bed at position (5,5)"""
        response = requests.get(f"{BASE_URL}/api/building/grid/{TEST_WORLD_ID}/{TEST_REGION_ID}")
        assert response.status_code == 200
        
        data = response.json()
        buildings = data["buildings"]
        
        # Find the flower bed
        flower_bed = None
        for b in buildings:
            if b["building_type"] == "flower_bed" and b["position"] == [5, 5]:
                flower_bed = b
                break
        
        assert flower_bed is not None, "Flower Bed at (5,5) not found"
        assert flower_bed["owner_id"] == TEST_USER_ID
        assert flower_bed["category"] == "decorative"
        
    def test_grid_creates_new_region_if_not_exists(self):
        """Verify new grid is created for non-existent region"""
        new_region = f"test_region_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/building/grid/{TEST_WORLD_ID}/{new_region}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["grid"]["region_id"] == new_region
        assert data["buildings"] == []


class TestBuildingPlacement:
    """Test building placement API"""
    
    def test_place_building_with_sufficient_balance(self):
        """Test placing a building when user has enough VE$"""
        # First check user balance
        wallet_res = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{TEST_USER_ID}")
        initial_balance = wallet_res.json().get("balance_ve", 0)
        
        # Place a dirt path (cost: 2 VE$)
        unique_pos = [50 + (hash(str(uuid.uuid4())) % 20), 50 + (hash(str(uuid.uuid4())) % 20)]
        
        response = requests.post(
            f"{BASE_URL}/api/building/place?owner_id={TEST_USER_ID}&owner_type=player",
            json={
                "building_type": "dirt_path",
                "position": unique_pos,
                "rotation": 0,
                "world_id": TEST_WORLD_ID,
                "region_id": TEST_REGION_ID
            }
        )
        
        if initial_balance >= 2:
            assert response.status_code == 200
            data = response.json()
            assert data["placed"] == True
            assert "building_id" in data
            assert data["cost_paid"] == 2
            
            # Verify balance was deducted
            wallet_res = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{TEST_USER_ID}")
            new_balance = wallet_res.json().get("balance_ve", 0)
            assert new_balance < initial_balance, "Balance should be deducted"
            
            # Cleanup - demolish the building
            requests.delete(f"{BASE_URL}/api/building/{data['building_id']}?owner_id={TEST_USER_ID}")
        else:
            assert response.status_code == 400
            assert "Insufficient funds" in response.json().get("detail", "")
    
    def test_place_building_insufficient_balance(self):
        """Test placing expensive building with insufficient balance"""
        # Try to place a portal (cost: 1000 VE$)
        response = requests.post(
            f"{BASE_URL}/api/building/place?owner_id={TEST_USER_ID}&owner_type=player",
            json={
                "building_type": "portal",
                "position": [80, 80],
                "rotation": 0,
                "world_id": TEST_WORLD_ID,
                "region_id": TEST_REGION_ID
            }
        )
        
        assert response.status_code == 400
        assert "Insufficient funds" in response.json().get("detail", "")
        
    def test_place_building_collision_detection(self):
        """Test that collision detection prevents overlapping buildings"""
        # Try to place at position (5,5) where Flower Bed exists
        response = requests.post(
            f"{BASE_URL}/api/building/place?owner_id={TEST_USER_ID}&owner_type=player",
            json={
                "building_type": "bench",
                "position": [5, 5],
                "rotation": 0,
                "world_id": TEST_WORLD_ID,
                "region_id": TEST_REGION_ID
            }
        )
        
        assert response.status_code == 400
        assert "Collision" in response.json().get("detail", "")
        
    def test_place_building_out_of_bounds(self):
        """Test that out of bounds placement is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/building/place?owner_id={TEST_USER_ID}&owner_type=player",
            json={
                "building_type": "wooden_house",  # 3x3 building
                "position": [99, 99],  # Would extend beyond 100x100 grid
                "rotation": 0,
                "world_id": TEST_WORLD_ID,
                "region_id": TEST_REGION_ID
            }
        )
        
        assert response.status_code == 400
        assert "out of bounds" in response.json().get("detail", "").lower()
        
    def test_place_unknown_building_type(self):
        """Test that unknown building type is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/building/place?owner_id={TEST_USER_ID}&owner_type=player",
            json={
                "building_type": "unknown_building_xyz",
                "position": [10, 10],
                "rotation": 0,
                "world_id": TEST_WORLD_ID,
                "region_id": TEST_REGION_ID
            }
        )
        
        assert response.status_code == 400
        assert "Unknown building type" in response.json().get("detail", "")


class TestBuildingMove:
    """Test building move API"""
    
    def test_move_building_success(self):
        """Test moving a building to a new valid position"""
        # Get the existing flower bed
        grid_res = requests.get(f"{BASE_URL}/api/building/grid/{TEST_WORLD_ID}/{TEST_REGION_ID}")
        buildings = grid_res.json()["buildings"]
        
        flower_bed = None
        for b in buildings:
            if b["building_type"] == "flower_bed" and b["owner_id"] == TEST_USER_ID:
                flower_bed = b
                break
        
        if not flower_bed:
            pytest.skip("No flower bed found to test move")
        
        original_pos = flower_bed["position"]
        new_pos = [6, 6]  # Move to adjacent position
        
        response = requests.post(
            f"{BASE_URL}/api/building/move?owner_id={TEST_USER_ID}",
            json={
                "building_id": flower_bed["building_id"],
                "new_position": new_pos
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["moved"] == True
        assert data["new_position"] == new_pos
        
        # Move it back
        requests.post(
            f"{BASE_URL}/api/building/move?owner_id={TEST_USER_ID}",
            json={
                "building_id": flower_bed["building_id"],
                "new_position": original_pos
            }
        )
        
    def test_move_building_not_owner(self):
        """Test that non-owner cannot move building"""
        # Get the existing flower bed
        grid_res = requests.get(f"{BASE_URL}/api/building/grid/{TEST_WORLD_ID}/{TEST_REGION_ID}")
        buildings = grid_res.json()["buildings"]
        
        flower_bed = None
        for b in buildings:
            if b["building_type"] == "flower_bed":
                flower_bed = b
                break
        
        if not flower_bed:
            pytest.skip("No flower bed found to test")
        
        response = requests.post(
            f"{BASE_URL}/api/building/move?owner_id=different_user_123",
            json={
                "building_id": flower_bed["building_id"],
                "new_position": [10, 10]
            }
        )
        
        assert response.status_code == 403
        assert "Not your building" in response.json().get("detail", "")
        
    def test_move_building_not_found(self):
        """Test moving non-existent building"""
        response = requests.post(
            f"{BASE_URL}/api/building/move?owner_id={TEST_USER_ID}",
            json={
                "building_id": "non-existent-building-id",
                "new_position": [10, 10]
            }
        )
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()


class TestBuildingDemolish:
    """Test building demolish API"""
    
    def test_demolish_returns_50_percent_refund(self):
        """Test that demolishing returns 50% of building cost"""
        # First place a building to demolish
        wallet_res = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{TEST_USER_ID}")
        initial_balance = wallet_res.json().get("balance_ve", 0)
        
        if initial_balance < 5:
            pytest.skip("Insufficient balance to test demolish")
        
        # Place a flower bed (cost: 5 VE$)
        place_res = requests.post(
            f"{BASE_URL}/api/building/place?owner_id={TEST_USER_ID}&owner_type=player",
            json={
                "building_type": "flower_bed",
                "position": [70, 70],
                "rotation": 0,
                "world_id": TEST_WORLD_ID,
                "region_id": TEST_REGION_ID
            }
        )
        
        if place_res.status_code != 200:
            pytest.skip("Could not place building for demolish test")
        
        building_id = place_res.json()["building_id"]
        
        # Get balance after placement
        wallet_res = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{TEST_USER_ID}")
        balance_after_place = wallet_res.json().get("balance_ve", 0)
        
        # Demolish the building
        demolish_res = requests.delete(f"{BASE_URL}/api/building/{building_id}?owner_id={TEST_USER_ID}")
        
        assert demolish_res.status_code == 200
        data = demolish_res.json()
        assert data["demolished"] == True
        assert data["refund"] == 2  # 50% of 5 VE$ = 2 (integer)
        
        # Verify refund was added
        wallet_res = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{TEST_USER_ID}")
        balance_after_demolish = wallet_res.json().get("balance_ve", 0)
        assert balance_after_demolish > balance_after_place, "Balance should increase after refund"
        
    def test_demolish_not_owner(self):
        """Test that non-owner cannot demolish building"""
        # Get the existing flower bed
        grid_res = requests.get(f"{BASE_URL}/api/building/grid/{TEST_WORLD_ID}/{TEST_REGION_ID}")
        buildings = grid_res.json()["buildings"]
        
        flower_bed = None
        for b in buildings:
            if b["building_type"] == "flower_bed" and b["owner_id"] == TEST_USER_ID:
                flower_bed = b
                break
        
        if not flower_bed:
            pytest.skip("No flower bed found to test")
        
        response = requests.delete(f"{BASE_URL}/api/building/{flower_bed['building_id']}?owner_id=different_user_123")
        
        assert response.status_code == 403
        assert "Not your building" in response.json().get("detail", "")
        
    def test_demolish_not_found(self):
        """Test demolishing non-existent building"""
        response = requests.delete(f"{BASE_URL}/api/building/non-existent-id?owner_id={TEST_USER_ID}")
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()


class TestOwnedBuildings:
    """Test owned buildings endpoint"""
    
    def test_get_owned_buildings(self):
        """Test getting all buildings owned by a user"""
        response = requests.get(f"{BASE_URL}/api/building/owned/{TEST_USER_ID}?world_id={TEST_WORLD_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "buildings" in data
        assert "count" in data
        assert isinstance(data["buildings"], list)
        
        # Verify all returned buildings belong to the user
        for building in data["buildings"]:
            assert building["owner_id"] == TEST_USER_ID


class TestBuildingStats:
    """Test building statistics endpoint"""
    
    def test_get_building_stats(self):
        """Test getting building statistics for a world"""
        response = requests.get(f"{BASE_URL}/api/building/stats/{TEST_WORLD_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_buildings" in data
        assert "by_category" in data
        assert "by_owner_type" in data
        assert isinstance(data["total_buildings"], int)


class TestDeploymentGuide:
    """Test that deployment guide exists and has required content"""
    
    def test_deployment_guide_exists(self):
        """Verify DEPLOYMENT_GUIDE.md exists"""
        import os
        guide_path = "/app/DEPLOYMENT_GUIDE.md"
        assert os.path.exists(guide_path), "DEPLOYMENT_GUIDE.md should exist"
        
    def test_deployment_guide_has_production_instructions(self):
        """Verify deployment guide has production deployment section"""
        with open("/app/DEPLOYMENT_GUIDE.md", "r") as f:
            content = f.read()
        
        # Check for key sections
        assert "Production Deployment" in content, "Should have Production Deployment section"
        assert "Docker" in content, "Should mention Docker"
        assert "docker-compose" in content.lower(), "Should have docker-compose instructions"
        
    def test_deployment_guide_has_troubleshooting(self):
        """Verify deployment guide has troubleshooting section"""
        with open("/app/DEPLOYMENT_GUIDE.md", "r") as f:
            content = f.read()
        
        assert "Troubleshooting" in content, "Should have Troubleshooting section"
        
    def test_deployment_guide_has_architecture(self):
        """Verify deployment guide has architecture overview"""
        with open("/app/DEPLOYMENT_GUIDE.md", "r") as f:
            content = f.read()
        
        assert "Architecture" in content, "Should have Architecture section"
        assert "FRONTEND" in content, "Should mention frontend in architecture"
        assert "BACKEND" in content, "Should mention backend in architecture"
