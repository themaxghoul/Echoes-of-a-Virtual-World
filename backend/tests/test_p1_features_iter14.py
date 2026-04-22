"""
P1 Features Test Suite - Iteration 14
Tests: Task Marketplace, Building System, World Map, Character Customization with 3D Model Descriptors
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com')

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestTaskMarketplace:
    """Task Marketplace API tests - 10 categories for human/robot integration"""
    
    def test_get_categories_returns_10_categories(self, api_client):
        """GET /api/task-marketplace/categories returns 10 task categories"""
        response = api_client.get(f"{BASE_URL}/api/task-marketplace/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 10
        
        expected_categories = [
            "data_labeling", "transcription", "content_moderation", "ai_training",
            "quality_assurance", "creative_writing", "creative_art", "translation",
            "research", "world_building"
        ]
        for cat in expected_categories:
            assert cat in data["categories"], f"Missing category: {cat}"
    
    def test_categories_have_required_fields(self, api_client):
        """Each category has name, description, icon, color, base_pay_range, skills_rewarded"""
        response = api_client.get(f"{BASE_URL}/api/task-marketplace/categories")
        data = response.json()
        
        for cat_id, cat_data in data["categories"].items():
            assert "name" in cat_data, f"{cat_id} missing name"
            assert "description" in cat_data, f"{cat_id} missing description"
            assert "icon" in cat_data, f"{cat_id} missing icon"
            assert "color" in cat_data, f"{cat_id} missing color"
            assert "base_pay_range" in cat_data, f"{cat_id} missing base_pay_range"
            assert "skills_rewarded" in cat_data, f"{cat_id} missing skills_rewarded"
            assert len(cat_data["base_pay_range"]) == 2, f"{cat_id} base_pay_range should have 2 values"
    
    def test_difficulty_levels_returned(self, api_client):
        """GET /api/task-marketplace/categories returns difficulty levels"""
        response = api_client.get(f"{BASE_URL}/api/task-marketplace/categories")
        data = response.json()
        
        assert "difficulty_levels" in data
        expected_difficulties = ["trivial", "easy", "medium", "hard", "expert", "legendary"]
        for diff in expected_difficulties:
            assert diff in data["difficulty_levels"], f"Missing difficulty: {diff}"
            assert "multiplier" in data["difficulty_levels"][diff]
            assert "xp_bonus" in data["difficulty_levels"][diff]
    
    def test_list_tasks_endpoint(self, api_client):
        """GET /api/task-marketplace/tasks returns task list"""
        response = api_client.get(f"{BASE_URL}/api/task-marketplace/tasks")
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert isinstance(data["tasks"], list)
    
    def test_marketplace_stats_endpoint(self, api_client):
        """GET /api/task-marketplace/stats returns marketplace statistics"""
        response = api_client.get(f"{BASE_URL}/api/task-marketplace/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_tasks" in data
        assert "open_tasks" in data
        assert "completed_tasks" in data


class TestBuildingSystem:
    """Building System API tests - 5 categories with grid-based placement"""
    
    def test_get_catalog_returns_5_categories(self, api_client):
        """GET /api/building/catalog returns 5 building categories"""
        response = api_client.get(f"{BASE_URL}/api/building/catalog")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 5
        
        expected_categories = [
            "basic_structures", "functional_buildings", "decorative", "paths", "special"
        ]
        for cat in expected_categories:
            assert cat in data["categories"], f"Missing category: {cat}"
    
    def test_catalog_has_grid_settings(self, api_client):
        """Building catalog includes grid_size and cell_size"""
        response = api_client.get(f"{BASE_URL}/api/building/catalog")
        data = response.json()
        
        assert "grid_size" in data
        assert "cell_size" in data
        assert data["grid_size"] == 100
        assert data["cell_size"] == 32
    
    def test_basic_structures_has_buildings(self, api_client):
        """Basic structures category has expected buildings"""
        response = api_client.get(f"{BASE_URL}/api/building/catalog")
        data = response.json()
        
        basic = data["categories"]["basic_structures"]
        assert "items" in basic
        expected_buildings = ["wooden_house", "stone_house", "cottage", "tower", "wall_segment", "gate", "bridge"]
        for building in expected_buildings:
            assert building in basic["items"], f"Missing building: {building}"
    
    def test_functional_buildings_have_functions(self, api_client):
        """Functional buildings have function field"""
        response = api_client.get(f"{BASE_URL}/api/building/catalog")
        data = response.json()
        
        functional = data["categories"]["functional_buildings"]["items"]
        for building_id, building_data in functional.items():
            assert "function" in building_data, f"{building_id} missing function"
    
    def test_buildings_have_required_fields(self, api_client):
        """Each building has name, size, cost, materials"""
        response = api_client.get(f"{BASE_URL}/api/building/catalog")
        data = response.json()
        
        for cat_id, cat_data in data["categories"].items():
            for building_id, building_data in cat_data["items"].items():
                assert "name" in building_data, f"{building_id} missing name"
                assert "size" in building_data, f"{building_id} missing size"
                assert "cost" in building_data, f"{building_id} missing cost"
                assert "materials" in building_data, f"{building_id} missing materials"
                assert len(building_data["size"]) == 2, f"{building_id} size should be [width, height]"


class TestWorldMap:
    """World Map API tests - 8 regions, 15 terrain types"""
    
    def test_get_config_returns_8_regions(self, api_client):
        """GET /api/world-map/config returns 8 regions"""
        response = api_client.get(f"{BASE_URL}/api/world-map/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "regions" in data
        assert len(data["regions"]) == 8
        
        expected_regions = [
            "village_square", "oracle_sanctum", "the_forge", "ancient_library",
            "wanderers_rest", "shadow_grove", "watchtower", "outer_realms"
        ]
        for region in expected_regions:
            assert region in data["regions"], f"Missing region: {region}"
    
    def test_get_config_returns_15_terrain_types(self, api_client):
        """GET /api/world-map/config returns 15 terrain types"""
        response = api_client.get(f"{BASE_URL}/api/world-map/config")
        data = response.json()
        
        assert "terrain_types" in data
        assert len(data["terrain_types"]) == 15
    
    def test_regions_have_required_fields(self, api_client):
        """Each region has name, position, size, terrain, color, connectedTo"""
        response = api_client.get(f"{BASE_URL}/api/world-map/config")
        data = response.json()
        
        for region_id, region_data in data["regions"].items():
            assert "name" in region_data, f"{region_id} missing name"
            assert "position" in region_data, f"{region_id} missing position"
            assert "size" in region_data, f"{region_id} missing size"
            assert "terrain" in region_data, f"{region_id} missing terrain"
            assert "color" in region_data, f"{region_id} missing color"
            assert "connectedTo" in region_data, f"{region_id} missing connectedTo"
    
    def test_terrain_types_have_required_fields(self, api_client):
        """Each terrain type has color, traversable, speed_mod"""
        response = api_client.get(f"{BASE_URL}/api/world-map/config")
        data = response.json()
        
        for terrain_id, terrain_data in data["terrain_types"].items():
            assert "color" in terrain_data, f"{terrain_id} missing color"
            assert "traversable" in terrain_data, f"{terrain_id} missing traversable"
            assert "speed_mod" in terrain_data, f"{terrain_id} missing speed_mod"
    
    def test_default_size_returned(self, api_client):
        """World map config includes default_size"""
        response = api_client.get(f"{BASE_URL}/api/world-map/config")
        data = response.json()
        
        assert "default_size" in data
        assert data["default_size"]["width"] == 100
        assert data["default_size"]["height"] == 100


class TestCharacterCustomization:
    """Character API tests - 3D Model Descriptors for Unity"""
    
    def test_create_character_with_model(self, api_client):
        """POST /api/characters creates character with 3D model descriptor"""
        test_id = f"TEST_char_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/characters", json={
            "user_id": test_id,
            "name": f"Test Character {test_id}",
            "background": "A test character for P1 features",
            "traits": ["Brave", "Curious"],
            "appearance": "Tall and mysterious",
            "model": {
                "bodyType": "athletic",
                "faceType": "angular",
                "skinTone": "medium",
                "hairStyle": "short",
                "hairColor": "black",
                "eyeColor": "blue",
                "clothingStyle": "adventurer",
                "height": 180,
                "age": 30,
                "scars": True,
                "tattoos": False,
                "beard": False,
                "accessories": []
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == f"Test Character {test_id}"
        
        return data["id"]
    
    def test_update_character_model(self, api_client):
        """PUT /api/character/{id} updates character with new model"""
        # First create a character
        test_id = f"TEST_update_{uuid.uuid4().hex[:8]}"
        
        create_response = api_client.post(f"{BASE_URL}/api/characters", json={
            "user_id": test_id,
            "name": f"Update Test {test_id}",
            "background": "Original background",
            "traits": ["Brave"],
            "appearance": "Original appearance"
        })
        
        assert create_response.status_code == 200
        char_id = create_response.json()["id"]
        
        # Update the character
        update_response = api_client.put(f"{BASE_URL}/api/character/{char_id}", json={
            "name": f"Updated {test_id}",
            "background": "Updated background",
            "traits": ["Brave", "Wise"],
            "appearance": "Updated appearance",
            "model": {
                "bodyType": "muscular",
                "faceType": "square",
                "skinTone": "tan",
                "hairStyle": "long",
                "hairColor": "brown",
                "eyeColor": "green",
                "clothingStyle": "warrior",
                "height": 185,
                "age": 35,
                "scars": True,
                "tattoos": True,
                "beard": True,
                "accessories": ["ring"]
            }
        })
        
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["status"] == "success"
        assert "model" in update_data["updated_fields"]
    
    def test_get_character_returns_model(self, api_client):
        """GET /api/character/{id} returns character with model"""
        # Create character with model
        test_id = f"TEST_get_{uuid.uuid4().hex[:8]}"
        
        create_response = api_client.post(f"{BASE_URL}/api/characters", json={
            "user_id": test_id,
            "name": f"Get Test {test_id}",
            "background": "Test background",
            "traits": ["Curious"],
            "model": {
                "bodyType": "slender",
                "height": 165
            }
        })
        
        char_id = create_response.json()["id"]
        
        # Get the character
        get_response = api_client.get(f"{BASE_URL}/api/character/{char_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert "model" in data
        assert data["model"]["bodyType"] == "slender"
        assert data["model"]["height"] == 165


class TestContinueJourneyAuth:
    """Continue Journey auth check tests"""
    
    def test_character_belongs_to_user(self, api_client):
        """Character endpoint returns user_id for ownership verification"""
        # Create a character
        test_user = f"TEST_auth_user_{uuid.uuid4().hex[:8]}"
        
        create_response = api_client.post(f"{BASE_URL}/api/characters", json={
            "user_id": test_user,
            "name": "Auth Test Character",
            "background": "Testing auth"
        })
        
        char_id = create_response.json()["id"]
        
        # Get character and verify user_id is returned
        get_response = api_client.get(f"{BASE_URL}/api/character/{char_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert "user_id" in data
        assert data["user_id"] == test_user
    
    def test_character_not_found_returns_404(self, api_client):
        """GET /api/character/{invalid_id} returns 404"""
        response = api_client.get(f"{BASE_URL}/api/character/nonexistent-id-12345")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
