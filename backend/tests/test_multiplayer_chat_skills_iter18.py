"""
Test Suite for Iteration 18: Multiplayer Chat & Skill Trees
Tests:
- Multiplayer Chat REST APIs (online users, chat history, party system, blocks)
- Skill Trees API (5 trees, 32 skills, title passives)
- Registration with display_name field
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USERNAME = f"test_chat_{uuid.uuid4().hex[:8]}"
TEST_PASSWORD = "TestPass123"
TEST_DISPLAY_NAME = "Test Chat User"


class TestRegistrationWithDisplayName:
    """Test registration includes display_name field"""
    
    def test_register_with_display_name(self):
        """Registration should accept and store display_name"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "display_name": TEST_DISPLAY_NAME
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        assert "user" in data
        assert data["user"]["username"] == TEST_USERNAME.lower()
        assert data["user"]["display_name"] == TEST_DISPLAY_NAME
        
        # Store user_id for later tests
        pytest.test_user_id = data["user"]["id"]
        print(f"✓ Registration with display_name works - user_id: {pytest.test_user_id}")


class TestChatOnlineUsersAPI:
    """Test /api/chat/online endpoint"""
    
    def test_get_online_users(self):
        """Should return online users count and list"""
        response = requests.get(f"{BASE_URL}/api/chat/online")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "online_count" in data
        assert "users" in data
        assert isinstance(data["online_count"], int)
        assert isinstance(data["users"], list)
        
        print(f"✓ Online users API works - {data['online_count']} users online")


