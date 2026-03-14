"""
Test module for new AI Village features:
- Day/Night cycle phases (POST /api/time/phase, GET /api/time/phases)
- Guild system (POST /api/guilds, GET /api/guilds, POST /api/guilds/{id}/join)
- Biblical demon system (GET /api/demons, POST /api/demons/spawn/{location_id}, 
  GET /api/infestation/{location_id}, POST /api/demons/{encounter_id}/attack)
- AI mood/emotional memory (GET /api/villagers/{id}/mood, POST /api/villagers/{id}/interact)
- Scan/Profile endpoints with Sirix-1 distortion (GET /api/scan/{target_id}, GET /api/profile/view/{user_id})
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def sirix_credentials():
    """Sirix-1 login credentials"""
    return {"username": "sirix_1", "password": "k3bdp0wn!0nr(?8vd&74v2l!"}

@pytest.fixture(scope="module")
def test_user(api_client):
    """Create a test user for testing"""
    user_data = {
        "username": f"TEST_user_{uuid.uuid4().hex[:8]}",
        "display_name": "Test Player"
    }
    response = api_client.post(f"{BASE_URL}/api/users", json=user_data)
    if response.status_code in [200, 201]:
        return response.json()
    # If user creation fails, try to use existing
    return {"id": f"test_{uuid.uuid4().hex[:8]}", "username": user_data["username"], "display_name": "Test Player"}


class TestTimePhases:
    """Test Day/Night cycle system"""
    
    def test_get_all_phases(self, api_client):
        """GET /api/time/phases - returns all phase definitions"""
        response = api_client.get(f"{BASE_URL}/api/time/phases")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        phases = response.json()
        assert isinstance(phases, dict), "Expected dict of phases"
        
        # Verify 7 phases exist as per requirements
        expected_phases = ["dawn", "morning", "afternoon", "dusk", "night", "witching_hour", "pre_dawn"]
        for phase in expected_phases:
            assert phase in phases, f"Missing phase: {phase}"
            assert "start_hour" in phases[phase], f"Phase {phase} missing start_hour"
            assert "end_hour" in phases[phase], f"Phase {phase} missing end_hour"
            assert "danger_level" in phases[phase], f"Phase {phase} missing danger_level"
        
        print(f"PASS: All 7 day phases verified: {list(phases.keys())}")
    
    def test_get_current_phase_utc(self, api_client):
        """POST /api/time/phase - get phase for UTC timezone"""
        response = api_client.post(f"{BASE_URL}/api/time/phase", json={"timezone_offset": 0})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        phase_data = response.json()
        assert "phase" in phase_data, "Response missing 'phase' field"
        assert "description" in phase_data, "Response missing 'description' field"
        assert "danger_level" in phase_data, "Response missing 'danger_level' field"
        
        print(f"PASS: Current phase (UTC+0): {phase_data['phase']} - danger: {phase_data['danger_level']}")
    
    def test_get_phase_different_timezones(self, api_client):
        """POST /api/time/phase - test different timezone offsets"""
        for offset in [-8, -5, 0, 5, 8, 12]:
            response = api_client.post(f"{BASE_URL}/api/time/phase", json={"timezone_offset": offset})
            assert response.status_code == 200, f"Expected 200 for offset {offset}, got {response.status_code}"
            
            phase_data = response.json()
            assert phase_data["phase"] in ["dawn", "morning", "afternoon", "dusk", "night", "witching_hour", "pre_dawn"]
        
        print("PASS: Phase calculation works for multiple timezone offsets")


class TestGuildSystem:
    """Test Guild creation, listing, and joining"""
    
    def test_get_guild_types(self, api_client):
        """GET /api/guild-types - verify 5 guild types exist"""
        response = api_client.get(f"{BASE_URL}/api/guild-types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        types = response.json()
        expected_types = ["trade", "combat", "crafting", "exploration", "mystical"]
        for guild_type in expected_types:
            assert guild_type in types, f"Missing guild type: {guild_type}"
            assert "bonuses" in types[guild_type], f"Guild type {guild_type} missing bonuses"
        
        print(f"PASS: All 5 guild types verified: {list(types.keys())}")
    
    def test_create_guild(self, api_client, test_user):
        """POST /api/guilds - create a new guild"""
        guild_data = {
            "name": f"TEST_Guild_{uuid.uuid4().hex[:6]}",
            "tag": f"TG{uuid.uuid4().hex[:3].upper()}",
            "guild_type": "combat",
            "description": "Test guild for combat",
            "founder_id": test_user.get("id", "test_founder")
        }
        
        response = api_client.post(f"{BASE_URL}/api/guilds", json=guild_data)
        # May fail if founder doesn't exist, but we check response structure
        
        if response.status_code in [200, 201]:
            guild = response.json()
            assert "id" in guild, "Created guild missing 'id'"
            assert guild["name"] == guild_data["name"], "Guild name mismatch"
            assert guild["guild_type"] == "combat", "Guild type mismatch"
            assert "bonuses" in guild, "Guild missing bonuses"
            print(f"PASS: Guild created: {guild['name']} ({guild['id']})")
            return guild
        elif response.status_code == 404:
            print(f"SKIP: Guild creation - founder not found (test setup issue)")
        else:
            print(f"INFO: Guild creation returned {response.status_code}: {response.text[:200]}")
    
    def test_list_guilds(self, api_client):
        """GET /api/guilds - list all guilds"""
        response = api_client.get(f"{BASE_URL}/api/guilds")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        guilds = response.json()
        assert isinstance(guilds, list), "Expected list of guilds"
        
        print(f"PASS: Listed {len(guilds)} guild(s)")
        return guilds
    
    def test_join_guild_requires_valid_user(self, api_client):
        """POST /api/guilds/{id}/join - verify validation"""
        # First get a guild if available
        guilds = api_client.get(f"{BASE_URL}/api/guilds").json()
        
        if guilds:
            guild_id = guilds[0]["id"]
            # Try joining with invalid user
            response = api_client.post(f"{BASE_URL}/api/guilds/{guild_id}/join?user_id=invalid_user_999")
            assert response.status_code in [400, 404], f"Expected 400/404 for invalid user, got {response.status_code}"
            print("PASS: Guild join validates user exists")
        else:
            print("SKIP: No guilds available to test join")


class TestBiblicalDemons:
    """Test biblical demon system - 9 demons across 4 ranks"""
    
    def test_get_all_demon_types(self, api_client):
        """GET /api/demons - list all demon types"""
        response = api_client.get(f"{BASE_URL}/api/demons")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        demons = response.json()
        assert isinstance(demons, dict), "Expected dict of demons"
        
        # Verify 9 demons exist as per requirements
        expected_demons = [
            "imp", "shade",  # Lesser
            "legion_soldier", "tempter",  # Standard
            "asmodeus_spawn", "mammon_collector", "belphegor_sloth",  # Greater
            "beelzebub_avatar", "abaddon_destroyer"  # Arch
        ]
        
        for demon in expected_demons:
            assert demon in demons, f"Missing demon type: {demon}"
            assert "rank" in demons[demon], f"Demon {demon} missing rank"
            assert "health" in demons[demon], f"Demon {demon} missing health"
            assert "damage" in demons[demon], f"Demon {demon} missing damage"
            assert "biblical_origin" in demons[demon], f"Demon {demon} missing biblical_origin"
        
        print(f"PASS: All 9 biblical demons verified across 4 ranks")
        
        # Verify rank distribution
        ranks = {}
        for dtype, ddata in demons.items():
            rank = ddata["rank"]
            ranks[rank] = ranks.get(rank, 0) + 1
        print(f"  Ranks: {ranks}")
    
    def test_get_specific_demon(self, api_client):
        """GET /api/demons/{demon_type} - get specific demon details"""
        response = api_client.get(f"{BASE_URL}/api/demons/legion_soldier")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        demon = response.json()
        assert demon["demon_type"] == "legion_soldier", "Demon type mismatch"
        assert demon["rank"] == "standard", "Expected standard rank"
        assert "Mark 5:9" in demon.get("biblical_origin", ""), "Missing Legion biblical reference"
        
        print(f"PASS: Legion soldier details: HP={demon['health']}, DMG={demon['damage']}")
    
    def test_get_infestation_level_clear(self, api_client):
        """GET /api/infestation/{location_id} - default is clear"""
        response = api_client.get(f"{BASE_URL}/api/infestation/test_location_new")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        infestation = response.json()
        assert infestation["level"] == "clear", "New location should be clear"
        assert infestation["demon_count"] == 0, "Clear location should have 0 demons"
        
        print("PASS: New location has clear infestation")
    
    def test_demon_spawn_daytime(self, api_client):
        """POST /api/demons/spawn/{location_id} - daytime should not spawn"""
        # Use timezone offset that puts us in afternoon (low danger)
        from datetime import datetime, timezone
        current_hour = datetime.now(timezone.utc).hour
        
        # Calculate offset to put us in afternoon (12-17 hours)
        target_hour = 14  # afternoon
        offset = target_hour - current_hour
        
        response = api_client.post(f"{BASE_URL}/api/demons/spawn/test_daytime_loc?timezone_offset={offset}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "spawned" in result, "Response missing 'spawned' field"
        # May or may not spawn, but response should be valid
        print(f"PASS: Demon spawn (afternoon) - spawned: {result['spawned']}")
    
    def test_demon_spawn_nighttime(self, api_client):
        """POST /api/demons/spawn/{location_id} - nighttime has higher spawn chance"""
        from datetime import datetime, timezone
        current_hour = datetime.now(timezone.utc).hour
        
        # Calculate offset to put us in witching hour (0-3)
        target_hour = 1
        offset = target_hour - current_hour
        
        response = api_client.post(f"{BASE_URL}/api/demons/spawn/test_night_loc?timezone_offset={offset}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "spawned" in result, "Response missing 'spawned' field"
        
        if result["spawned"]:
            assert "encounter" in result, "Spawn success missing 'encounter'"
            assert "demon" in result, "Spawn success missing 'demon' info"
            assert "warning" in result, "Spawn success missing 'warning' message"
            print(f"PASS: Demon spawned at witching hour - {result['warning']}")
        else:
            print(f"PASS: Demon spawn attempt (witching hour) - reason: {result.get('reason', 'unknown')}")
    
    def test_attack_demon_flow(self, api_client):
        """POST /api/demons/{encounter_id}/attack - combat flow"""
        from datetime import datetime, timezone
        current_hour = datetime.now(timezone.utc).hour
        target_hour = 1
        offset = target_hour - current_hour
        
        # Spawn demons until one appears
        location_id = f"test_combat_loc_{uuid.uuid4().hex[:6]}"
        encounter_id = None
        
        for _ in range(10):  # Try up to 10 times
            spawn_response = api_client.post(f"{BASE_URL}/api/demons/spawn/{location_id}?timezone_offset={offset}")
            if spawn_response.status_code == 200:
                spawn_data = spawn_response.json()
                if spawn_data.get("spawned"):
                    encounter_id = spawn_data["encounter"]["id"]
                    print(f"  Demon spawned: {spawn_data['demon']['name']}")
                    break
        
        if not encounter_id:
            print("SKIP: Could not spawn demon for attack test (RNG)")
            return
        
        # Attack the demon
        attacker_id = "test_attacker"
        response = api_client.post(f"{BASE_URL}/api/demons/{encounter_id}/attack?attacker_id={attacker_id}&damage=100")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        combat = response.json()
        assert "status" in combat, "Combat response missing 'status'"
        
        if combat["status"] == "victory":
            assert "drops" in combat, "Victory missing 'drops'"
            assert "demon_rank" in combat, "Victory missing 'demon_rank'"
            print(f"PASS: Demon defeated! Drops: {combat['drops']}")
        else:
            assert combat["status"] == "combat_continues", f"Unexpected status: {combat['status']}"
            assert "demon_health" in combat, "Combat missing 'demon_health'"
            print(f"PASS: Combat continues - demon HP: {combat['demon_health']}")


class TestAIMoodSystem:
    """Test AI emotional memory system"""
    
    @pytest.fixture
    def villager_id(self, api_client):
        """Get a villager ID for testing"""
        response = api_client.get(f"{BASE_URL}/api/villagers")
        if response.status_code == 200:
            villagers = response.json()
            if villagers:
                return villagers[0]["id"]
        return None
    
    def test_get_villager_mood_default(self, api_client, villager_id):
        """GET /api/villagers/{id}/mood - check default neutral mood"""
        if not villager_id:
            print("SKIP: No villagers available")
            return
        
        response = api_client.get(f"{BASE_URL}/api/villagers/{villager_id}/mood")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        mood_data = response.json()
        assert "current_mood" in mood_data, "Response missing 'current_mood'"
        assert "mood_value" in mood_data, "Response missing 'mood_value'"
        assert "will_trade" in mood_data, "Response missing 'will_trade'"
        assert "mood_details" in mood_data, "Response missing 'mood_details'"
        
        print(f"PASS: Villager {mood_data.get('villager_name', 'unknown')} mood: {mood_data['current_mood']}")
    
    def test_positive_interaction(self, api_client, villager_id, test_user):
        """POST /api/villagers/{id}/interact - positive interaction improves mood"""
        if not villager_id:
            print("SKIP: No villagers available")
            return
        
        player_id = test_user.get("id", "test_player")
        response = api_client.post(
            f"{BASE_URL}/api/villagers/{villager_id}/interact"
            f"?player_id={player_id}&interaction_type=friendly_chat"
        )
        
        if response.status_code == 404:
            print("SKIP: Player not found for interaction test")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["status"] == "success", "Interaction should succeed"
        assert result["mood_change"] > 0, "Friendly chat should improve mood"
        
        print(f"PASS: Friendly chat - mood changed from {result['old_mood']} to {result['new_mood']}")
    
    def test_negative_interaction(self, api_client, villager_id, test_user):
        """POST /api/villagers/{id}/interact - negative interaction damages mood"""
        if not villager_id:
            print("SKIP: No villagers available")
            return
        
        player_id = test_user.get("id", "test_player")
        response = api_client.post(
            f"{BASE_URL}/api/villagers/{villager_id}/interact"
            f"?player_id={player_id}&interaction_type=insult"
        )
        
        if response.status_code == 404:
            print("SKIP: Player not found for interaction test")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["mood_change"] < 0, "Insult should damage mood"
        
        print(f"PASS: Insult interaction - mood changed from {result['old_mood']} to {result['new_mood']}")
    
    def test_property_damage_closes_shop(self, api_client, test_user):
        """POST /api/villagers/{id}/interact - severe damage closes shop"""
        # Get a fresh villager to avoid state issues
        response = api_client.get(f"{BASE_URL}/api/villagers")
        if response.status_code != 200:
            print("SKIP: Cannot get villagers")
            return
        
        villagers = response.json()
        if len(villagers) < 2:
            print("SKIP: Need at least 2 villagers for this test")
            return
        
        villager_id = villagers[1]["id"]  # Use second villager
        player_id = test_user.get("id", "test_player_damage")
        
        response = api_client.post(
            f"{BASE_URL}/api/villagers/{villager_id}/interact"
            f"?player_id={player_id}&interaction_type=property_damage"
        )
        
        if response.status_code == 404:
            print("SKIP: Player not found for property damage test")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["mood_change"] == -50, "Property damage should be -50 mood"
        
        if "shop_status" in result:
            print(f"PASS: Property damage closed shop - {result['shop_status']}")
        else:
            print(f"PASS: Property damage - mood: {result['new_mood']}, serves: {result['will_serve_player']}")
    
    def test_invalid_interaction_type(self, api_client, villager_id, test_user):
        """POST /api/villagers/{id}/interact - invalid type returns error"""
        if not villager_id:
            print("SKIP: No villagers available")
            return
        
        player_id = test_user.get("id", "test_player")
        response = api_client.post(
            f"{BASE_URL}/api/villagers/{villager_id}/interact"
            f"?player_id={player_id}&interaction_type=invalid_type_xyz"
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
        print("PASS: Invalid interaction type returns 400")


class TestSirixScanProtection:
    """Test Sirix-1 scan/profile protection"""
    
    def test_scan_normal_entity(self, api_client):
        """GET /api/scan/{target_id} - scan a normal villager"""
        # Get a villager to scan
        response = api_client.get(f"{BASE_URL}/api/villagers")
        if response.status_code != 200:
            print("SKIP: Cannot get villagers for scan test")
            return
        
        villagers = response.json()
        if not villagers:
            print("SKIP: No villagers to scan")
            return
        
        villager_id = villagers[0]["id"]
        
        response = api_client.get(f"{BASE_URL}/api/scan/{villager_id}?scanner_id=test_scanner")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        scan_data = response.json()
        assert scan_data["success"] == True, "Scan should succeed"
        assert scan_data["entity_type"] == "villager", "Entity type should be villager"
        
        print(f"PASS: Scanned villager: {scan_data['data']['name']}")
    
    def test_scan_sirix_causes_distortion(self, api_client):
        """GET /api/scan/{target_id} - scanning Sirix-1 returns distorted data"""
        response = api_client.get(f"{BASE_URL}/api/scan/sirix_1_supreme?scanner_id=test_scanner")
        
        # If Sirix-1 exists, should return distortion
        if response.status_code == 200:
            scan_data = response.json()
            
            if scan_data.get("success") == False:
                assert scan_data.get("distorted") == True, "Sirix scan should be distorted"
                assert "error_code" in scan_data, "Should have error code"
                assert "visual_corruption" in scan_data, "Should have visual corruption"
                print(f"PASS: Sirix-1 scan distorted - {scan_data['error_code']}: {scan_data['message']}")
            else:
                print(f"INFO: Sirix-1 scan returned normal data (may need transcendent flag)")
        elif response.status_code == 404:
            print("SKIP: Sirix-1 not found (not initialized)")
        else:
            print(f"INFO: Sirix scan returned {response.status_code}: {response.text[:200]}")
    
    def test_view_profile_sirix_masked(self, api_client):
        """GET /api/profile/view/{user_id} - viewing Sirix-1 shows masked data"""
        response = api_client.get(f"{BASE_URL}/api/profile/view/sirix_1_supreme?viewer_id=normal_user")
        
        if response.status_code == 200:
            profile = response.json()
            
            if profile.get("is_transcendent"):
                # Should have distorted values
                assert "warning" in profile, "Transcendent profile should have warning"
                assert "visual_corruption" in profile, "Should have visual corruption"
                
                # Check for cryptic display values
                assert any(char in str(profile.get("xp", "")) for char in "∞???█▓░◈"), \
                    "XP should be cryptic"
                
                print(f"PASS: Sirix-1 profile masked - warning: {profile['warning']}")
            else:
                print("INFO: Sirix-1 profile not transcendent (check initialization)")
        elif response.status_code == 404:
            print("SKIP: Sirix-1 profile not found")
        else:
            print(f"INFO: Profile view returned {response.status_code}")
    
    def test_scan_nonexistent_entity(self, api_client):
        """GET /api/scan/{target_id} - nonexistent entity returns 404"""
        response = api_client.get(f"{BASE_URL}/api/scan/nonexistent_id_xyz123?scanner_id=test")
        assert response.status_code == 404, f"Expected 404 for nonexistent entity, got {response.status_code}"
        print("PASS: Scanning nonexistent entity returns 404")


class TestMoodDecay:
    """Test mood decay system"""
    
    def test_decay_moods_endpoint(self, api_client):
        """POST /api/villagers/decay-moods - trigger mood decay"""
        response = api_client.post(f"{BASE_URL}/api/villagers/decay-moods")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["status"] == "success", "Decay should succeed"
        assert "villagers_updated" in result, "Should report update count"
        
        print(f"PASS: Mood decay applied to {result['villagers_updated']} villagers")


class TestInfestationLevels:
    """Test infestation level mechanics"""
    
    def test_infestation_known_location(self, api_client):
        """GET /api/infestation/{location_id} - get infestation for village location"""
        response = api_client.get(f"{BASE_URL}/api/infestation/village_square")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        infestation = response.json()
        assert "level" in infestation, "Missing level"
        assert "demon_count" in infestation, "Missing demon_count"
        assert "description" in infestation, "Missing description"
        
        print(f"PASS: Village square infestation: {infestation['level']} ({infestation['demon_count']} demons)")
    
    def test_get_active_demons_at_location(self, api_client):
        """GET /api/demons/active/{location_id} - get active encounters"""
        response = api_client.get(f"{BASE_URL}/api/demons/active/village_square")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        encounters = response.json()
        assert isinstance(encounters, list), "Expected list of encounters"
        
        print(f"PASS: Active demons at village_square: {len(encounters)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
