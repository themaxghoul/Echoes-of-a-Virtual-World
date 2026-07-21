# Iteration 27 Tests: Profile Customization & AI Training System
# Tests: Display name editing, Profile customization API, AI Training System with Student→Master progression

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user ID from requirements
TEST_USER_ID = "sirix_1_supreme"
TEST_NPC_ID = "elder_mira"


class TestProfileCustomizationAPI:
    """Tests for Profile Customization endpoints - Display name editing fix"""
    
    def test_get_profile_customization(self):
        """GET /api/profile/customization/{user_id} - Returns profile with display_name, username, profile_logo, auth_method, legacy_usernames"""
        response = requests.get(f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions - validate response structure
        data = response.json()
        assert "user_id" in data, "Response should contain user_id"
        assert "display_name" in data, "Response should contain display_name"
        assert "username" in data, "Response should contain username"
        assert "profile_logo" in data, "Response should contain profile_logo"
        assert "auth_method" in data, "Response should contain auth_method"
        assert "legacy_usernames" in data, "Response should contain legacy_usernames"
        
        # Validate data types
        assert isinstance(data["legacy_usernames"], list), "legacy_usernames should be a list"
        assert data["user_id"] == TEST_USER_ID, f"user_id should match {TEST_USER_ID}"
        
        print(f"Profile customization retrieved: display_name={data['display_name']}, username={data['username']}")
    
    def test_update_display_name(self):
        """PUT /api/profile/customization/{user_id} - Display name can be updated successfully"""
        # First get current display name
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}")
        assert get_response.status_code == 200
        original_name = get_response.json().get("display_name")
        
        # Update display name
        new_display_name = f"TEST_Updated_{datetime.now().strftime('%H%M%S')}"
        update_payload = {"display_name": new_display_name}
        
        update_response = requests.put(
            f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}",
            json=update_payload
        )
        
        # Status code assertion
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Data assertions
        update_data = update_response.json()
        assert update_data.get("updated") == True, "Update should return updated=True"
        
        # Verify persistence with GET
        verify_response = requests.get(f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}")
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["display_name"] == new_display_name, f"Display name should be updated to {new_display_name}"
        
        print(f"Display name updated from '{original_name}' to '{new_display_name}'")
        
        # Restore original name if it existed
        if original_name:
            requests.put(
                f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}",
                json={"display_name": original_name}
            )
    
    def test_display_name_validation_too_short(self):
        """PUT /api/profile/customization/{user_id} - Rejects display name < 2 characters"""
        update_payload = {"display_name": "A"}  # Too short
        
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}",
            json=update_payload
        )
        
        # Should return 400 for validation error
        assert response.status_code == 400, f"Expected 400 for too short name, got {response.status_code}"
        assert "2-30 characters" in response.text.lower() or "display name" in response.text.lower()
        print("Correctly rejected display name that is too short")
    
    def test_display_name_validation_too_long(self):
        """PUT /api/profile/customization/{user_id} - Rejects display name > 30 characters"""
        update_payload = {"display_name": "A" * 35}  # Too long
        
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}",
            json=update_payload
        )
        
        # Should return 400 for validation error
        assert response.status_code == 400, f"Expected 400 for too long name, got {response.status_code}"
        assert "2-30 characters" in response.text.lower() or "display name" in response.text.lower()
        print("Correctly rejected display name that is too long")
    
    def test_update_profile_logo(self):
        """PUT /api/profile/customization/{user_id} - Can update profile_logo"""
        test_logo_url = "https://example.com/test_logo.png"
        update_payload = {"profile_logo": test_logo_url}
        
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}",
            json=update_payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence
        verify_response = requests.get(f"{BASE_URL}/api/profile/customization/{TEST_USER_ID}")
        verify_data = verify_response.json()
        assert verify_data["profile_logo"] == test_logo_url, "profile_logo should be updated"
        print(f"Profile logo updated to: {test_logo_url}")
    
    def test_get_customization_options(self):
        """GET /api/profile/customization-options - Returns available customization options"""
        response = requests.get(f"{BASE_URL}/api/profile/customization-options")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "chat_colors" in data, "Should return chat_colors"
        assert "model_presets" in data, "Should return model_presets"
        assert "color_fields" in data, "Should return color_fields"
        
        print(f"Customization options: {len(data['chat_colors'])} colors, {len(data['model_presets'])} presets")
    
    def test_profile_not_found(self):
        """GET /api/profile/customization/{user_id} - Returns 404 for non-existent user"""
        response = requests.get(f"{BASE_URL}/api/profile/customization/nonexistent_user_12345")
        
        assert response.status_code == 404, f"Expected 404 for non-existent user, got {response.status_code}"
        print("Correctly returned 404 for non-existent user")