class TestChatHistoryAPI:
    """Test /api/chat/history/{channel} endpoint"""
    
    def test_get_global_chat_history(self):
        """Should return global chat history"""
        response = requests.get(f"{BASE_URL}/api/chat/history/global")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "channel" in data
        assert data["channel"] == "global"
        assert "messages" in data
        assert "count" in data
        assert isinstance(data["messages"], list)
        
        print(f"✓ Global chat history works - {data['count']} messages")
    
    def test_get_region_chat_history(self):
        """Should return region chat history"""
        response = requests.get(f"{BASE_URL}/api/chat/history/region?region_id=village_square")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["channel"] == "region"
        print(f"✓ Region chat history works")
    
    def test_get_party_chat_history(self):
        """Should return party chat history"""
        response = requests.get(f"{BASE_URL}/api/chat/history/party?party_id=test_party")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["channel"] == "party"
        print(f"✓ Party chat history works")
    
    def test_get_whisper_chat_history(self):
        """Should return whisper chat history for a user"""
        user_id = getattr(pytest, 'test_user_id', 'test_user')
        response = requests.get(f"{BASE_URL}/api/chat/history/whisper?user_id={user_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["channel"] == "whisper"
        print(f"✓ Whisper chat history works")


class TestChatStatsAPI:
    """Test /api/chat/stats endpoint"""
    
    def test_get_chat_stats(self):
        """Should return chat statistics"""
        response = requests.get(f"{BASE_URL}/api/chat/stats")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "online_users" in data
        assert "messages_24h" in data
        assert "active_parties" in data
        assert "regions_with_players" in data
        
        print(f"✓ Chat stats API works - {data['online_users']} online, {data['active_parties']} parties")


class TestPartySystemAPI:
    """Test party creation and management"""
    
    def test_create_party(self):
        """Should create a new party"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        
        response = requests.post(
            f"{BASE_URL}/api/chat/party/create?creator_id={user_id}",
            json={
                "name": "Test Party",
                "max_members": 6
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "party_id" in data
        assert data["name"] == "Test Party"
        assert user_id in data["members"]
        
        pytest.test_party_id = data["party_id"]
        print(f"✓ Party creation works - party_id: {data['party_id']}")
    
    def test_get_party_info(self):
        """Should get party information"""
        party_id = getattr(pytest, 'test_party_id', None)
        if not party_id:
            pytest.skip("No party created")
        
        response = requests.get(f"{BASE_URL}/api/chat/party/{party_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["party_id"] == party_id
        assert "members" in data
        assert "leader_id" in data
        
        print(f"✓ Get party info works")
    
    def test_party_not_found(self):
        """Should return 404 for non-existent party"""
        response = requests.get(f"{BASE_URL}/api/chat/party/nonexistent_party_id")
        
        assert response.status_code == 404
        print(f"✓ Party not found returns 404")


class TestBlockSystemAPI:
    """Test user blocking functionality"""
    
    def test_block_user(self):
        """Should block a user"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        blocked_id = str(uuid.uuid4())
        
        response = requests.post(
            f"{BASE_URL}/api/chat/block?user_id={user_id}",
            json={"blocked_user_id": blocked_id}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "blocked"
        assert data["blocked_id"] == blocked_id
        
        pytest.blocked_user_id = blocked_id
        print(f"✓ Block user works")
    
    def test_get_blocked_users(self):
        """Should get list of blocked users"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        
        response = requests.get(f"{BASE_URL}/api/chat/blocks/{user_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "blocked_users" in data
        assert isinstance(data["blocked_users"], list)
        
        print(f"✓ Get blocked users works - {len(data['blocked_users'])} blocked")
    
    def test_unblock_user(self):
        """Should unblock a user"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        blocked_id = getattr(pytest, 'blocked_user_id', str(uuid.uuid4()))
        
        response = requests.delete(f"{BASE_URL}/api/chat/block/{blocked_id}?user_id={user_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "unblocked"
        print(f"✓ Unblock user works")


class TestSkillTreesAPI:
    """Test /api/skill-trees endpoints"""
    
    def test_get_all_skill_trees(self):
        """Should return all 5 skill trees with 32 total skills"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "skill_trees" in data
        assert "total_trees" in data
        assert "total_skills" in data
        
        # Verify 5 trees
        assert data["total_trees"] == 5, f"Expected 5 trees, got {data['total_trees']}"
        
        # Verify tree names
        trees = data["skill_trees"]
        expected_trees = ["combat", "magic", "crafting", "social", "survival"]
        for tree_name in expected_trees:
            assert tree_name in trees, f"Missing tree: {tree_name}"
        
        # Verify 32 total skills
        assert data["total_skills"] == 32, f"Expected 32 skills, got {data['total_skills']}"
        
        print(f"✓ Skill trees API works - {data['total_trees']} trees, {data['total_skills']} skills")
    
    def test_get_combat_tree(self):
        """Should return combat skill tree details"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/combat")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["name"] == "Combat Mastery"
        assert "tiers" in data
        assert "1" in data["tiers"]
        
        # Check for specific skills
        tier1 = data["tiers"]["1"]
        assert "power_strike" in tier1
        assert "defensive_stance" in tier1
        
        print(f"✓ Combat tree has Power Strike and Defensive Stance")
    
    def test_get_magic_tree(self):
        """Should return magic skill tree with Arcane Bolt, Chain Lightning, Meteor Strike"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/magic")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["name"] == "Arcane Arts"
        
        # Check for specific skills across tiers
        all_skills = []
        for tier_skills in data["tiers"].values():
            all_skills.extend(tier_skills.keys())
        
        assert "arcane_bolt" in all_skills, "Missing Arcane Bolt"
        assert "chain_lightning" in all_skills, "Missing Chain Lightning"
        assert "meteor_strike" in all_skills, "Missing Meteor Strike"
        
        print(f"✓ Magic tree has Arcane Bolt, Chain Lightning, Meteor Strike")
    
    def test_get_crafting_tree(self):
        """Should return crafting skill tree"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/crafting")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["name"] == "Master Craftsman"
        print(f"✓ Crafting tree works")
    
    def test_get_social_tree(self):
        """Should return social skill tree"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/social")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["name"] == "Silver Tongue"
        print(f"✓ Social tree works")
    
    def test_get_survival_tree(self):
        """Should return survival skill tree"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/survival")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["name"] == "Wilderness Expert"
        print(f"✓ Survival tree works")
    
    def test_tree_not_found(self):
        """Should return 404 for non-existent tree"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/nonexistent")
        
        assert response.status_code == 404
        print(f"✓ Non-existent tree returns 404")


class TestTitlePassivesAPI:
    """Test /api/skill-trees/title-passives endpoints"""
    
    def test_get_all_title_passives(self):
        """Should return all 10 titles with passive bonuses"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/title-passives")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "title_passives" in data
        assert "total_titles" in data
        
        # Verify 10 titles
        assert data["total_titles"] == 10, f"Expected 10 titles, got {data['total_titles']}"
        
        # Check for specific titles
        titles = data["title_passives"]
        expected_titles = ["newcomer", "explorer", "hero", "champion", "legend", 
                          "wealthy", "master_crafter", "shadow_walker", "dragon_slayer", "transcendent"]
        
        for title in expected_titles:
            assert title in titles, f"Missing title: {title}"
        
        print(f"✓ Title passives API works - {data['total_titles']} titles")
    
    def test_explorer_title_passives(self):
        """Explorer title should have +5% movement speed and +20% exploration XP"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/title-passives/explorer")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["title_name"] == "Explorer"
        assert "passives" in data
        
        # Check for specific passives
        passive_names = [p["name"] for p in data["passives"]]
        assert "Wanderer's Pace" in passive_names, "Missing Wanderer's Pace passive"
        assert "Discovery Bonus" in passive_names, "Missing Discovery Bonus passive"
        
        # Verify effects
        for passive in data["passives"]:
            if passive["name"] == "Wanderer's Pace":
                assert passive["effect"]["movement_speed"] == 0.05
            if passive["name"] == "Discovery Bonus":
                assert passive["effect"]["exploration_xp_bonus"] == 0.2
        
        print(f"✓ Explorer title has +5% movement speed and +20% exploration XP")
    
    def test_title_not_found(self):
        """Should return 404 for non-existent title"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/title-passives/nonexistent")
        
        assert response.status_code == 404
        print(f"✓ Non-existent title returns 404")


