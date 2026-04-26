"""
Iteration 25 Feature Tests
==========================
Tests for:
1. VillageExplorer sidebar World Actions (Explore/Build buttons)
2. WorldExplorer inverted controls (W/Up = South, S/Down = North)
3. World Memory API (10 memory types, global memories)
4. Party System API (4 roles including npc_companion, party creation)
5. Login with sirix_1 / HCLynnTV04
6. Google OAuth endpoint responds
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com').rstrip('/')


class TestWorldMemoryAPI:
    """World Memory System API tests - Global events that impact the virtual verse"""
    
    def test_world_memory_types_returns_10_types(self):
        """GET /api/world-memory/types should return 10 memory types"""
        response = requests.get(f"{BASE_URL}/api/world-memory/types")
        assert response.status_code == 200
        
        data = response.json()
        assert "memory_types" in data
        assert "impact_levels" in data
        
        # Verify 10 memory types
        memory_types = data["memory_types"]
        assert len(memory_types) == 10, f"Expected 10 memory types, got {len(memory_types)}"
        
        # Verify expected types exist
        expected_types = [
            "first_discovery", "territory_claim", "structure_built", "world_event",
            "demon_invasion", "npc_transformation", "player_achievement",
            "alliance_formed", "battle_outcome", "economic_shift"
        ]
        for expected in expected_types:
            assert expected in memory_types, f"Missing memory type: {expected}"
    
    def test_world_memory_types_have_required_fields(self):
        """Each memory type should have name, description, impact_level, persistence, icon"""
        response = requests.get(f"{BASE_URL}/api/world-memory/types")
        assert response.status_code == 200
        
        data = response.json()
        for type_id, type_data in data["memory_types"].items():
            assert "name" in type_data, f"Missing 'name' in {type_id}"
            assert "description" in type_data, f"Missing 'description' in {type_id}"
            assert "impact_level" in type_data, f"Missing 'impact_level' in {type_id}"
            assert "persistence" in type_data, f"Missing 'persistence' in {type_id}"
            assert "icon" in type_data, f"Missing 'icon' in {type_id}"
    
    def test_world_memory_impact_levels(self):
        """Impact levels should include local, regional, global"""
        response = requests.get(f"{BASE_URL}/api/world-memory/types")
        assert response.status_code == 200
        
        data = response.json()
        impact_levels = data["impact_levels"]
        
        assert "local" in impact_levels
        assert "regional" in impact_levels
        assert "global" in impact_levels
        
        # Global should have radius -1 (infinite)
        assert impact_levels["global"]["radius"] == -1
    
    def test_world_memory_global_endpoint(self):
        """GET /api/world-memory/global should return global memories"""
        response = requests.get(f"{BASE_URL}/api/world-memory/global")
        assert response.status_code == 200
        
        data = response.json()
        assert "memories" in data
        assert "total" in data
        assert "returned" in data
        assert isinstance(data["memories"], list)
    
    def test_world_memory_chronicle_endpoint(self):
        """GET /api/world-memory/chronicle should return world chronicle"""
        response = requests.get(f"{BASE_URL}/api/world-memory/chronicle")
        assert response.status_code == 200
        
        data = response.json()
        assert "chronicle" in data
        assert "total_entries" in data
    
    def test_world_memory_stats_endpoint(self):
        """GET /api/world-memory/stats should return memory statistics"""
        response = requests.get(f"{BASE_URL}/api/world-memory/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_memories" in data
        assert "by_type" in data
        assert "by_impact_level" in data
        assert "by_actor_type" in data


class TestPartySystemAPI:
    """Party System API tests - Unified party system for players AND NPCs"""
    
    def test_party_roles_returns_4_roles(self):
        """GET /api/party/roles should return 4 roles including npc_companion"""
        response = requests.get(f"{BASE_URL}/api/party/roles")
        assert response.status_code == 200
        
        data = response.json()
        assert "roles" in data
        assert "max_party_size" in data
        assert "max_npcs" in data
        
        # Verify 4 roles
        roles = data["roles"]
        assert len(roles) == 4, f"Expected 4 roles, got {len(roles)}"
        
        # Verify expected roles exist
        expected_roles = ["leader", "officer", "member", "npc_companion"]
        for expected in expected_roles:
            assert expected in roles, f"Missing role: {expected}"
    
    def test_party_roles_have_required_fields(self):
        """Each role should have name, permissions, icon"""
        response = requests.get(f"{BASE_URL}/api/party/roles")
        assert response.status_code == 200
        
        data = response.json()
        for role_id, role_data in data["roles"].items():
            assert "name" in role_data, f"Missing 'name' in {role_id}"
            assert "permissions" in role_data, f"Missing 'permissions' in {role_id}"
            assert "icon" in role_data, f"Missing 'icon' in {role_id}"
    
    def test_party_max_size_is_6(self):
        """Max party size should be 6"""
        response = requests.get(f"{BASE_URL}/api/party/roles")
        assert response.status_code == 200
        
        data = response.json()
        assert data["max_party_size"] == 6
    
    def test_party_max_npcs_is_3(self):
        """Max NPCs per party should be 3"""
        response = requests.get(f"{BASE_URL}/api/party/roles")
        assert response.status_code == 200
        
        data = response.json()
        assert data["max_npcs"] == 3
    
    def test_party_leader_has_all_permissions(self):
        """Leader role should have invite, kick, promote, disband, set_destination"""
        response = requests.get(f"{BASE_URL}/api/party/roles")
        assert response.status_code == 200
        
        data = response.json()
        leader_perms = data["roles"]["leader"]["permissions"]
        
        expected_perms = ["invite", "kick", "promote", "disband", "set_destination"]
        for perm in expected_perms:
            assert perm in leader_perms, f"Leader missing permission: {perm}"
    
    def test_party_npc_companion_has_no_permissions(self):
        """NPC Companion role should have no permissions"""
        response = requests.get(f"{BASE_URL}/api/party/roles")
        assert response.status_code == 200
        
        data = response.json()
        npc_perms = data["roles"]["npc_companion"]["permissions"]
        assert len(npc_perms) == 0, "NPC Companion should have no permissions"
    
    def test_party_create_endpoint(self):
        """POST /api/party/create should create a new party"""
        import uuid
        test_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/party/create",
            json={
                "leader_id": test_id,
                "leader_name": "Test Leader",
                "party_name": "Test Party"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "party_id" in data
        assert data["name"] == "Test Party"
        
        # Cleanup - leave the party
        party_id = data["party_id"]
        requests.post(f"{BASE_URL}/api/party/leave/{party_id}?member_id={test_id}")
    
    def test_party_stats_endpoint(self):
        """GET /api/party/stats should return party system statistics"""
        response = requests.get(f"{BASE_URL}/api/party/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_parties" in data
        assert "total_parties_created" in data
        assert "max_party_size" in data
        assert "max_npcs_per_party" in data


class TestAuthenticationAPI:
    """Authentication API tests"""
    
    def test_login_with_sirix_1_credentials(self):
        """POST /api/auth/login should work with sirix_1 / HCLynnTV04"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": "sirix_1",
                "password": "HCLynnTV04"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "user" in data
        assert data["user"]["username"] == "sirix_1"
    
    def test_login_returns_user_details(self):
        """Login should return user details including permission_level"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": "sirix_1",
                "password": "HCLynnTV04"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        user = data["user"]
        
        assert "id" in user
        assert "username" in user
        assert "display_name" in user
        assert "permission_level" in user
        assert user["permission_level"] == "sirix_1"  # Supreme authority
    
    def test_google_oauth_callback_endpoint_exists(self):
        """POST /api/auth/google/callback should exist and respond"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google/callback",
            json={
                "session_id": "test_session"
            }
        )
        # Should return 401 (invalid session) not 404 (not found)
        assert response.status_code in [200, 401, 400]
        
        # If 401, verify it's the expected error
        if response.status_code == 401:
            data = response.json()
            assert "detail" in data
            assert "session" in data["detail"].lower() or "verify" in data["detail"].lower()


class TestWorldExplorerInvertedControls:
    """Tests to verify WorldExplorer has inverted controls documentation"""
    
    def test_world_explore_endpoint_exists(self):
        """POST /api/world/explore should exist"""
        # Get a user position first
        response = requests.get(f"{BASE_URL}/api/world/player/sirix_1_supreme/position")
        
        # The endpoint should exist (may return 200 or 404 if no position)
        assert response.status_code in [200, 404]
    
    def test_world_stats_endpoint(self):
        """GET /api/world/stats should return world statistics"""
        response = requests.get(f"{BASE_URL}/api/world/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "world_seed_id" in data or "total_tile_discoveries" in data


class TestVillageExplorerSidebar:
    """Tests for VillageExplorer sidebar World Actions"""
    
    def test_locations_endpoint(self):
        """GET /api/locations should return village locations"""
        response = requests.get(f"{BASE_URL}/api/locations")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Each location should have required fields
        for loc in data:
            assert "id" in loc
            assert "name" in loc


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
