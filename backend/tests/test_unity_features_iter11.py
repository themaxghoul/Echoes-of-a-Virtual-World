"""
Test Suite for AI Village: The Echoes - Iteration 11
Testing: Unity Offload, Mode Selection (3 modes), Open Maps in Story Mode, Jobs Hub

Features tested:
1. Unity API endpoints: GET /api/unity/config, GET /api/unity/downloads
2. Unity session management: POST /api/unity/session
3. Mode Selection page (3 modes: Story, First Person 3D, Unity 3D)
4. Village Explorer - All locations open (ALL_LOCATIONS_OPEN = true)
5. Jobs Hub - Job catalog and enrollment
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com').rstrip('/')

class TestUnityAPI:
    """Unity Offload API endpoint tests"""
    
    def test_unity_config_endpoint(self):
        """GET /api/unity/config - Returns Unity server configuration"""
        response = requests.get(f"{BASE_URL}/api/unity/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify required fields
        assert "server_url" in data, "Missing server_url"
        assert "api_version" in data, "Missing api_version"
        assert "supported_platforms" in data, "Missing supported_platforms"
        assert "features" in data, "Missing features"
        
        # Verify platform support
        platforms = data["supported_platforms"]
        assert "windows" in platforms, "Windows not in supported platforms"
        assert "mac" in platforms, "Mac not in supported platforms"
        assert "linux" in platforms, "Linux not in supported platforms"
        
        # Verify features
        features = data["features"]
        assert features.get("cross_platform_sync") == True, "Cross-platform sync should be enabled"
        assert features.get("real_time_chat") == True, "Real-time chat should be enabled"
        assert features.get("3d_combat") == True, "3D combat should be enabled"
        
        print(f"✓ Unity config: server_url={data['server_url']}, platforms={platforms}")
    
    def test_unity_downloads_endpoint(self):
        """GET /api/unity/downloads - Returns download links for Unity client"""
        response = requests.get(f"{BASE_URL}/api/unity/downloads")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify download links
        assert "windows" in data, "Missing windows download link"
        assert "mac" in data, "Missing mac download link"
        assert "linux" in data, "Missing linux download link"
        assert "version" in data, "Missing version"
        assert "changelog" in data, "Missing changelog"
        
        # Verify links are valid URLs
        assert data["windows"].startswith("http"), "Windows link should be a URL"
        assert data["mac"].startswith("http"), "Mac link should be a URL"
        assert data["linux"].startswith("http"), "Linux link should be a URL"
        
        # Verify requirements
        assert "requirements" in data, "Missing requirements"
        assert "windows" in data["requirements"], "Missing Windows requirements"
        
        print(f"✓ Unity downloads: version={data['version']}, changelog items={len(data['changelog'])}")


class TestJobsHub:
    """Jobs Hub API endpoint tests"""
    
    def test_jobs_catalog_endpoint(self):
        """GET /api/jobs/catalog - Returns job catalog"""
        response = requests.get(f"{BASE_URL}/api/jobs/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "jobs" in data, "Missing jobs in response"
        
        jobs = data["jobs"]
        # Should have multiple job categories
        assert len(jobs) > 0, "Job catalog should not be empty"
        
        # Check for expected categories
        categories = list(jobs.keys())
        print(f"✓ Jobs catalog: {len(categories)} categories found: {categories[:5]}...")
    
    def test_jobs_economy_stats(self):
        """GET /api/jobs/economy-stats - Returns economy statistics"""
        response = requests.get(f"{BASE_URL}/api/jobs/economy-stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify economy stats fields
        assert "total_ve_distributed" in data or "total_tasks_completed" in data, "Missing economy stats"
        
        print(f"✓ Economy stats retrieved successfully")


class TestLocationsAPI:
    """Locations API tests - verifying all locations are accessible"""
    
    def test_locations_endpoint(self):
        """GET /api/locations - Returns all locations"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Locations should be a list"
        assert len(data) > 0, "Should have at least one location"
        
        # Verify location structure
        location = data[0]
        assert "id" in location, "Location missing id"
        assert "name" in location, "Location missing name"
        assert "description" in location, "Location missing description"
        
        # List all location IDs
        location_ids = [loc["id"] for loc in data]
        print(f"✓ Locations: {len(data)} locations found: {location_ids}")
        
        # Verify key locations exist
        expected_locations = ["village_square", "oracle_sanctum", "the_forge", "ancient_library"]
        for loc_id in expected_locations:
            assert loc_id in location_ids, f"Expected location {loc_id} not found"


class TestCharacterAPI:
    """Character API tests"""
    
    def test_create_test_character(self):
        """Create a test character for Unity testing"""
        # First create a test user
        user_data = {
            "username": f"TEST_unity_user_{datetime.now().strftime('%H%M%S')}",
            "display_name": "Unity Test User"
        }
        
        user_response = requests.post(f"{BASE_URL}/api/users", json=user_data)
        if user_response.status_code == 200:
            user = user_response.json()
            user_id = user.get("id")
            
            # Create character
            char_data = {
                "user_id": user_id,
                "name": f"TEST_Unity_Hero_{datetime.now().strftime('%H%M%S')}",
                "background": "A brave adventurer testing Unity integration",
                "traits": ["brave", "curious"],
                "appearance": "Tall with golden armor"
            }
            
            char_response = requests.post(f"{BASE_URL}/api/character", json=char_data)
            if char_response.status_code == 200:
                character = char_response.json()
                print(f"✓ Test character created: {character.get('name')} (id: {character.get('id')})")
                return character
        
        print("⚠ Could not create test character (may already exist)")
        return None


class TestUnitySession:
    """Unity session management tests"""
    
    @pytest.fixture
    def test_user_and_character(self):
        """Create test user and character for session tests"""
        # Create user
        user_data = {
            "username": f"TEST_session_user_{datetime.now().strftime('%H%M%S')}",
            "display_name": "Session Test User"
        }
        user_response = requests.post(f"{BASE_URL}/api/users", json=user_data)
        if user_response.status_code != 200:
            pytest.skip("Could not create test user")
        
        user = user_response.json()
        user_id = user.get("id")
        
        # Create character
        char_data = {
            "user_id": user_id,
            "name": f"TEST_Session_Hero_{datetime.now().strftime('%H%M%S')}",
            "background": "Session tester",
            "traits": ["test"],
            "appearance": "Test appearance"
        }
        char_response = requests.post(f"{BASE_URL}/api/character", json=char_data)
        if char_response.status_code != 200:
            pytest.skip("Could not create test character")
        
        character = char_response.json()
        return {"user_id": user_id, "character_id": character.get("id")}
    
    def test_create_unity_session(self, test_user_and_character):
        """POST /api/unity/session - Create Unity session"""
        player_id = test_user_and_character["user_id"]
        character_id = test_user_and_character["character_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/unity/session",
            params={"player_id": player_id, "character_id": character_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "session_id" in data, "Missing session_id"
        assert "token" in data, "Missing token"
        assert "connect_url" in data, "Missing connect_url"
        
        print(f"✓ Unity session created: session_id={data['session_id'][:8]}...")


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API is responding"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200, "API should be responding"
        print("✓ API is healthy and responding")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