class TestPlayerSkillsAPI:
    """Test player skill management endpoints"""
    
    def test_get_player_skills(self):
        """Should return player's skill data"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        
        response = requests.get(f"{BASE_URL}/api/skill-trees/player/{user_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "player_id" in data
        assert "skill_points" in data
        assert "unlocked_skills" in data
        assert "skill_trees" in data
        
        print(f"✓ Player skills API works - {data['skill_points']} skill points")
    
    def test_award_skill_points(self):
        """Should award skill points to player"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        
        response = requests.post(f"{BASE_URL}/api/skill-trees/award-points?player_id={user_id}&points=3")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["awarded"] == 3
        assert data["player_id"] == user_id
        
        print(f"✓ Award skill points works")
    
    def test_get_active_effects(self):
        """Should return player's active passive effects"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        
        response = requests.get(f"{BASE_URL}/api/skill-trees/active-effects/{user_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "passive_effects" in data
        assert "combined_bonuses" in data
        assert "total_passives" in data
        
        print(f"✓ Active effects API works - {data['total_passives']} passives")


class TestWhisperConversationsAPI:
    """Test whisper conversation listing"""
    
    def test_get_whisper_conversations(self):
        """Should return list of whisper conversations"""
        user_id = getattr(pytest, 'test_user_id', str(uuid.uuid4()))
        
        response = requests.get(f"{BASE_URL}/api/chat/whispers/{user_id}/conversations")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
        
        print(f"✓ Whisper conversations API works - {len(data['conversations'])} conversations")


# Cleanup test data
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup test data after all tests"""
    def cleanup_data():
        # Clean up test user if created
        user_id = getattr(pytest, 'test_user_id', None)
        if user_id:
            try:
                requests.delete(f"{BASE_URL}/api/users/{user_id}")
            except:
                pass
        
        # Clean up test party if created
        party_id = getattr(pytest, 'test_party_id', None)
        if party_id:
            try:
                requests.delete(f"{BASE_URL}/api/chat/party/{party_id}")
            except:
                pass
    
    request.addfinalizer(cleanup_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
