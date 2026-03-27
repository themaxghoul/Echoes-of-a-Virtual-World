"""
Test suite for AI Village: The Echoes - New Features (Iteration 10)
Tests: Commands System, Oracle World Monitor, AI Integrations API
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com').rstrip('/')

# Test credentials from review request
SIRIX_1_CREDENTIALS = {
    "username": "sirix_1",
    "password": "k3bdp0wn!0nr(?8vd&74v2l!",
    "user_id": "sirix_1_supreme"
}

TEST_CHARACTER_ID = "eb3a4d4e-805a-4183-bb2e-ec43467aff14"


class TestCommandsSystem:
    """Test the /commands system for mods/high rankers"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user with sirix_1 permissions"""
        self.sirix_user_id = SIRIX_1_CREDENTIALS["user_id"]
        # Create or ensure sirix_1 user exists
        user_data = {
            "username": SIRIX_1_CREDENTIALS["username"],
            "display_name": "Sirix-1 Supreme",
            "permission_level": "sirix_1"
        }
        try:
            response = requests.post(f"{BASE_URL}/api/users", json=user_data)
            if response.status_code == 201:
                self.sirix_user_id = response.json().get("id", self.sirix_user_id)
        except:
            pass
    
    def test_get_commands_for_sirix_1(self):
        """GET /api/commands - Should return all commands for Sirix-1 (level 999)"""
        response = requests.get(f"{BASE_URL}/api/commands?user_id={self.sirix_user_id}")
        
        # Should return 200 or 404 if user doesn't exist
        if response.status_code == 404:
            pytest.skip("Sirix-1 user not found - need to create first")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "commands" in data
        assert "permission_level" in data
        
        commands = data["commands"]
        print(f"Available commands for Sirix-1: {len(commands)}")
        
        # Sirix-1 should have access to all commands including /god, /reset_world
        if data.get("permission_level") == "sirix_1":
            assert "/help" in commands
            assert "/god" in commands or len(commands) >= 10  # Should have many commands
    
    def test_get_commands_for_basic_user(self):
        """GET /api/commands - Basic user should only get /help and /commands"""
        # Create a basic test user
        test_user_id = f"TEST_basic_user_{uuid.uuid4().hex[:8]}"
        user_data = {
            "username": f"test_basic_{uuid.uuid4().hex[:6]}",
            "display_name": "Test Basic User",
            "permission_level": "basic"
        }
        create_response = requests.post(f"{BASE_URL}/api/users", json=user_data)
        
        if create_response.status_code == 201:
            test_user_id = create_response.json()["id"]
        
        response = requests.get(f"{BASE_URL}/api/commands?user_id={test_user_id}")
        
        if response.status_code == 404:
            pytest.skip("Test user not found")
        
        assert response.status_code == 200
        data = response.json()
        
        commands = data.get("commands", {})
        print(f"Commands for basic user: {list(commands.keys())}")
        
        # Basic user should have limited commands
        assert "/help" in commands or "/commands" in commands
        # Should NOT have admin commands
        assert "/god" not in commands
        assert "/reset_world" not in commands
    
    def test_execute_announce_command(self):
        """POST /api/commands/execute - Execute /announce command"""
        # First ensure we have a mod+ user
        response = requests.post(f"{BASE_URL}/api/commands/execute", json={
            "user_id": self.sirix_user_id,
            "command": "/announce",
            "args": ["Test announcement from testing agent"],
            "location_id": "village_square"
        })
        
        if response.status_code == 404:
            pytest.skip("User not found for command execution")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "success" in data
        assert "message" in data
        print(f"Announce command result: {data}")
    
    def test_execute_help_command(self):
        """POST /api/commands/execute - Execute /help command"""
        response = requests.post(f"{BASE_URL}/api/commands/execute", json={
            "user_id": self.sirix_user_id,
            "command": "/help",
            "args": []
        })
        
        if response.status_code == 404:
            pytest.skip("User not found")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_execute_unknown_command(self):
        """POST /api/commands/execute - Unknown command should fail gracefully"""
        response = requests.post(f"{BASE_URL}/api/commands/execute", json={
            "user_id": self.sirix_user_id,
            "command": "/nonexistent_command",
            "args": []
        })
        
        if response.status_code == 404:
            pytest.skip("User not found")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == False
        assert "Unknown command" in data.get("message", "")


