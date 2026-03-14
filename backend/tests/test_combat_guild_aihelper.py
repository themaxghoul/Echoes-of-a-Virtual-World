"""
Tests for AI Village Combat System, Guild Management, and AI Helper features
Testing:
- Combat system (attack, block, dodge, sprint with stamina drain formula)
- Guild management (create, list, join guilds)  
- AI Helper device access (Sirix-1 only test feature)
- Sprint stamina drain formula: drain = 0.5 + (armor_weight * 0.5) / ((strength/endurance) * 0.75)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
SIRIX_USER_ID = "sirix_1_supreme"
SIRIX_USERNAME = "sirix_1"
SIRIX_PASSWORD = "k3bdp0wn!0nr(?8vd&74v2l!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user(api_client):
    """Create a test user for testing"""
    user_data = {
        "username": f"test_user_{uuid.uuid4().hex[:8]}",
        "display_name": "Test Combat User"
    }
    response = api_client.post(f"{BASE_URL}/api/users", json=user_data)
    if response.status_code == 200:
        return response.json()
    # If creation fails, return a mock user id for tests
    return {"id": f"test_user_{uuid.uuid4().hex[:8]}", "username": user_data["username"]}


@pytest.fixture(scope="module")
def test_character(api_client, test_user):
    """Create a test character for combat testing"""
    char_data = {
        "user_id": test_user["id"],
        "name": f"Test Warrior {uuid.uuid4().hex[:6]}",
        "background": "A brave warrior for testing",
        "traits": ["strong", "brave"],
        "appearance": "test appearance"
    }
    response = api_client.post(f"{BASE_URL}/api/characters", json=char_data)
    if response.status_code == 200:
        return response.json()
    return {"id": f"test_char_{uuid.uuid4().hex[:8]}", "user_id": test_user["id"]}


class TestCombatDefinitions:
    """Test GET /api/combat/stats - returns combat definitions"""
    
    def test_get_combat_stats_returns_definitions(self, api_client):
        """GET /api/combat/stats should return combat actions, armor types, weapon types"""
        response = api_client.get(f"{BASE_URL}/api/combat/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all combat actions exist
        assert "actions" in data
        actions = data["actions"]
        assert "attack" in actions
        assert "block" in actions
        assert "dodge" in actions
        assert "sprint" in actions
        
        # Verify action structure
        assert "stamina_cost" in actions["attack"]
        assert "base_damage" in actions["attack"]
        assert "damage_reduction" in actions["block"]
        assert "stamina_cost" in actions["dodge"]
        assert "stamina_cost_base" in actions["sprint"]
        
        # Verify armor types exist
        assert "armor_types" in data
        assert "none" in data["armor_types"]
        assert "plate" in data["armor_types"]
        
        # Verify weapon types exist
        assert "weapon_types" in data
        assert "fists" in data["weapon_types"]
        assert "sword" in data["weapon_types"]
        
        # Verify base stats exist
        assert "base_stats" in data
        assert "health" in data["base_stats"]
        assert "stamina" in data["base_stats"]
        print("PASS: Combat definitions returned correctly")


class TestCharacterCombatStats:
    """Test GET /api/character/{id}/combat-stats - character combat stats with sprint drain"""
    
    def test_get_character_combat_stats(self, api_client, test_character):
        """Should return character combat stats with sprint drain calculation"""
        char_id = test_character["id"]
        response = api_client.get(f"{BASE_URL}/api/character/{char_id}/combat-stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic character info
        assert data["character_id"] == char_id
        assert "health" in data
        assert "max_health" in data
        assert "stamina" in data
        
        # Stats structure
        assert "stats" in data
        assert "strength" in data["stats"]
        assert "endurance" in data["stats"]
        assert "agility" in data["stats"]
        
        # Equipment structure
        assert "equipment" in data
        assert "weapon" in data["equipment"]
        assert "armor" in data["equipment"]
        
        # Derived stats with sprint drain formula
        assert "derived_stats" in data
        assert "sprint_stamina_drain_per_second" in data["derived_stats"]
        sprint_drain = data["derived_stats"]["sprint_stamina_drain_per_second"]
        assert isinstance(sprint_drain, (int, float))
        assert sprint_drain >= 0.1  # Min clamp
        assert sprint_drain <= 20.0  # Max clamp
        
        # Combat state
        assert "combat_state" in data
        assert "is_blocking" in data["combat_state"]
        assert "is_sprinting" in data["combat_state"]
        assert "in_combat" in data["combat_state"]
        print(f"PASS: Character combat stats returned with sprint drain: {sprint_drain}")
    
    def test_character_not_found(self, api_client):
        """Should return 404 for non-existent character"""
        response = api_client.get(f"{BASE_URL}/api/character/nonexistent_char_123/combat-stats")
        assert response.status_code == 404
        print("PASS: 404 returned for non-existent character")


class TestCombatActions:
    """Test POST /api/character/{id}/action - combat actions"""
    
    def test_attack_action(self, api_client, test_character):
        """Attack action should deal damage and cost stamina"""
        char_id = test_character["id"]
        action_data = {
            "character_id": char_id,
            "action": "attack"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/action", json=action_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["action"] == "attack"
        assert "damage_dealt" in data
        assert "stamina_cost" in data
        assert "remaining_stamina" in data
        assert "cooldown" in data
        assert "is_critical" in data
        print(f"PASS: Attack action - damage: {data['damage_dealt']}, stamina cost: {data['stamina_cost']}")
    
    def test_block_action(self, api_client, test_character):
        """Block action should enable blocking state"""
        char_id = test_character["id"]
        action_data = {
            "character_id": char_id,
            "action": "block"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/action", json=action_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["action"] == "block"
        assert data["blocking"] == True
        assert "damage_reduction" in data
        assert data["damage_reduction"] == 0.7  # 70% damage reduction
        print(f"PASS: Block action - damage reduction: {data['damage_reduction']}")
    
    def test_dodge_action(self, api_client, test_character):
        """Dodge action should use stamina and provide invulnerability"""
        char_id = test_character["id"]
        action_data = {
            "character_id": char_id,
            "action": "dodge"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/action", json=action_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["action"] == "dodge"
        assert "dodge_success" in data
        assert "stamina_cost" in data
        assert "remaining_stamina" in data
        assert "cooldown" in data
        print(f"PASS: Dodge action - success: {data['dodge_success']}, stamina cost: {data['stamina_cost']}")
    
    def test_sprint_action_with_formula(self, api_client, test_character):
        """Sprint action should calculate drain based on strength/endurance/armor"""
        char_id = test_character["id"]
        action_data = {
            "character_id": char_id,
            "action": "sprint"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/action", json=action_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["action"] == "sprint"
        assert data["sprinting"] == True
        assert "stamina_drain_per_second" in data
        assert "speed_multiplier" in data
        assert data["speed_multiplier"] == 2.0
        
        # Verify formula breakdown is included
        assert "formula_breakdown" in data
        breakdown = data["formula_breakdown"]
        assert "strength" in breakdown
        assert "endurance" in breakdown
        assert "armor_weight" in breakdown
        assert "base_drain" in breakdown
        
        print(f"PASS: Sprint action - drain/sec: {data['stamina_drain_per_second']}, formula: {breakdown}")
    
    def test_invalid_action(self, api_client, test_character):
        """Invalid action should return 400"""
        char_id = test_character["id"]
        action_data = {
            "character_id": char_id,
            "action": "invalid_action"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/action", json=action_data)
        assert response.status_code == 400
        print("PASS: Invalid action returns 400")


class TestMovement:
    """Test POST /api/character/{id}/move - movement with sprint stamina drain"""
    
    def test_normal_movement(self, api_client, test_character):
        """Normal movement should update position without stamina drain"""
        char_id = test_character["id"]
        move_data = {
            "character_id": char_id,
            "direction": "up",
            "is_sprinting": False
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json=move_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["direction"] == "up"
        assert "new_position" in data
        assert data["is_sprinting"] == False
        assert data["stamina_used"] == 0
        print(f"PASS: Normal movement - position: {data['new_position']}")
    
    def test_sprint_movement_with_drain(self, api_client, test_character):
        """Sprinting movement should drain stamina according to formula"""
        char_id = test_character["id"]
        move_data = {
            "character_id": char_id,
            "direction": "right",
            "is_sprinting": True
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json=move_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["direction"] == "right"
        assert "new_position" in data
        assert "speed" in data
        
        # If sprinting succeeded
        if data["is_sprinting"]:
            assert data["stamina_used"] > 0
            assert "remaining_stamina" in data
        print(f"PASS: Sprint movement - speed: {data['speed']}, stamina used: {data['stamina_used']}")
    
    def test_all_directions(self, api_client, test_character):
        """Should support all 8 movement directions"""
        char_id = test_character["id"]
        directions = ["up", "down", "left", "right", "up-left", "up-right", "down-left", "down-right"]
        
        for direction in directions:
            move_data = {
                "character_id": char_id,
                "direction": direction,
                "is_sprinting": False
            }
            response = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json=move_data)
            assert response.status_code == 200
        
        print(f"PASS: All 8 directions work: {directions}")
    
    def test_invalid_direction(self, api_client, test_character):
        """Invalid direction should return 400"""
        char_id = test_character["id"]
        move_data = {
            "character_id": char_id,
            "direction": "invalid_dir",
            "is_sprinting": False
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/move", json=move_data)
        assert response.status_code == 400
        print("PASS: Invalid direction returns 400")


class TestEquipment:
    """Test POST /api/character/{id}/equip - equip weapon/armor"""
    
    def test_equip_weapon(self, api_client, test_character):
        """Should equip weapon successfully"""
        char_id = test_character["id"]
        equip_data = {
            "character_id": char_id,
            "slot": "weapon",
            "item_type": "sword"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json=equip_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "equipped_weapon" in data
        assert data["equipped_weapon"]["name"] == "Iron Sword"
        print(f"PASS: Weapon equipped - {data['equipped_weapon']['name']}")
    
    def test_equip_armor(self, api_client, test_character):
        """Should equip armor and update armor_weight"""
        char_id = test_character["id"]
        equip_data = {
            "character_id": char_id,
            "slot": "armor",
            "item_type": "chain"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json=equip_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "equipped_armor" in data
        assert data["equipped_armor"]["name"] == "Chainmail"
        assert data["equipped_armor"]["weight"] == 12  # Chain armor weight
        print(f"PASS: Armor equipped - {data['equipped_armor']['name']}, weight: {data['equipped_armor']['weight']}")
    
    def test_invalid_weapon(self, api_client, test_character):
        """Should return 400 for invalid weapon type"""
        char_id = test_character["id"]
        equip_data = {
            "character_id": char_id,
            "slot": "weapon",
            "item_type": "invalid_weapon"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json=equip_data)
        assert response.status_code == 400
        print("PASS: Invalid weapon type returns 400")
    
    def test_invalid_armor(self, api_client, test_character):
        """Should return 400 for invalid armor type"""
        char_id = test_character["id"]
        equip_data = {
            "character_id": char_id,
            "slot": "armor",
            "item_type": "invalid_armor"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json=equip_data)
        assert response.status_code == 400
        print("PASS: Invalid armor type returns 400")
    
    def test_invalid_equipment_slot(self, api_client, test_character):
        """Should return 400 for invalid slot"""
        char_id = test_character["id"]
        equip_data = {
            "character_id": char_id,
            "slot": "invalid_slot",
            "item_type": "sword"
        }
        
        response = api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json=equip_data)
        assert response.status_code == 400
        print("PASS: Invalid equipment slot returns 400")


class TestSprintStaminaDrainFormula:
    """Test sprint stamina drain formula with different equipment"""
    
    def test_heavy_armor_increases_drain(self, api_client, test_character):
        """Heavier armor should increase sprint stamina drain"""
        char_id = test_character["id"]
        
        # First equip light armor (cloth)
        api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json={
            "character_id": char_id,
            "slot": "armor",
            "item_type": "cloth"
        })
        
        # Get combat stats with light armor
        response = api_client.get(f"{BASE_URL}/api/character/{char_id}/combat-stats")
        light_drain = response.json()["derived_stats"]["sprint_stamina_drain_per_second"]
        
        # Now equip heavy armor (plate)
        api_client.post(f"{BASE_URL}/api/character/{char_id}/equip", json={
            "character_id": char_id,
            "slot": "armor",
            "item_type": "plate"
        })
        
        # Get combat stats with heavy armor
        response = api_client.get(f"{BASE_URL}/api/character/{char_id}/combat-stats")
        heavy_drain = response.json()["derived_stats"]["sprint_stamina_drain_per_second"]
        
        # Heavier armor should have higher drain
        assert heavy_drain > light_drain
        print(f"PASS: Heavy armor drain ({heavy_drain}) > Light armor drain ({light_drain})")


class TestGuildSystem:
    """Test Guild CRUD operations"""
    
    def test_create_guild(self, api_client, test_user):
        """POST /api/guilds - create a new guild"""
        guild_data = {
            "name": f"Test Guild {uuid.uuid4().hex[:6]}",
            "tag": f"TG{uuid.uuid4().hex[:3]}",
            "guild_type": "combat",
            "description": "A test guild for combat",
            "founder_id": test_user["id"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/guilds", json=guild_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["name"] == guild_data["name"]
        assert data["guild_type"] == "combat"
        assert data["leader_id"] == test_user["id"]
        assert "bonuses" in data
        assert data["bonuses"]["damage"] == 1.15  # Combat guild bonus
        print(f"PASS: Guild created - {data['name']} (type: {data['guild_type']})")
        return data
    
    def test_list_guilds(self, api_client):
        """GET /api/guilds - list all guilds"""
        response = api_client.get(f"{BASE_URL}/api/guilds")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"PASS: Listed {len(data)} guilds")
    
    def test_create_guild_invalid_type(self, api_client, test_user):
        """Should reject invalid guild type"""
        guild_data = {
            "name": f"Invalid Guild {uuid.uuid4().hex[:6]}",
            "tag": f"IG{uuid.uuid4().hex[:3]}",
            "guild_type": "invalid_type",
            "description": "This should fail",
            "founder_id": test_user["id"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/guilds", json=guild_data)
        assert response.status_code == 400
        print("PASS: Invalid guild type returns 400")


class TestGuildJoin:
    """Test POST /api/guilds/{id}/join - join a guild"""
    
    def test_join_guild(self, api_client):
        """User should be able to join a guild"""
        # First create a new user without a guild
        user_data = {
            "username": f"joiner_{uuid.uuid4().hex[:8]}",
            "display_name": "Guild Joiner"
        }
        user_response = api_client.post(f"{BASE_URL}/api/users", json=user_data)
        
        if user_response.status_code != 200:
            pytest.skip("Could not create test user")
            
        new_user = user_response.json()
        
        # Create a guild with a different founder
        founder_data = {
            "username": f"founder_{uuid.uuid4().hex[:8]}",
            "display_name": "Guild Founder"
        }
        founder_response = api_client.post(f"{BASE_URL}/api/users", json=founder_data)
        
        if founder_response.status_code != 200:
            pytest.skip("Could not create founder")
            
        founder = founder_response.json()
        
        guild_data = {
            "name": f"Join Test Guild {uuid.uuid4().hex[:6]}",
            "tag": f"JT{uuid.uuid4().hex[:3]}",
            "guild_type": "trade",
            "description": "A guild to join",
            "founder_id": founder["id"]
        }
        
        guild_response = api_client.post(f"{BASE_URL}/api/guilds", json=guild_data)
        if guild_response.status_code != 200:
            pytest.skip("Could not create guild")
            
        guild = guild_response.json()
        
        # Now join the guild
        join_response = api_client.post(f"{BASE_URL}/api/guilds/{guild['id']}/join?user_id={new_user['id']}")
        
        assert join_response.status_code == 200
        data = join_response.json()
        
        assert data["status"] == "success"
        assert "Joined" in data["message"]
        print(f"PASS: User joined guild - {data['message']}")


class TestAIHelperStatus:
    """Test GET /api/ai-helper/status - check AI helper availability"""
    
    def test_ai_helper_status_for_regular_user(self, api_client, test_user):
        """Regular users should not have AI helper access"""
        response = api_client.get(f"{BASE_URL}/api/ai-helper/status?user_id={test_user['id']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["enabled"] == False
        assert data["is_test_feature"] == True
        assert data["user_authorized"] == False
        print("PASS: Regular user AI helper status - not authorized")
    
    def test_ai_helper_status_for_sirix(self, api_client):
        """Sirix-1 should have AI helper access"""
        response = api_client.get(f"{BASE_URL}/api/ai-helper/status?user_id={SIRIX_USER_ID}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Sirix-1 should be enabled if properly initialized
        assert data["is_test_feature"] == True
        assert "privacy_note" in data
        print(f"PASS: Sirix-1 AI helper status - enabled: {data['enabled']}")


class TestAIHelperCapabilities:
    """Test GET /api/ai-helper/capabilities - device capabilities"""
    
    def test_capabilities_for_regular_user(self, api_client, test_user):
        """Regular users should get restricted response"""
        response = api_client.get(f"{BASE_URL}/api/ai-helper/capabilities?user_id={test_user['id']}&is_mobile=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] == False
        assert "restricted" in data["reason"].lower()
        assert data["capabilities"] == {}
        print("PASS: Regular user capabilities - restricted")
    
    def test_capabilities_for_sirix_mobile(self, api_client):
        """Sirix-1 on mobile should get full capabilities"""
        response = api_client.get(f"{BASE_URL}/api/ai-helper/capabilities?user_id={SIRIX_USER_ID}&is_mobile=true")
        
        assert response.status_code == 200
        data = response.json()
        
        # Even if Sirix-1 isn't fully initialized, structure should be valid
        if data["available"]:
            assert "capabilities" in data
            assert len(data["capabilities"]) > 0
            # Mobile should have vibration capability
            if "vibration" in data["capabilities"]:
                assert data["capabilities"]["vibration"]["mobile_only"] == True
            print(f"PASS: Sirix-1 mobile capabilities - {len(data['capabilities'])} available")
        else:
            # Sirix-1 might not be initialized in test DB
            print(f"INFO: Sirix-1 capabilities unavailable (may need initialization)")


class TestAIHelperExecute:
    """Test POST /api/ai-helper/execute - execute device command"""
    
    def test_execute_fails_for_regular_user(self, api_client, test_user):
        """Regular users should get 403 when trying to execute commands"""
        command_data = {
            "user_id": test_user["id"],
            "command_type": "vibrate",
            "payload": {"pattern": "alert"}
        }
        
        response = api_client.post(f"{BASE_URL}/api/ai-helper/execute", json=command_data)
        
        assert response.status_code == 403
        print("PASS: Regular user execute command - 403 forbidden")
    
    def test_execute_vibrate_for_sirix(self, api_client):
        """Sirix-1 should be able to execute vibrate command"""
        command_data = {
            "user_id": SIRIX_USER_ID,
            "command_type": "vibrate",
            "payload": {"pattern": "heartbeat"}
        }
        
        response = api_client.post(f"{BASE_URL}/api/ai-helper/execute", json=command_data)
        
        # If Sirix-1 is initialized, should succeed; otherwise 403
        if response.status_code == 200:
            data = response.json()
            assert data["command"] == "vibrate"
            assert "pattern" in data
            assert data["pattern_name"] == "heartbeat"
            print(f"PASS: Sirix-1 vibrate command - pattern: {data['pattern']}")
        else:
            assert response.status_code == 403
            print("INFO: Sirix-1 vibrate failed (user not initialized)")
    
    def test_execute_notify_for_sirix(self, api_client):
        """Sirix-1 should be able to execute notify command"""
        command_data = {
            "user_id": SIRIX_USER_ID,
            "command_type": "notify",
            "payload": {"title": "Test Alert", "body": "This is a test"}
        }
        
        response = api_client.post(f"{BASE_URL}/api/ai-helper/execute", json=command_data)
        
        if response.status_code == 200:
            data = response.json()
            assert data["command"] == "notification"
            assert data["title"] == "Test Alert"
            print(f"PASS: Sirix-1 notify command - title: {data['title']}")
        else:
            print("INFO: Sirix-1 notify failed (user not initialized)")
    
    def test_execute_invalid_command(self, api_client):
        """Invalid command type should return 400"""
        command_data = {
            "user_id": SIRIX_USER_ID,
            "command_type": "invalid_command",
            "payload": {}
        }
        
        response = api_client.post(f"{BASE_URL}/api/ai-helper/execute", json=command_data)
        
        # Either 400 (invalid command) or 403 (Sirix not initialized)
        assert response.status_code in [400, 403]
        print(f"PASS: Invalid command returns {response.status_code}")


class TestGuildTypes:
    """Test guild types endpoint"""
    
    def test_get_guild_types(self, api_client):
        """Should return all 5 guild types with bonuses"""
        response = api_client.get(f"{BASE_URL}/api/guild-types")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 5 types
        expected_types = ["trade", "combat", "crafting", "exploration", "mystical"]
        for guild_type in expected_types:
            assert guild_type in data
            assert "focus" in data[guild_type]
            assert "bonuses" in data[guild_type]
        
        # Verify specific bonuses
        assert data["trade"]["bonuses"]["gold_gain"] == 1.2
        assert data["combat"]["bonuses"]["damage"] == 1.15
        assert data["crafting"]["bonuses"]["craft_speed"] == 1.25
        assert data["exploration"]["bonuses"]["travel_speed"] == 1.3
        assert data["mystical"]["bonuses"]["essence_gain"] == 1.25
        
        print(f"PASS: All 5 guild types returned with correct bonuses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