class TestAITrainingSkillsAPI:
    """Tests for AI Training System - GET /api/ai-training/skills"""
    
    def test_get_trainable_skills(self):
        """GET /api/ai-training/skills - Returns trainable skills with 6 categories and 7 mastery levels"""
        response = requests.get(f"{BASE_URL}/api/ai-training/skills")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate structure
        assert "skills" in data, "Response should contain skills"
        assert "by_category" in data, "Response should contain by_category"
        assert "categories" in data, "Response should contain categories"
        assert "mastery_levels" in data, "Response should contain mastery_levels"
        
        # Validate 6 categories
        expected_categories = ["combat", "crafting", "magic", "social", "knowledge", "survival"]
        assert data["categories"] == expected_categories, f"Expected 6 categories: {expected_categories}"
        
        # Validate 7 mastery levels
        expected_levels = ["novice", "student", "apprentice", "journeyman", "expert", "master", "grandmaster"]
        assert len(data["mastery_levels"]) == 7, f"Expected 7 mastery levels, got {len(data['mastery_levels'])}"
        for level in expected_levels:
            assert level in data["mastery_levels"], f"Missing mastery level: {level}"
        
        # Validate mastery level structure
        for level_name, level_info in data["mastery_levels"].items():
            assert "level" in level_info, f"Mastery level {level_name} should have 'level'"
            assert "xp_required" in level_info, f"Mastery level {level_name} should have 'xp_required'"
            assert "efficiency" in level_info, f"Mastery level {level_name} should have 'efficiency'"
        
        # Validate skills exist in each category
        for category in expected_categories:
            assert category in data["by_category"], f"Category {category} should be in by_category"
            assert len(data["by_category"][category]) > 0, f"Category {category} should have skills"
        
        print(f"AI Training skills: {len(data['skills'])} skills across {len(data['categories'])} categories")
        print(f"Mastery levels: {list(data['mastery_levels'].keys())}")


class TestAITrainingActivitiesAPI:
    """Tests for AI Training System - GET /api/ai-training/activities"""
    
    def test_get_training_activities(self):
        """GET /api/ai-training/activities - Returns training activities with XP values"""
        response = requests.get(f"{BASE_URL}/api/ai-training/activities")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate structure
        assert "activities" in data, "Response should contain activities"
        
        # Validate activities have required fields
        activities = data["activities"]
        assert len(activities) > 0, "Should have at least one activity"
        
        for activity_id, activity_info in activities.items():
            assert "xp" in activity_info, f"Activity {activity_id} should have 'xp'"
            assert "description" in activity_info, f"Activity {activity_id} should have 'description'"
            assert isinstance(activity_info["xp"], int), f"Activity {activity_id} xp should be int"
        
        # Check for expected activities
        expected_activities = ["observe_player", "assist_player", "practice_alone", "receive_lesson", "complete_task"]
        for expected in expected_activities:
            assert expected in activities, f"Missing expected activity: {expected}"
        
        print(f"Training activities: {list(activities.keys())}")
        print(f"XP values: {[(k, v['xp']) for k, v in activities.items()]}")