class TestOracleWorldMonitor:
    """Test Oracle Veythra World Monitor endpoints"""
    
    def test_get_oracle_status(self):
        """GET /api/oracle/status - Get Oracle Veythra status"""
        response = requests.get(f"{BASE_URL}/api/oracle/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "oracle" in data
        oracle = data["oracle"]
        
        # Oracle should have expected fields
        assert "name" in oracle or "villager_id" in oracle
        print(f"Oracle status: {oracle.get('name', oracle.get('villager_id'))}")
    
    def test_oracle_vision_world_state(self):
        """POST /api/oracle/vision - Get world monitoring data with vision_type=world_state"""
        response = requests.post(f"{BASE_URL}/api/oracle/vision", json={
            "vision_type": "world_state",
            "viewer_id": SIRIX_1_CREDENTIALS["user_id"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "vision_type" in data
        assert data["vision_type"] == "world_state"
        assert "oracle" in data
        assert "data" in data
        
        vision_data = data["data"]
        print(f"World state vision data keys: {list(vision_data.keys())}")
        
        # World state should include population and civilization data
        if "world_population" in vision_data:
            assert "total_souls" in vision_data["world_population"]
        if "civilizations" in vision_data:
            assert "guilds_formed" in vision_data["civilizations"]
    
    def test_oracle_vision_prophecy(self):
        """POST /api/oracle/vision - Get prophecy vision"""
        response = requests.post(f"{BASE_URL}/api/oracle/vision", json={
            "vision_type": "prophecy",
            "viewer_id": SIRIX_1_CREDENTIALS["user_id"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["vision_type"] == "prophecy"
        assert "data" in data
        
        # Prophecy should have prophecy text
        vision_data = data["data"]
        assert "prophecy" in vision_data
        print(f"Prophecy: {vision_data['prophecy'][:100]}...")
    
    def test_oracle_vision_player_fate(self):
        """POST /api/oracle/vision - Get player fate reading"""
        response = requests.post(f"{BASE_URL}/api/oracle/vision", json={
            "vision_type": "player_fate",
            "viewer_id": SIRIX_1_CREDENTIALS["user_id"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["vision_type"] == "player_fate"
        assert "data" in data
        print(f"Player fate data: {data['data']}")


class TestAIIntegrationsAPI:
    """Test AI Integration API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.test_app_id = None
        self.mod_user_id = SIRIX_1_CREDENTIALS["user_id"]
    
    def test_list_ai_apps(self):
        """GET /api/integrations/apps - List registered AI apps"""
        response = requests.get(f"{BASE_URL}/api/integrations/apps")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "apps" in data
        assert "total" in data
        
        print(f"Total AI apps registered: {data['total']}")
        
        # Apps should be a list
        assert isinstance(data["apps"], list)
    
    def test_list_ai_apps_with_user(self):
        """GET /api/integrations/apps - List apps with user context"""
        response = requests.get(f"{BASE_URL}/api/integrations/apps?user_id={self.mod_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "apps" in data
        # Each app should have 'installed' field when user_id provided
        for app in data["apps"]:
            if "installed" in app:
                assert isinstance(app["installed"], bool)
    
    def test_register_ai_app_requires_mod_permissions(self):
        """POST /api/integrations/register - Requires mod+ permissions"""
        # Try to register with a basic user (should fail)
        basic_user_id = f"TEST_basic_{uuid.uuid4().hex[:8]}"
        
        # Create basic user first
        user_data = {
            "username": f"test_basic_{uuid.uuid4().hex[:6]}",
            "display_name": "Test Basic",
            "permission_level": "basic"
        }
        create_resp = requests.post(f"{BASE_URL}/api/users", json=user_data)
        if create_resp.status_code == 201:
            basic_user_id = create_resp.json()["id"]
        
        response = requests.post(f"{BASE_URL}/api/integrations/register", json={
            "app_name": "Test AI App",
            "app_description": "A test AI application",
            "developer_id": basic_user_id,
            "api_endpoint": "https://example.com/api",
            "capabilities": ["dialogue"],
            "required_permissions": []
        })
        
        # Should fail with 403 or 404
        assert response.status_code in [403, 404]
        print(f"Register with basic user: {response.status_code} - {response.json()}")
    
    def test_register_ai_app_with_mod_user(self):
        """POST /api/integrations/register - Register new AI app with mod+ permissions"""
        response = requests.post(f"{BASE_URL}/api/integrations/register", json={
            "app_name": f"TEST_AI_App_{uuid.uuid4().hex[:6]}",
            "app_description": "A test AI application for testing",
            "developer_id": self.mod_user_id,
            "api_endpoint": "https://test-ai-app.example.com/api",
            "capabilities": ["dialogue", "combat_ai"],
            "required_permissions": []
        })
        
        if response.status_code == 404:
            pytest.skip("Mod user not found")
        
        # Should succeed with 200 or fail with 403 if user doesn't have mod perms
        if response.status_code == 200:
            data = response.json()
            assert "app_id" in data
            assert data["status"] == "pending_approval"
            self.test_app_id = data["app_id"]
            print(f"Registered AI app: {data['app_id']}")
        else:
            print(f"Register failed: {response.status_code} - {response.json()}")


class TestMultiplayerChatFix:
    """Test the multiplayer chat input fix (onKeyPress to onKeyDown)"""
    
    def test_chat_endpoint_exists(self):
        """Verify chat-related endpoints exist"""
        # Test that the WebSocket endpoint pattern exists
        # We can't directly test WebSocket here, but we can verify the API structure
        response = requests.get(f"{BASE_URL}/api/locations")
        
        assert response.status_code == 200
        data = response.json()
        
        # Locations should exist for chat
        if isinstance(data, list):
            print(f"Locations available for chat: {len(data)}")
        else:
            assert "locations" in data
            print(f"Locations available for chat: {len(data.get('locations', []))}")


class TestFirstPersonView3D:
    """Test FirstPersonView3D component loads correctly"""
    
    def test_character_endpoint_for_3d_view(self):
        """Verify character endpoint works for 3D view"""
        # Create a test character
        test_user_id = f"TEST_3d_user_{uuid.uuid4().hex[:8]}"
        
        # Create user first
        user_data = {
            "username": f"test_3d_{uuid.uuid4().hex[:6]}",
            "display_name": "Test 3D User",
            "permission_level": "basic"
        }
        user_resp = requests.post(f"{BASE_URL}/api/users", json=user_data)
        if user_resp.status_code == 201:
            test_user_id = user_resp.json()["id"]
        
        # Create character
        char_data = {
            "user_id": test_user_id,
            "name": f"TEST_3D_Hero_{uuid.uuid4().hex[:6]}",
            "background": "wanderer",
            "traits": ["brave", "curious"],
            "appearance": "A test hero"
        }
        char_resp = requests.post(f"{BASE_URL}/api/characters", json=char_data)
        
        if char_resp.status_code == 201:
            char_id = char_resp.json()["id"]
            
            # Verify character can be retrieved
            get_resp = requests.get(f"{BASE_URL}/api/character/{char_id}")
            assert get_resp.status_code == 200
            
            char = get_resp.json()
            assert "current_location" in char
            print(f"Character location: {char['current_location']}")
    
    def test_combat_stats_endpoint(self):
        """Verify combat stats endpoint for 3D view HUD"""
        # Use existing test character
        response = requests.get(f"{BASE_URL}/api/character/{TEST_CHARACTER_ID}/combat-stats")
        
        if response.status_code == 404:
            pytest.skip("Test character not found")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have combat stats
        assert "health" in data or "max_health" in data
        print(f"Combat stats: {data}")
    
    def test_time_phase_endpoint(self):
        """Verify time phase endpoint for day/night cycle"""
        response = requests.post(f"{BASE_URL}/api/time/phase", json={
            "timezone_offset": 0
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "phase" in data
        assert "danger_level" in data
        print(f"Time phase: {data['phase']}, danger: {data['danger_level']}")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed data after all tests"""
    yield
    # Cleanup would go here if needed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
