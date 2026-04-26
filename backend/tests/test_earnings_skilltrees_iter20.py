"""
Test Suite for Iteration 20 Features:
- Earnings Hub real data endpoints (GET /api/earnings/history/{user_id}, GET/PUT /api/earnings/preferences/{user_id})
- Skill Trees endpoints (GET /api/skill-trees/trees, GET /api/skill-trees/player/{player_id}, POST /api/skill-trees/unlock)
- Session end syncs earnings (POST /api/rt-tasks/session/{session_id}/end)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = "sirix_1"
TEST_PASSWORD = os.environ.get("SIRIX_ADMIN_PASSWORD", "test_password")


class TestEarningsHistoryEndpoint:
    """Test GET /api/earnings/history/{user_id} - Real earnings data"""
    
    def test_earnings_history_returns_today_and_week_earned(self):
        """Verify endpoint returns today_earned and week_earned fields"""
        # First login to get user_id
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        user_id = login_res.json().get("user", {}).get("id")
        
        # Get earnings history
        response = requests.get(f"{BASE_URL}/api/earnings/history/{user_id}")
        assert response.status_code == 200, f"Earnings history failed: {response.text}"
        
        data = response.json()
        assert "today_earned" in data, "Missing today_earned field"
        assert "week_earned" in data, "Missing week_earned field"
        assert "daily_breakdown" in data, "Missing daily_breakdown field"
        assert "total_earned" in data, "Missing total_earned field"
        assert "available_balance" in data, "Missing available_balance field"
        
        # Verify types
        assert isinstance(data["today_earned"], (int, float)), "today_earned should be numeric"
        assert isinstance(data["week_earned"], (int, float)), "week_earned should be numeric"
    
    def test_earnings_history_with_days_param(self):
        """Test earnings history with custom days parameter"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        response = requests.get(f"{BASE_URL}/api/earnings/history/{user_id}?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert "transaction_count" in data
        assert "rt_session_count" in data


class TestWithdrawalPreferencesEndpoint:
    """Test GET/PUT /api/earnings/preferences/{user_id} - Withdrawal preferences"""
    
    def test_get_withdrawal_preferences_returns_defaults(self):
        """Verify GET returns default preferences for new user"""
        test_user_id = f"TEST_prefs_{uuid.uuid4().hex[:8]}"
        
        response = requests.get(f"{BASE_URL}/api/earnings/preferences/{test_user_id}")
        assert response.status_code == 200, f"Get preferences failed: {response.text}"
        
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["default_method"] == "game_balance", "Default method should be game_balance"
        assert data["is_default"] == True, "Should indicate these are defaults"
        assert "wallet_percentage" in data
    
    def test_put_withdrawal_preferences_saves_permanently(self):
        """Verify PUT saves preferences and GET retrieves them"""
        # Login to get valid user
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        # Ensure earnings account exists
        requests.get(f"{BASE_URL}/api/earnings/account/{user_id}")
        
        # Update preferences
        prefs_data = {
            "user_id": user_id,
            "default_method": "crypto",
            "default_wallet": "0x1234567890123456789012345678901234567890",
            "wallet_percentage": 75,
            "auto_withdraw_threshold": 50.0
        }
        
        put_response = requests.put(f"{BASE_URL}/api/earnings/preferences/{user_id}", json=prefs_data)
        assert put_response.status_code == 200, f"PUT preferences failed: {put_response.text}"
        
        put_data = put_response.json()
        assert put_data["updated"] == True
        
        # Verify GET returns saved preferences
        get_response = requests.get(f"{BASE_URL}/api/earnings/preferences/{user_id}")
        assert get_response.status_code == 200
        
        get_data = get_response.json()
        assert get_data["default_method"] == "crypto"
        assert get_data["default_wallet"] == "0x1234567890123456789012345678901234567890"
        assert get_data["wallet_percentage"] == 75
        assert get_data["is_default"] == False, "Should not be defaults after saving"
    
    def test_put_preferences_validates_wallet_format(self):
        """Verify wallet address validation"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        # Invalid wallet address
        prefs_data = {
            "user_id": user_id,
            "default_method": "crypto",
            "default_wallet": "invalid_wallet",
            "wallet_percentage": 100
        }
        
        response = requests.put(f"{BASE_URL}/api/earnings/preferences/{user_id}", json=prefs_data)
        assert response.status_code == 400, "Should reject invalid wallet format"


class TestSkillTreesEndpoints:
    """Test Skill Trees backend endpoints"""
    
    def test_get_all_skill_trees(self):
        """Verify GET /api/skill-trees/trees returns all 5 trees"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees")
        assert response.status_code == 200, f"Get skill trees failed: {response.text}"
        
        data = response.json()
        assert "skill_trees" in data
        trees = data["skill_trees"]
        
        # Verify all 5 trees exist
        expected_trees = ["combat", "magic", "crafting", "social", "survival"]
        for tree_id in expected_trees:
            assert tree_id in trees, f"Missing skill tree: {tree_id}"
            assert "name" in trees[tree_id]
            assert "tiers" in trees[tree_id]
            assert "description" in trees[tree_id]
        
        assert data["total_trees"] == 5
    
    def test_get_specific_skill_tree(self):
        """Verify GET /api/skill-trees/trees/{tree_id} returns tree details"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/trees/combat")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Combat Mastery"
        assert "tiers" in data
        assert 1 in data["tiers"] or "1" in data["tiers"]
    
    def test_get_player_skills(self):
        """Verify GET /api/skill-trees/player/{player_id} returns player skill data"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        response = requests.get(f"{BASE_URL}/api/skill-trees/player/{user_id}")
        assert response.status_code == 200, f"Get player skills failed: {response.text}"
        
        data = response.json()
        assert "player_id" in data
        assert "skill_points" in data
        assert "unlocked_skills" in data
        assert "skill_trees" in data
        assert "title_passives" in data
    
    def test_get_title_passives(self):
        """Verify GET /api/skill-trees/title-passives returns all title passives"""
        response = requests.get(f"{BASE_URL}/api/skill-trees/title-passives")
        assert response.status_code == 200
        
        data = response.json()
        assert "title_passives" in data
        assert "total_titles" in data
        
        # Check some expected titles
        passives = data["title_passives"]
        assert "newcomer" in passives or "explorer" in passives or "hero" in passives
    
    def test_unlock_skill_requires_points(self):
        """Verify POST /api/skill-trees/unlock validates skill points"""
        test_player_id = f"TEST_skill_{uuid.uuid4().hex[:8]}"
        
        # Try to unlock without skill points
        response = requests.post(
            f"{BASE_URL}/api/skill-trees/unlock?player_id={test_player_id}",
            json={"skill_tree": "combat", "skill_id": "power_strike"}
        )
        # Should fail because player doesn't exist or has no points
        assert response.status_code in [400, 404]


