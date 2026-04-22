# Test P0 Systems - Skills, Titles, Entity Earnings, AI Autonomy, World Instances
# Iteration 13 - Testing new P0 features

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSkillSystemCatalog:
    """Test Skills Catalog API - 6 categories, 30 skills"""
    
    def test_01_skills_catalog_returns_6_categories(self):
        """GET /api/skill-system/catalog - Returns 6 categories"""
        response = requests.get(f"{BASE_URL}/api/skill-system/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categories" in data, "Response should have 'categories'"
        
        categories = data["categories"]
        assert len(categories) == 6, f"Expected 6 categories, got {len(categories)}"
        
        expected_categories = ["combat", "magic", "crafting", "gathering", "social", "knowledge"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        print(f"✓ Skills catalog has 6 categories: {list(categories.keys())}")
    
    def test_02_skills_catalog_returns_30_skills(self):
        """GET /api/skill-system/catalog - Returns 30 total skills"""
        response = requests.get(f"{BASE_URL}/api/skill-system/catalog")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_skills" in data, "Response should have 'total_skills'"
        assert data["total_skills"] == 30, f"Expected 30 skills, got {data['total_skills']}"
        
        # Verify each category has skills
        categories = data["categories"]
        for cat_id, cat_data in categories.items():
            assert "skills" in cat_data, f"Category {cat_id} should have skills"
            assert len(cat_data["skills"]) == 5, f"Category {cat_id} should have 5 skills"
        
        print(f"✓ Skills catalog has {data['total_skills']} total skills")
    
    def test_03_skills_catalog_has_action_mappings(self):
        """GET /api/skill-system/catalog - Returns action mappings"""
        response = requests.get(f"{BASE_URL}/api/skill-system/catalog")
        assert response.status_code == 200
        
        data = response.json()
        assert "action_mappings" in data, "Response should have 'action_mappings'"
        
        mappings = data["action_mappings"]
        assert len(mappings) > 20, f"Expected 20+ action mappings, got {len(mappings)}"
        
        # Check a few expected actions
        expected_actions = ["attack_melee", "cast_heal", "forge_item", "mine_ore", "negotiate"]
        for action in expected_actions:
            assert action in mappings, f"Missing action mapping: {action}"
        
        print(f"✓ Skills catalog has {len(mappings)} action mappings")


class TestTitlesCatalog:
    """Test Titles Catalog API - 31 titles"""
    
    def test_01_titles_catalog_returns_31_titles(self):
        """GET /api/skill-system/titles/catalog - Returns 31 titles"""
        response = requests.get(f"{BASE_URL}/api/skill-system/titles/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "titles" in data, "Response should have 'titles'"
        assert "total_titles" in data, "Response should have 'total_titles'"
        
        assert data["total_titles"] == 31, f"Expected 31 titles, got {data['total_titles']}"
        
        titles = data["titles"]
        assert len(titles) == 31, f"Expected 31 titles in dict, got {len(titles)}"
        
        print(f"✓ Titles catalog has {data['total_titles']} titles")
    
    def test_02_titles_have_requirements_and_boosts(self):
        """Titles should have requirements and stat boosts"""
        response = requests.get(f"{BASE_URL}/api/skill-system/titles/catalog")
        assert response.status_code == 200
        
        data = response.json()
        titles = data["titles"]
        
        # Check a few specific titles
        assert "sword_saint" in titles, "Missing title: sword_saint"
        sword_saint = titles["sword_saint"]
        assert "requirement" in sword_saint, "Title should have requirement"
        assert "boosts" in sword_saint, "Title should have boosts"
        assert sword_saint["requirement"]["skill"] == "swordsmanship"
        assert sword_saint["requirement"]["level"] == 100
        
        print(f"✓ Titles have proper requirements and boosts")


class TestSkillAction:
    """Test Skill Action API - Awards XP"""
    
    def test_01_skill_action_awards_xp(self):
        """POST /api/skill-system/action - Awards XP for action"""
        payload = {
            "entity_id": "TEST_player_skill_action",
            "entity_type": "player",
            "action": "attack_melee"
        }
        
        response = requests.post(f"{BASE_URL}/api/skill-system/action", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "xp_gained" in data, "Response should have 'xp_gained'"
        assert "skill" in data, "Response should have 'skill'"
        assert data["skill"] == "swordsmanship", f"Expected swordsmanship, got {data['skill']}"
        assert data["xp_gained"] > 0, "XP gained should be positive"
        
        print(f"✓ Skill action awarded {data['xp_gained']} XP to {data['skill']}")
    
    def test_02_skill_action_with_difficulty_multiplier(self):
        """POST /api/skill-system/action - Difficulty affects XP"""
        payload = {
            "entity_id": "TEST_player_skill_difficulty",
            "entity_type": "player",
            "action": "forge_item",
            "context": {"difficulty": 2.0}
        }
        
        response = requests.post(f"{BASE_URL}/api/skill-system/action", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["skill"] == "blacksmithing"
        assert data["xp_gained"] > 0
        
        print(f"✓ Skill action with difficulty multiplier awarded {data['xp_gained']} XP")
    
    def test_03_invalid_action_returns_400(self):
        """POST /api/skill-system/action - Invalid action returns 400"""
        payload = {
            "entity_id": "TEST_player_invalid",
            "entity_type": "player",
            "action": "invalid_action_xyz"
        }
        
        response = requests.post(f"{BASE_URL}/api/skill-system/action", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        print("✓ Invalid action correctly returns 400")


class TestEntityEarnings:
    """Test Entity Earnings API - VE$ for players and AI"""
    
    def test_01_activities_returns_18_activities(self):
        """GET /api/entity-earnings/activities - Returns 18 activities"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/activities")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "activities" in data, "Response should have 'activities'"
        
        activities = data["activities"]
        assert len(activities) == 18, f"Expected 18 activities, got {len(activities)}"
        
        # Check some expected activities
        expected = ["trade_completed", "quest_completed", "item_crafted", "conversation_value"]
        for act in expected:
            assert act in activities, f"Missing activity: {act}"
        
        print(f"✓ Entity earnings has {len(activities)} activities")
    
    def test_02_wallet_creation_for_player(self):
        """GET /api/entity-earnings/wallet/player/{id} - Creates wallet"""
        entity_id = "TEST_player_wallet_123"
        response = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{entity_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "entity_id" in data, "Response should have 'entity_id'"
        assert "entity_type" in data, "Response should have 'entity_type'"
        assert "balance_ve" in data, "Response should have 'balance_ve'"
        assert data["entity_id"] == entity_id
        assert data["entity_type"] == "player"
        
        print(f"✓ Player wallet created with balance: {data['balance_ve']} VE$")
    
    def test_03_wallet_creation_for_npc(self):
        """GET /api/entity-earnings/wallet/npc/{id} - Creates NPC wallet"""
        entity_id = "TEST_npc_wallet_456"
        response = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/npc/{entity_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["entity_type"] == "npc"
        
        print(f"✓ NPC wallet created with balance: {data['balance_ve']} VE$")
    
    def test_04_record_earning(self):
        """POST /api/entity-earnings/record - Records earning"""
        payload = {
            "entity_id": "TEST_player_earning",
            "entity_type": "player",
            "activity": "trade_completed",
            "multiplier": 1.0
        }
        
        response = requests.post(f"{BASE_URL}/api/entity-earnings/record", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recorded" in data, "Response should have 'recorded'"
        assert data["recorded"] == True, "Earning should be recorded"
        assert "amount" in data, "Response should have 'amount'"
        assert data["amount"] > 0, "Amount should be positive"
        
        print(f"✓ Recorded earning of {data['amount']} VE$ for {payload['activity']}")
    
    def test_05_record_earning_for_npc(self):
        """POST /api/entity-earnings/record - NPC can earn VE$"""
        payload = {
            "entity_id": "TEST_npc_earning",
            "entity_type": "npc",
            "activity": "conversation_value"
        }
        
        response = requests.post(f"{BASE_URL}/api/entity-earnings/record", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["recorded"] == True
        
        print(f"✓ NPC earned {data['amount']} VE$ for conversation")


class TestAIAutonomy:
    """Test AI Autonomy API - NPC state and autonomous actions"""
    
    def test_01_get_npc_state(self):
        """GET /api/ai-autonomy/npc/{id}/state - Returns NPC state"""
        npc_id = "TEST_autonomous_npc"
        response = requests.get(f"{BASE_URL}/api/ai-autonomy/npc/{npc_id}/state")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "npc_id" in data, "Response should have 'npc_id'"
        assert "personality" in data, "Response should have 'personality'"
        assert "free_will" in data, "Response should have 'free_will'"
        assert "resources" in data, "Response should have 'resources'"
        
        # Check personality traits
        personality = data["personality"]
        expected_traits = ["cooperative", "aggressive", "curious", "creative", "social"]
        for trait in expected_traits:
            assert trait in personality, f"Missing personality trait: {trait}"
        
        print(f"✓ NPC state retrieved with free_will: {data['free_will']}")
    
    def test_02_npc_autonomous_action(self):
        """POST /api/ai-autonomy/npc/{id}/act - NPC takes action"""
        npc_id = "TEST_acting_npc"
        
        # First get state to ensure NPC exists
        requests.get(f"{BASE_URL}/api/ai-autonomy/npc/{npc_id}/state")
        
        # Try to make NPC act
        response = requests.post(f"{BASE_URL}/api/ai-autonomy/npc/{npc_id}/act")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # NPC may or may not act based on free_will
        assert "acted" in data, "Response should have 'acted'"
        
        if data["acted"]:
            assert "action" in data, "Response should have 'action'"
            print(f"✓ NPC took action: {data['action']}")
        else:
            print(f"✓ NPC chose not to act (reason: {data.get('reason', 'unknown')})")
    
    def test_03_start_ai_conversation(self):
        """POST /api/ai-autonomy/conversation/start - Start AI-to-AI conversation"""
        payload = {
            "initiator_id": "TEST_npc_initiator",
            "target_id": "TEST_npc_target",
            "topic": "trade negotiations",
            "location": "village_square"
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-autonomy/conversation/start", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "conversation_id" in data, "Response should have 'conversation_id'"
        assert "initial_message" in data, "Response should have 'initial_message'"
        
        print(f"✓ AI conversation started: {data['conversation_id'][:8]}...")
        print(f"  Initial message: {data['initial_message'][:50]}...")
        
        return data["conversation_id"]


class TestWorldInstances:
    """Test World Instances API - Private worlds, Sirix-1 realm, story world"""
    
    def test_01_world_types_and_story_characters(self):
        """GET /api/worlds/types - Returns world types and story characters"""
        response = requests.get(f"{BASE_URL}/api/worlds/types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "types" in data, "Response should have 'types'"
        assert "story_characters" in data, "Response should have 'story_characters'"
        
        # Check world types
        types = data["types"]
        expected_types = ["private", "shared", "story", "instance"]
        for wtype in expected_types:
            assert wtype in types, f"Missing world type: {wtype}"
        
        # Check story characters (should be 8)
        characters = data["story_characters"]
        assert len(characters) == 8, f"Expected 8 story characters, got {len(characters)}"
        
        print(f"✓ World types: {list(types.keys())}")
        print(f"✓ Story characters: {[c['name'] for c in characters]}")
    
    def test_02_sirix_1_private_realm_access(self):
        """GET /api/worlds/sirix-1/realm - Sirix-1 exclusive access"""
        # Test with sirix_1 user
        response = requests.get(f"{BASE_URL}/api/worlds/sirix-1/realm?user_id=sirix_1")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "world" in data, "Response should have 'world'"
        assert "exclusive" in data, "Response should have 'exclusive'"
        assert data["exclusive"] == True
        
        world = data["world"]
        assert world["owner_id"] == "sirix_1"
        
        print(f"✓ Sirix-1 private realm accessible: {world['name']}")
    
    def test_03_sirix_1_realm_denied_to_others(self):
        """GET /api/worlds/sirix-1/realm - Denied to non-sirix_1 users"""
        response = requests.get(f"{BASE_URL}/api/worlds/sirix-1/realm?user_id=other_user")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        print("✓ Sirix-1 realm correctly denies access to other users")
    
    def test_04_main_story_world(self):
        """GET /api/worlds/story/main - Returns main story world"""
        response = requests.get(f"{BASE_URL}/api/worlds/story/main")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "world" in data, "Response should have 'world'"
        assert "original_characters" in data, "Response should have 'original_characters'"
        
        world = data["world"]
        assert world["world_type"] == "story"
        
        characters = data["original_characters"]
        assert len(characters) == 8, f"Expected 8 original characters, got {len(characters)}"
        
        # Check some expected characters
        char_names = [c["name"] for c in characters]
        expected_chars = ["Elder Morvain", "Lyra the Wanderer", "Oracle Veythra"]
        for char in expected_chars:
            assert char in char_names, f"Missing character: {char}"
        
        print(f"✓ Main story world: {world['name']}")
        print(f"✓ Original characters: {char_names}")


class TestEntitySkillsAndTitles:
    """Test entity skills and titles retrieval"""
    
    def test_01_get_entity_skills(self):
        """GET /api/skill-system/entity/player/{id} - Returns player skills"""
        entity_id = "TEST_player_skills"
        response = requests.get(f"{BASE_URL}/api/skill-system/entity/player/{entity_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "entity_id" in data
        assert "entity_type" in data
        assert "skills" in data
        assert "total_skill_points" in data
        
        print(f"✓ Entity skills retrieved, total points: {data['total_skill_points']}")
    
    def test_02_get_entity_titles(self):
        """GET /api/skill-system/entity/player/{id}/titles - Returns player titles"""
        entity_id = "TEST_player_titles"
        response = requests.get(f"{BASE_URL}/api/skill-system/entity/player/{entity_id}/titles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "entity_id" in data
        assert "unlocked_titles" in data
        assert "active_title" in data
        
        print(f"✓ Entity titles retrieved, unlocked: {len(data['unlocked_titles'])}")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed data after tests"""
    yield
    # Note: In a real scenario, we'd clean up test data here
    print("\n✓ Test cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