class TestAITrainingTrainAPI:
    """Tests for AI Training System - POST /api/ai-training/train"""
    
    def test_train_npc_in_skill(self):
        """POST /api/ai-training/train - Can train an NPC in a skill and receive XP"""
        train_payload = {
            "trainer_id": TEST_USER_ID,
            "entity_id": TEST_NPC_ID,
            "entity_type": "npc",
            "skill_id": "diplomacy",
            "activity": "receive_lesson",
            "duration_minutes": 5,
            "context": "Teaching diplomacy basics"
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-training/train", json=train_payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate response structure
        assert data.get("success") == True, "Training should return success=True"
        assert "skill" in data, "Response should contain skill"
        assert "activity" in data, "Response should contain activity"
        assert "xp_gained" in data, "Response should contain xp_gained"
        assert "total_xp" in data, "Response should contain total_xp"
        assert "current_level" in data, "Response should contain current_level"
        assert "efficiency" in data, "Response should contain efficiency"
        
        # Validate data values
        assert data["skill"] == "diplomacy", "Skill should be diplomacy"
        assert data["activity"] == "receive_lesson", "Activity should be receive_lesson"
        assert data["xp_gained"] > 0, "Should gain positive XP"
        assert data["total_xp"] >= data["xp_gained"], "Total XP should be >= gained XP"
        
        print(f"Training result: skill={data['skill']}, xp_gained={data['xp_gained']}, total_xp={data['total_xp']}, level={data['current_level']}")
    
    def test_train_invalid_skill(self):
        """POST /api/ai-training/train - Returns 400 for invalid skill"""
        train_payload = {
            "trainer_id": TEST_USER_ID,
            "entity_id": TEST_NPC_ID,
            "entity_type": "npc",
            "skill_id": "invalid_skill_xyz",
            "activity": "receive_lesson",
            "duration_minutes": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-training/train", json=train_payload)
        
        assert response.status_code == 400, f"Expected 400 for invalid skill, got {response.status_code}"
        assert "unknown skill" in response.text.lower()
        print("Correctly rejected invalid skill")
    
    def test_train_invalid_activity(self):
        """POST /api/ai-training/train - Returns 400 for invalid activity"""
        train_payload = {
            "trainer_id": TEST_USER_ID,
            "entity_id": TEST_NPC_ID,
            "entity_type": "npc",
            "skill_id": "diplomacy",
            "activity": "invalid_activity_xyz",
            "duration_minutes": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/ai-training/train", json=train_payload)
        
        assert response.status_code == 400, f"Expected 400 for invalid activity, got {response.status_code}"
        assert "unknown activity" in response.text.lower()
        print("Correctly rejected invalid activity")
    
    def test_train_multiple_activities(self):
        """POST /api/ai-training/train - Different activities give different XP"""
        activities_xp = {}
        
        for activity in ["observe_player", "assist_player", "receive_lesson"]:
            train_payload = {
                "trainer_id": TEST_USER_ID,
                "entity_id": f"test_npc_{activity}",
                "entity_type": "npc",
                "skill_id": "swordsmanship",
                "activity": activity,
                "duration_minutes": 5
            }
            
            response = requests.post(f"{BASE_URL}/api/ai-training/train", json=train_payload)
            assert response.status_code == 200, f"Training with {activity} failed: {response.text}"
            
            data = response.json()
            activities_xp[activity] = data["xp_gained"]
        
        # receive_lesson should give more XP than observe_player
        assert activities_xp["receive_lesson"] > activities_xp["observe_player"], \
            "receive_lesson should give more XP than observe_player"
        
        print(f"Activity XP comparison: {activities_xp}")


class TestAITrainingEntitySkillsAPI:
    """Tests for AI Training System - GET /api/ai-training/entity/{entity_id}/skills"""
    
    def test_get_entity_skills(self):
        """GET /api/ai-training/entity/{entity_id}/skills - Returns all skills for an entity"""
        # First train the entity to ensure they have at least one skill
        train_payload = {
            "trainer_id": TEST_USER_ID,
            "entity_id": TEST_NPC_ID,
            "entity_type": "npc",
            "skill_id": "diplomacy",
            "activity": "practice_alone",
            "duration_minutes": 1
        }
        requests.post(f"{BASE_URL}/api/ai-training/train", json=train_payload)
        
        # Now get entity skills
        response = requests.get(f"{BASE_URL}/api/ai-training/entity/{TEST_NPC_ID}/skills?entity_type=npc")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate structure
        assert "entity_id" in data, "Response should contain entity_id"
        assert "skills" in data, "Response should contain skills"
        assert "by_category" in data, "Response should contain by_category"
        assert "total_skills" in data, "Response should contain total_skills"
        assert "total_xp" in data, "Response should contain total_xp"
        assert "overall_rating" in data, "Response should contain overall_rating"
        
        assert data["entity_id"] == TEST_NPC_ID, f"entity_id should be {TEST_NPC_ID}"
        assert isinstance(data["skills"], list), "skills should be a list"
        assert isinstance(data["total_xp"], int), "total_xp should be int"
        
        print(f"Entity {TEST_NPC_ID} skills: {data['total_skills']} skills, {data['total_xp']} total XP, rating: {data['overall_rating']}")
    
    def test_get_entity_skills_empty(self):
        """GET /api/ai-training/entity/{entity_id}/skills - Returns empty for new entity"""
        response = requests.get(f"{BASE_URL}/api/ai-training/entity/new_entity_no_skills/skills?entity_type=npc")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["total_skills"] == 0, "New entity should have 0 skills"
        assert data["total_xp"] == 0, "New entity should have 0 XP"
        print("Correctly returned empty skills for new entity")


class TestAITrainingSkillDetailAPI:
    """Tests for AI Training System - GET /api/ai-training/entity/{entity_id}/skill/{skill_id}"""
    
    def test_get_entity_skill_detail(self):
        """GET /api/ai-training/entity/{entity_id}/skill/{skill_id} - Returns detailed skill info"""
        # First train the entity
        train_payload = {
            "trainer_id": TEST_USER_ID,
            "entity_id": TEST_NPC_ID,
            "entity_type": "npc",
            "skill_id": "diplomacy",
            "activity": "receive_lesson",
            "duration_minutes": 5
        }
        requests.post(f"{BASE_URL}/api/ai-training/train", json=train_payload)
        
        # Get skill detail
        response = requests.get(f"{BASE_URL}/api/ai-training/entity/{TEST_NPC_ID}/skill/diplomacy?entity_type=npc")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate structure
        assert "entity_id" in data, "Response should contain entity_id"
        assert "skill_id" in data, "Response should contain skill_id"
        assert "xp" in data, "Response should contain xp"
        assert "mastery_level" in data, "Response should contain mastery_level"
        assert "efficiency" in data, "Response should contain efficiency"
        assert "has_started" in data, "Response should contain has_started"
        
        assert data["skill_id"] == "diplomacy", "skill_id should be diplomacy"
        assert data["has_started"] == True, "has_started should be True after training"
        assert data["xp"] > 0, "XP should be > 0 after training"
        
        print(f"Skill detail: {data['skill_id']}, xp={data['xp']}, level={data['mastery_level']}, efficiency={data['efficiency']}")
    
    def test_get_entity_skill_not_started(self):
        """GET /api/ai-training/entity/{entity_id}/skill/{skill_id} - Returns novice for untrained skill"""
        response = requests.get(f"{BASE_URL}/api/ai-training/entity/new_entity_xyz/skill/archery?entity_type=npc")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["xp"] == 0, "Untrained skill should have 0 XP"
        assert data["mastery_level"] == "novice", "Untrained skill should be novice level"
        assert data["has_started"] == False, "Untrained skill should have has_started=False"
        print("Correctly returned novice level for untrained skill")
    
    def test_get_invalid_skill_detail(self):
        """GET /api/ai-training/entity/{entity_id}/skill/{skill_id} - Returns 400 for invalid skill"""
        response = requests.get(f"{BASE_URL}/api/ai-training/entity/{TEST_NPC_ID}/skill/invalid_skill_xyz?entity_type=npc")
        
        assert response.status_code == 400, f"Expected 400 for invalid skill, got {response.status_code}"
        print("Correctly returned 400 for invalid skill")


class TestAITrainingLeaderboardAPI:
    """Tests for AI Training System - GET /api/ai-training/leaderboard/{skill_id}"""
    
    def test_get_skill_leaderboard(self):
        """GET /api/ai-training/leaderboard/{skill_id} - Returns leaderboard for a skill"""
        response = requests.get(f"{BASE_URL}/api/ai-training/leaderboard/diplomacy?entity_type=npc&limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate structure
        assert "skill_id" in data, "Response should contain skill_id"
        assert "skill_name" in data, "Response should contain skill_name"
        assert "leaderboard" in data, "Response should contain leaderboard"
        
        assert data["skill_id"] == "diplomacy", "skill_id should be diplomacy"
        assert isinstance(data["leaderboard"], list), "leaderboard should be a list"
        
        # If there are entries, validate structure
        if len(data["leaderboard"]) > 0:
            entry = data["leaderboard"][0]
            assert "entity_id" in entry, "Leaderboard entry should have entity_id"
            assert "xp" in entry, "Leaderboard entry should have xp"
        
        print(f"Leaderboard for {data['skill_name']}: {len(data['leaderboard'])} entries")
    
    def test_get_invalid_skill_leaderboard(self):
        """GET /api/ai-training/leaderboard/{skill_id} - Returns 400 for invalid skill"""
        response = requests.get(f"{BASE_URL}/api/ai-training/leaderboard/invalid_skill_xyz")
        
        assert response.status_code == 400, f"Expected 400 for invalid skill, got {response.status_code}"
        print("Correctly returned 400 for invalid skill leaderboard")


class TestMasteryProgression:
    """Tests for Student→Master progression system"""
    
    def test_mastery_level_progression(self):
        """Verify mastery levels have correct XP thresholds"""
        response = requests.get(f"{BASE_URL}/api/ai-training/skills")
        assert response.status_code == 200
        
        data = response.json()
        mastery_levels = data["mastery_levels"]
        
        # Verify XP thresholds are in ascending order
        expected_order = ["novice", "student", "apprentice", "journeyman", "expert", "master", "grandmaster"]
        prev_xp = -1
        
        for level_name in expected_order:
            level_info = mastery_levels[level_name]
            assert level_info["xp_required"] > prev_xp, f"{level_name} XP should be > {prev_xp}"
            prev_xp = level_info["xp_required"]
            
            # Verify efficiency increases with level
            assert 0 < level_info["efficiency"] <= 1.0, f"{level_name} efficiency should be between 0 and 1"
        
        # Verify grandmaster has highest efficiency
        assert mastery_levels["grandmaster"]["efficiency"] == 1.0, "Grandmaster should have 100% efficiency"
        
        print("Mastery progression verified: novice→student→apprentice→journeyman→expert→master→grandmaster")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