class TestSessionEndSyncsEarnings:
    """Test POST /api/rt-tasks/session/{session_id}/end syncs earnings"""
    
    def test_session_end_syncs_to_main_account(self):
        """Verify session end syncs earnings to main earnings account"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        # Start a task session
        start_res = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": user_id,
            "worker_type": "player",
            "task_type": "sentiment_label"
        })
        assert start_res.status_code == 200, f"Start session failed: {start_res.text}"
        
        session_data = start_res.json()
        session_id = session_data["session_id"]
        
        # Complete a task to earn something
        if session_data.get("tasks"):
            task = session_data["tasks"][0]
            complete_res = requests.post(f"{BASE_URL}/api/rt-tasks/task/complete", json={
                "task_id": task["task_id"],
                "worker_id": user_id,
                "response": {"sentiment": "positive"},
                "time_taken_seconds": 5.0
            })
            # Task completion may succeed or fail based on state
        
        # End session - this should sync earnings
        end_res = requests.post(f"{BASE_URL}/api/rt-tasks/session/{session_id}/end")
        assert end_res.status_code == 200, f"End session failed: {end_res.text}"
        
        end_data = end_res.json()
        assert end_data["ended"] == True
        assert "tasks_completed" in end_data
        assert "total_earnings" in end_data
        assert "synced_to_account" in end_data


class TestRTTasksTypes:
    """Test RT Tasks endpoint returns task types"""
    
    def test_get_task_types(self):
        """Verify GET /api/rt-tasks/types returns all task types"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/types")
        assert response.status_code == 200
        
        data = response.json()
        assert "task_types" in data
        assert "providers" in data
        
        # Check some expected task types
        task_types = data["task_types"]
        expected_types = ["image_tagging", "sentiment_label", "content_rating"]
        for task_type in expected_types:
            assert task_type in task_types, f"Missing task type: {task_type}"


class TestEarningsAccountEndpoint:
    """Test earnings account endpoint"""
    
    def test_get_earnings_account(self):
        """Verify GET /api/earnings/account/{user_id} returns account data"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        response = requests.get(f"{BASE_URL}/api/earnings/account/{user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "total_earned_usd" in data
        assert "available_balance_usd" in data
        assert "tasks_completed" in data


class TestSkillTreeUnlockFlow:
    """Test skill unlock flow with proper setup"""
    
    def test_award_points_and_unlock_skill(self):
        """Test awarding points and unlocking a skill"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        # Award skill points
        award_res = requests.post(
            f"{BASE_URL}/api/skill-trees/award-points?player_id={user_id}&points=5"
        )
        assert award_res.status_code == 200, f"Award points failed: {award_res.text}"
        
        # Get player skills to verify points
        player_res = requests.get(f"{BASE_URL}/api/skill-trees/player/{user_id}")
        assert player_res.status_code == 200
        
        player_data = player_res.json()
        assert player_data["skill_points"] >= 1, "Should have skill points"
    
    def test_get_active_effects(self):
        """Test GET /api/skill-trees/active-effects/{player_id}"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        user_id = login_res.json().get("user", {}).get("id")
        
        response = requests.get(f"{BASE_URL}/api/skill-trees/active-effects/{user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "passive_effects" in data
        assert "combined_bonuses" in data
        assert "total_passives" in data


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
