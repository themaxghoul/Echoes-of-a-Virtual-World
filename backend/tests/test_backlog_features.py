"""
Test suite for AI Village backlog features:
- Travel distance tracking & land discoveries (POST /api/character/{id}/move)
- PvP combat system (challenge, accept, attack, active session)
- Time phase system (GET /api/time/phase)
- Mood-based AI villager dialogue (GET /api/villagers/{id}/dialogue)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SIRIX_USERNAME = "sirix_1"
SIRIX_PASSWORD = "k3bdp0wn!0nr(?8vd&74v2l!"

# Test fixtures
@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def test_user(api_client):
    """Create a test user for PvP testing"""
    username = f"TEST_pvp_user_{uuid.uuid4().hex[:8]}"
    response = api_client.post(f"{BASE_URL}/api/users", json={
        "username": username,
        "display_name": "PvP Test User",
        "permission_level": "basic"
    })
    if response.status_code == 200:
        return response.json()
    return None

@pytest.fixture(scope="module")
def test_character_1(api_client, test_user):
    """Create test character 1 for PvP"""
    if not test_user:
        pytest.skip("Test user not created")
    response = api_client.post(f"{BASE_URL}/api/characters", json={
        "user_id": test_user["id"],
        "name": f"TEST_Fighter_{uuid.uuid4().hex[:6]}",
        "background": "warrior",
        "traits": ["brave", "strong"]
    })
    if response.status_code == 200:
        return response.json()
    return None

@pytest.fixture(scope="module")
def test_user_2(api_client):
    """Create a second test user for PvP opponent"""
    username = f"TEST_pvp_user2_{uuid.uuid4().hex[:8]}"
    response = api_client.post(f"{BASE_URL}/api/users", json={
        "username": username,
        "display_name": "PvP Opponent",
        "permission_level": "basic"
    })
    if response.status_code == 200:
        return response.json()
    return None

@pytest.fixture(scope="module")
def test_character_2(api_client, test_user_2):
    """Create test character 2 for PvP opponent"""
    if not test_user_2:
        pytest.skip("Test user 2 not created")
    response = api_client.post(f"{BASE_URL}/api/characters", json={
        "user_id": test_user_2["id"],
        "name": f"TEST_Opponent_{uuid.uuid4().hex[:6]}",
        "background": "rogue",
        "traits": ["quick", "cunning"]
    })
    if response.status_code == 200:
        return response.json()
    return None

@pytest.fixture(scope="module")
def test_villager(api_client):
    """Create a test AI villager for dialogue testing"""
    response = api_client.post(f"{BASE_URL}/api/villagers", json={
        "name": f"TEST_Merchant_{uuid.uuid4().hex[:6]}",
        "profession": "merchant",
        "personality": "friendly",
        "home_location": "village_square"
    })
    if response.status_code == 200:
        return response.json()
    return None


# ==========================================
# Travel Distance Tracking Tests
# ==========================================

class TestTravelDistanceTracking:
    """Test travel distance tracking and land discoveries"""
    
    def test_move_tracks_distance(self, api_client, test_character_1):
        """POST /api/character/{id}/move - should track total_distance_traveled"""
        if not test_character_1:
            pytest.skip("Test character not created")
        
        char_id = test_character_1["id"]
        
        # Move character multiple times
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json={
            "character_id": char_id,
            "direction": "right",
            "is_sprinting": False
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify distance tracking fields
        assert "distance_moved" in data
        assert "total_distance_traveled" in data
        assert data["distance_moved"] > 0
        assert data["total_distance_traveled"] > 0
        print(f"✓ Move tracks distance: moved {data['distance_moved']}, total: {data['total_distance_traveled']}")
    
    def test_sprint_moves_faster(self, api_client, test_character_1):
        """POST /api/character/{id}/move - sprinting should move faster"""
        if not test_character_1:
            pytest.skip("Test character not created")
        
        char_id = test_character_1["id"]
        
        # Move normally
        normal_res = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json={
            "character_id": char_id,
            "direction": "up",
            "is_sprinting": False
        })
        
        # Move sprinting
        sprint_res = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json={
            "character_id": char_id,
            "direction": "up",
            "is_sprinting": True
        })
        
        assert normal_res.status_code == 200
        assert sprint_res.status_code == 200
        
        normal_speed = normal_res.json()["speed"]
        sprint_speed = sprint_res.json()["speed"]
        
        # Sprint should be 2x normal (if stamina available)
        assert sprint_speed >= normal_speed  # Should be faster or equal
        print(f"✓ Sprint speed: {sprint_speed}, Normal speed: {normal_speed}")
    
    def test_move_returns_discoveries_field(self, api_client, test_character_1):
        """POST /api/character/{id}/move - should include discoveries in response"""
        if not test_character_1:
            pytest.skip("Test character not created")
        
        char_id = test_character_1["id"]
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json={
            "character_id": char_id,
            "direction": "down",
            "is_sprinting": False
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify discoveries field exists (may be empty array)
        assert "discoveries" in data
        assert isinstance(data["discoveries"], list)
        print(f"✓ Move returns discoveries field: {data['discoveries']}")


# ==========================================
# PvP Combat System Tests
# ==========================================

class TestPvPCombatSystem:
    """Test PvP combat system endpoints"""
    
    def test_pvp_challenge_creation(self, api_client, test_character_1, test_character_2):
        """POST /api/pvp/challenge - create PvP challenge between players"""
        if not test_character_1 or not test_character_2:
            pytest.skip("Test characters not created")
        
        # Set both characters to same location first
        api_client.put(f"{BASE_URL}/api/character/{test_character_1['id']}/location?location_id=village_square")
        api_client.put(f"{BASE_URL}/api/character/{test_character_2['id']}/location?location_id=village_square")
        
        response = api_client.post(f"{BASE_URL}/api/pvp/challenge", json={
            "challenger_id": test_character_1["id"],
            "target_id": test_character_2["id"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "challenge_sent"
        assert "session" in data
        assert data["session"]["challenger_id"] == test_character_1["id"]
        assert data["session"]["target_id"] == test_character_2["id"]
        assert data["session"]["status"] == "pending"
        print(f"✓ PvP challenge created: {data['message']}")
        
        # Store session_id for later tests
        return data["session"]["id"]
    
    def test_pvp_challenge_requires_same_location(self, api_client, test_character_1, test_character_2):
        """POST /api/pvp/challenge - should fail if players in different locations"""
        if not test_character_1 or not test_character_2:
            pytest.skip("Test characters not created")
        
        # Move one character to different location
        api_client.put(f"{BASE_URL}/api/character/{test_character_1['id']}/location?location_id=the_forge")
        api_client.put(f"{BASE_URL}/api/character/{test_character_2['id']}/location?location_id=oracle_sanctum")
        
        response = api_client.post(f"{BASE_URL}/api/pvp/challenge", json={
            "challenger_id": test_character_1["id"],
            "target_id": test_character_2["id"]
        })
        
        assert response.status_code == 400
        assert "same location" in response.json()["detail"].lower()
        print("✓ PvP challenge correctly requires same location")
    
    def test_pvp_accept_challenge(self, api_client, test_character_1, test_character_2):
        """POST /api/pvp/{id}/accept - accept PvP challenge"""
        if not test_character_1 or not test_character_2:
            pytest.skip("Test characters not created")
        
        # First create a fresh challenge (set same location)
        api_client.put(f"{BASE_URL}/api/character/{test_character_1['id']}/location?location_id=village_square")
        api_client.put(f"{BASE_URL}/api/character/{test_character_2['id']}/location?location_id=village_square")
        
        create_res = api_client.post(f"{BASE_URL}/api/pvp/challenge", json={
            "challenger_id": test_character_1["id"],
            "target_id": test_character_2["id"]
        })
        
        if create_res.status_code != 200:
            pytest.skip("Could not create PvP challenge")
        
        session_id = create_res.json()["session"]["id"]
        
        # Accept the challenge
        response = api_client.post(
            f"{BASE_URL}/api/pvp/{session_id}/accept?target_id={test_character_2['id']}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "accepted"
        assert "PvP combat begins" in data["message"]
        print(f"✓ PvP challenge accepted: {data['message']}")
        
        return session_id
    
    def test_pvp_attack(self, api_client, test_character_1, test_character_2):
        """POST /api/pvp/{id}/attack - PvP combat attack"""
        if not test_character_1 or not test_character_2:
            pytest.skip("Test characters not created")
        
        # Create and accept a new challenge first
        api_client.put(f"{BASE_URL}/api/character/{test_character_1['id']}/location?location_id=village_square")
        api_client.put(f"{BASE_URL}/api/character/{test_character_2['id']}/location?location_id=village_square")
        
        # Reset characters health for clean test
        api_client.post(f"{BASE_URL}/api/character/{test_character_1['id']}/regenerate")
        api_client.post(f"{BASE_URL}/api/character/{test_character_2['id']}/regenerate")
        
        create_res = api_client.post(f"{BASE_URL}/api/pvp/challenge", json={
            "challenger_id": test_character_1["id"],
            "target_id": test_character_2["id"]
        })
        
        if create_res.status_code != 200:
            pytest.skip("Could not create PvP challenge")
        
        session_id = create_res.json()["session"]["id"]
        
        # Accept challenge
        accept_res = api_client.post(
            f"{BASE_URL}/api/pvp/{session_id}/accept?target_id={test_character_2['id']}"
        )
        
        if accept_res.status_code != 200:
            pytest.skip("Could not accept PvP challenge")
        
        # Execute attack
        response = api_client.post(f"{BASE_URL}/api/pvp/{session_id}/attack", json={
            "attacker_id": test_character_1["id"],
            "defender_id": test_character_2["id"],
            "action": "attack"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "damage" in data
        assert "defender_health_remaining" in data
        assert "attacker_stamina_remaining" in data
        assert data["damage"] > 0
        print(f"✓ PvP attack dealt {data['damage']} damage, defender HP: {data['defender_health_remaining']}")
    
    def test_pvp_get_active_session(self, api_client, test_character_1):
        """GET /api/pvp/active/{character_id} - check active PvP session"""
        if not test_character_1:
            pytest.skip("Test character not created")
        
        char_id = test_character_1["id"]
        
        response = api_client.get(f"{BASE_URL}/api/pvp/active/{char_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 'active' field
        assert "active" in data
        print(f"✓ Active PvP check: active={data['active']}")
    
    def test_pvp_invalid_action_fails(self, api_client, test_character_1, test_character_2):
        """POST /api/pvp/{id}/attack - invalid action should fail"""
        if not test_character_1 or not test_character_2:
            pytest.skip("Test characters not created")
        
        # Create and accept challenge
        api_client.put(f"{BASE_URL}/api/character/{test_character_1['id']}/location?location_id=village_square")
        api_client.put(f"{BASE_URL}/api/character/{test_character_2['id']}/location?location_id=village_square")
        
        create_res = api_client.post(f"{BASE_URL}/api/pvp/challenge", json={
            "challenger_id": test_character_1["id"],
            "target_id": test_character_2["id"]
        })
        
        if create_res.status_code != 200:
            pytest.skip("Could not create PvP challenge")
        
        session_id = create_res.json()["session"]["id"]
        api_client.post(f"{BASE_URL}/api/pvp/{session_id}/accept?target_id={test_character_2['id']}")
        
        # Try invalid action
        response = api_client.post(f"{BASE_URL}/api/pvp/{session_id}/attack", json={
            "attacker_id": test_character_1["id"],
            "defender_id": test_character_2["id"],
            "action": "invalid_action"
        })
        
        assert response.status_code == 400
        print("✓ Invalid PvP action correctly rejected")


# ==========================================
# Time Phase System Tests
# ==========================================

class TestTimePhaseSystem:
    """Test day/night time phase system"""
    
    def test_get_time_phase(self, api_client):
        """POST /api/time/phase - returns current time phase with danger level"""
        response = api_client.post(f"{BASE_URL}/api/time/phase", json={
            "timezone_offset": 0  # UTC
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "phase" in data
        assert "description" in data
        assert "danger_level" in data
        
        # Danger level should be between 0 and 1
        assert 0 <= data["danger_level"] <= 1.0
        
        # Phase should be one of the valid phases
        valid_phases = ["dawn", "morning", "afternoon", "dusk", "night", "witching_hour", "pre_dawn", "unknown"]
        assert data["phase"] in valid_phases
        
        print(f"✓ Time phase: {data['phase']}, danger: {data['danger_level']}, desc: {data['description'][:50]}...")
    
    def test_get_time_phase_with_offset(self, api_client):
        """POST /api/time/phase - works with different timezone offsets"""
        # Test with various offsets
        for offset in [-8, 0, 5, 9]:
            response = api_client.post(f"{BASE_URL}/api/time/phase", json={
                "timezone_offset": offset
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "phase" in data
            print(f"  - Offset {offset:+d}: {data['phase']}")
        
        print("✓ Time phase works with different timezone offsets")
    
    def test_get_all_phases(self, api_client):
        """GET /api/time/phases - returns all phase definitions"""
        response = api_client.get(f"{BASE_URL}/api/time/phases")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have multiple phases defined
        assert len(data) >= 5
        
        # Each phase should have required fields
        for phase_name, phase_data in data.items():
            assert "start_hour" in phase_data
            assert "end_hour" in phase_data
            assert "danger_level" in phase_data
            assert "description" in phase_data
        
        print(f"✓ All phases returned: {list(data.keys())}")


# ==========================================
# Mood-based Dialogue Tests
# ==========================================

class TestMoodBasedDialogue:
    """Test AI villager mood-based dialogue system"""
    
    def test_get_villager_dialogue_basic(self, api_client, test_villager, test_user):
        """GET /api/villagers/{id}/dialogue - get mood-based dialogue"""
        if not test_villager or not test_user:
            pytest.skip("Test villager or user not created")
        
        villager_id = test_villager["id"]
        player_id = test_user["id"]
        
        response = api_client.get(
            f"{BASE_URL}/api/villagers/{villager_id}/dialogue?player_id={player_id}&dialogue_type=greeting"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "villager_name" in data
        assert "mood" in data
        assert "dialogue" in data
        assert "dialogue_tone" in data
        
        # Dialogue should not be empty
        assert len(data["dialogue"]) > 0
        
        print(f"✓ Dialogue received - Mood: {data['mood']}, Tone: {data['dialogue_tone']}")
        print(f"  Dialogue: '{data['dialogue'][:60]}...'")
    
    def test_get_villager_dialogue_types(self, api_client, test_villager, test_user):
        """GET /api/villagers/{id}/dialogue - test different dialogue types"""
        if not test_villager or not test_user:
            pytest.skip("Test villager or user not created")
        
        villager_id = test_villager["id"]
        player_id = test_user["id"]
        
        dialogue_types = ["greeting", "trade", "farewell"]
        
        for dtype in dialogue_types:
            response = api_client.get(
                f"{BASE_URL}/api/villagers/{villager_id}/dialogue?player_id={player_id}&dialogue_type={dtype}"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "dialogue" in data
            assert len(data["dialogue"]) > 0
            print(f"  - {dtype}: '{data['dialogue'][:40]}...'")
        
        print("✓ All dialogue types return valid responses")
    
    def test_dialogue_returns_trade_info(self, api_client, test_villager, test_user):
        """GET /api/villagers/{id}/dialogue - should return trade availability"""
        if not test_villager or not test_user:
            pytest.skip("Test villager or user not created")
        
        villager_id = test_villager["id"]
        player_id = test_user["id"]
        
        response = api_client.get(
            f"{BASE_URL}/api/villagers/{villager_id}/dialogue?player_id={player_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include trade-related fields
        assert "will_trade" in data
        assert "trade_modifier" in data
        
        print(f"✓ Trade info: will_trade={data['will_trade']}, modifier={data['trade_modifier']}")
    
    def test_villager_not_found(self, api_client, test_user):
        """GET /api/villagers/{id}/dialogue - returns 404 for non-existent villager"""
        if not test_user:
            pytest.skip("Test user not created")
        
        response = api_client.get(
            f"{BASE_URL}/api/villagers/nonexistent-villager-id/dialogue?player_id={test_user['id']}"
        )
        
        assert response.status_code == 404
        print("✓ Non-existent villager returns 404")


# ==========================================
# Integration Tests
# ==========================================

class TestBacklogIntegration:
    """Integration tests for backlog features"""
    
    def test_full_pvp_combat_flow(self, api_client, test_character_1, test_character_2):
        """Full PvP flow: challenge -> accept -> attacks -> victory"""
        if not test_character_1 or not test_character_2:
            pytest.skip("Test characters not created")
        
        # Setup: same location, reset health
        api_client.put(f"{BASE_URL}/api/character/{test_character_1['id']}/location?location_id=village_square")
        api_client.put(f"{BASE_URL}/api/character/{test_character_2['id']}/location?location_id=village_square")
        
        # 1. Create challenge
        challenge_res = api_client.post(f"{BASE_URL}/api/pvp/challenge", json={
            "challenger_id": test_character_1["id"],
            "target_id": test_character_2["id"]
        })
        assert challenge_res.status_code == 200
        session_id = challenge_res.json()["session"]["id"]
        print("  1. Challenge created")
        
        # 2. Accept challenge
        accept_res = api_client.post(
            f"{BASE_URL}/api/pvp/{session_id}/accept?target_id={test_character_2['id']}"
        )
        assert accept_res.status_code == 200
        print("  2. Challenge accepted")
        
        # 3. Check active session
        active_res = api_client.get(f"{BASE_URL}/api/pvp/active/{test_character_1['id']}")
        assert active_res.status_code == 200
        assert active_res.json()["active"] == True
        print("  3. Active session confirmed")
        
        # 4. Execute multiple attacks (use heavy attack for more damage)
        attacks_made = 0
        victory = False
        
        for _ in range(20):  # Max 20 attacks
            attack_res = api_client.post(f"{BASE_URL}/api/pvp/{session_id}/attack", json={
                "attacker_id": test_character_1["id"],
                "defender_id": test_character_2["id"],
                "action": "heavy_attack"
            })
            
            if attack_res.status_code == 400:
                # Not enough stamina, switch to normal attack
                attack_res = api_client.post(f"{BASE_URL}/api/pvp/{session_id}/attack", json={
                    "attacker_id": test_character_1["id"],
                    "defender_id": test_character_2["id"],
                    "action": "attack"
                })
            
            if attack_res.status_code != 200:
                break
            
            attacks_made += 1
            data = attack_res.json()
            
            if data.get("victory"):
                victory = True
                print(f"  4. Victory after {attacks_made} attacks! Winner: {data['winner']}")
                break
        
        if not victory:
            print(f"  4. Combat ongoing after {attacks_made} attacks (health/stamina limits)")
        
        print("✓ Full PvP combat flow completed")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup(api_client, request):
    """Cleanup test data after all tests complete"""
    def cleanup_test_data():
        # Clean up test users
        try:
            users = api_client.get(f"{BASE_URL}/api/users").json()
            for user in users:
                if user.get("username", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/users/{user['id']}")
        except:
            pass
        
        # Clean up test villagers
        try:
            villagers = api_client.get(f"{BASE_URL}/api/villagers").json()
            for v in villagers:
                if v.get("name", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/villagers/{v['id']}")
        except:
            pass
    
    request.addfinalizer(cleanup_test_data)
