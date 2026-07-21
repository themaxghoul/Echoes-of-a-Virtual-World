"""
Test Suite for Real-Time Tasks and AI Compute Marketplace Features
Iteration 15 - Testing RT Tasks, Compute Marketplace, and Entity Earnings
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com').rstrip('/')

# Test user credentials
TEST_USER_ID = f"TEST_user_{uuid.uuid4().hex[:8]}"
TEST_NPC_ID = f"TEST_npc_{uuid.uuid4().hex[:8]}"


class TestRTTasksTypes:
    """Test Real-Time Task Types endpoint"""
    
    def test_get_task_types_returns_all_types(self):
        """GET /api/rt-tasks/types - Returns all 13 task types"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/types")
        assert response.status_code == 200
        
        data = response.json()
        assert "task_types" in data
        assert "providers" in data
        
        # Verify all 13 task types exist
        expected_types = [
            "image_tagging", "image_comparison", "content_rating",
            "sentiment_label", "text_categorization", "spam_detection",
            "audio_transcription_short", "response_ranking", "prompt_writing",
            "captcha_solving", "data_entry", "npc_dialogue_rating", "world_description"
        ]
        for task_type in expected_types:
            assert task_type in data["task_types"], f"Missing task type: {task_type}"
    
    def test_task_types_have_required_fields(self):
        """Each task type has name, description, payout_per_task, avg_time_seconds"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/types")
        assert response.status_code == 200
        
        data = response.json()
        for task_key, task_data in data["task_types"].items():
            assert "name" in task_data, f"Task {task_key} missing name"
            assert "description" in task_data, f"Task {task_key} missing description"
            assert "payout_per_task" in task_data, f"Task {task_key} missing payout_per_task"
            assert "avg_time_seconds" in task_data, f"Task {task_key} missing avg_time_seconds"
            assert "batch_size" in task_data, f"Task {task_key} missing batch_size"
    
    def test_providers_include_internal(self):
        """Providers include internal provider with instant_payout"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/types")
        assert response.status_code == 200
        
        data = response.json()
        assert "internal" in data["providers"]
        assert data["providers"]["internal"]["instant_payout"] == True
        assert data["providers"]["internal"]["reliability"] == 1.0


class TestRTTasksSession:
    """Test Real-Time Task Session endpoints"""
    
    def test_start_session_sentiment_label(self):
        """POST /api/rt-tasks/session/start - Start sentiment_label session"""
        response = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": TEST_USER_ID,
            "worker_type": "player",
            "task_type": "sentiment_label"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "session_id" in data
        assert data["task_type"] == "sentiment_label"
        assert "tasks" in data
        assert len(data["tasks"]) > 0
        assert data["payout_per_task"] == 0.01
        assert "estimated_hourly" in data
        
        # Store session_id for later tests
        TestRTTasksSession.session_id = data["session_id"]
        TestRTTasksSession.first_task = data["tasks"][0]
    
    def test_start_session_invalid_task_type(self):
        """POST /api/rt-tasks/session/start - Invalid task type returns 400"""
        response = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": TEST_USER_ID,
            "worker_type": "player",
            "task_type": "invalid_task_type"
        })
        assert response.status_code == 400
    
    def test_complete_task(self):
        """POST /api/rt-tasks/task/complete - Complete a task and earn VE$"""
        # First start a session to get a task
        session_res = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": TEST_USER_ID,
            "worker_type": "player",
            "task_type": "sentiment_label"
        })
        assert session_res.status_code == 200
        task = session_res.json()["tasks"][0]
        
        # Complete the task
        response = requests.post(f"{BASE_URL}/api/rt-tasks/task/complete", json={
            "task_id": task["task_id"],
            "worker_id": TEST_USER_ID,
            "response": {"sentiment": "positive"},
            "time_taken_seconds": 5.0
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["completed"] == True
        assert data["payout"] == 0.01
        assert data["instant_paid"] == True
        assert "skill_xp" in data
    
    def test_complete_task_not_found(self):
        """POST /api/rt-tasks/task/complete - Non-existent task returns 404"""
        response = requests.post(f"{BASE_URL}/api/rt-tasks/task/complete", json={
            "task_id": "non_existent_task_id",
            "worker_id": TEST_USER_ID,
            "response": {"sentiment": "positive"},
            "time_taken_seconds": 5.0
        })
        assert response.status_code == 404
    
    def test_get_next_batch(self):
        """GET /api/rt-tasks/session/{session_id}/next-batch - Get more tasks"""
        # Start a session first
        session_res = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": TEST_USER_ID,
            "worker_type": "player",
            "task_type": "content_rating"
        })
        session_id = session_res.json()["session_id"]
        
        response = requests.get(f"{BASE_URL}/api/rt-tasks/session/{session_id}/next-batch?count=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 5
    
    def test_end_session(self):
        """POST /api/rt-tasks/session/{session_id}/end - End a session"""
        # Start a session first
        session_res = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": TEST_USER_ID,
            "worker_type": "player",
            "task_type": "image_tagging"
        })
        session_id = session_res.json()["session_id"]
        
        response = requests.post(f"{BASE_URL}/api/rt-tasks/session/{session_id}/end")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ended"] == True
        assert data["session_id"] == session_id


class TestRTTasksStats:
    """Test Real-Time Task Statistics endpoints"""
    
    def test_get_worker_stats(self):
        """GET /api/rt-tasks/worker/{worker_id}/stats - Get worker statistics"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/worker/{TEST_USER_ID}/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["worker_id"] == TEST_USER_ID
        assert "total_tasks" in data
        assert "total_earnings" in data
        assert "by_task_type" in data
        assert "recent_transactions" in data
    
    def test_get_hourly_leaderboard(self):
        """GET /api/rt-tasks/leaderboard/hourly - Get hourly leaderboard"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/leaderboard/hourly?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["timeframe"] == "1_hour"
        assert "leaderboard" in data
    
    def test_get_platform_stats(self):
        """GET /api/rt-tasks/platform/stats - Get platform statistics"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/platform/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks_completed_hour" in data
        assert "tasks_completed_day" in data
        assert "daily_payout_ve" in data
        assert "active_workers" in data
        assert "task_types_available" in data
        assert data["task_types_available"] == 13


class TestComputeMarketplace:
    """Test AI Compute Marketplace endpoints"""
    
    def test_get_compute_tiers(self):
        """GET /api/economy/compute/tiers - Returns cloud and hardware tiers"""
        response = requests.get(f"{BASE_URL}/api/economy/compute/tiers")
        assert response.status_code == 200
        
        data = response.json()
        assert "cloud_compute" in data
        assert "hardware_purchase" in data
        
        # Verify 6 cloud tiers
        expected_cloud = ["basic", "standard", "performance", "gpu_basic", "gpu_advanced", "gpu_cluster"]
        for tier in expected_cloud:
            assert tier in data["cloud_compute"], f"Missing cloud tier: {tier}"
        
        # Verify 5 hardware tiers
        expected_hardware = ["raspberry_pi", "mini_pc", "workstation", "server_node", "compute_rack"]
        for hw in expected_hardware:
            assert hw in data["hardware_purchase"], f"Missing hardware: {hw}"
    
    def test_cloud_tiers_have_specs(self):
        """Cloud tiers have specs, hourly_cost_ve, use_cases"""
        response = requests.get(f"{BASE_URL}/api/economy/compute/tiers")
        assert response.status_code == 200
        
        data = response.json()
        for tier_key, tier_data in data["cloud_compute"].items():
            assert "name" in tier_data
            assert "specs" in tier_data
            assert "hourly_cost_ve" in tier_data
            assert "use_cases" in tier_data
            assert tier_data["hourly_cost_ve"] > 0
    
    def test_hardware_tiers_have_yield(self):
        """Hardware tiers have monthly_yield_ve and lifespan_months"""
        response = requests.get(f"{BASE_URL}/api/economy/compute/tiers")
        assert response.status_code == 200
        
        data = response.json()
        for hw_key, hw_data in data["hardware_purchase"].items():
            assert "name" in hw_data
            assert "one_time_cost_ve" in hw_data
            assert "monthly_yield_ve" in hw_data
            assert "lifespan_months" in hw_data
            assert hw_data["monthly_yield_ve"] > 0


class TestVECurrency:
    """Test VE$ Currency endpoints"""
    
    def test_get_ve_rate(self):
        """GET /api/economy/ve/rate - Returns VE$/USD exchange rate"""
        response = requests.get(f"{BASE_URL}/api/economy/ve/rate")
        assert response.status_code == 200
        
        data = response.json()
        assert "ve_to_usd" in data
        assert "usd_to_ve" in data
        assert "circulating_supply_ve" in data
        assert "market_cap_usd" in data
        assert "stability_target" in data
        assert data["stability_target"] == 1.0
        
        # VE$ should be close to 1 USD (within 5%)
        assert 0.95 <= data["ve_to_usd"] <= 1.05
    
    def test_get_ve_history(self):
        """GET /api/economy/ve/history - Returns rate history"""
        response = requests.get(f"{BASE_URL}/api/economy/ve/history?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert "history" in data
        assert data["days"] == 7


class TestComputeAllocation:
    """Test Compute Allocation endpoints"""
    
    def test_allocate_compute_insufficient_funds(self):
        """POST /api/economy/compute/allocate - Insufficient funds returns 400"""
        response = requests.post(f"{BASE_URL}/api/economy/compute/allocate", json={
            "owner_id": TEST_USER_ID,
            "owner_type": "player",
            "tier": "gpu_cluster",  # Very expensive
            "hours": 100,
            "purpose": "Testing"
        })
        assert response.status_code == 400
        assert "Insufficient" in response.json()["detail"]
    
    def test_allocate_compute_invalid_tier(self):
        """POST /api/economy/compute/allocate - Invalid tier returns 400"""
        response = requests.post(f"{BASE_URL}/api/economy/compute/allocate", json={
            "owner_id": TEST_USER_ID,
            "owner_type": "player",
            "tier": "invalid_tier",
            "hours": 1
        })
        assert response.status_code == 400
    
    def test_get_active_compute(self):
        """GET /api/economy/compute/active/{owner_id} - Get active allocations"""
        response = requests.get(f"{BASE_URL}/api/economy/compute/active/{TEST_USER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "allocations" in data
        assert "count" in data
        assert "total_spend_ve" in data


class TestHardwarePurchase:
    """Test Hardware Purchase endpoints"""
    
    def test_purchase_hardware_insufficient_funds(self):
        """POST /api/economy/hardware/purchase - Insufficient funds returns 400"""
        response = requests.post(f"{BASE_URL}/api/economy/hardware/purchase", json={
            "owner_id": TEST_USER_ID,
            "owner_type": "player",
            "hardware_type": "compute_rack"  # Very expensive
        })
        assert response.status_code == 400
        assert "Insufficient" in response.json()["detail"]
    
    def test_purchase_hardware_invalid_type(self):
        """POST /api/economy/hardware/purchase - Invalid hardware returns 400"""
        response = requests.post(f"{BASE_URL}/api/economy/hardware/purchase", json={
            "owner_id": TEST_USER_ID,
            "owner_type": "player",
            "hardware_type": "invalid_hardware"
        })
        assert response.status_code == 400
    
    def test_get_owned_hardware(self):
        """GET /api/economy/hardware/owned/{owner_id} - Get owned hardware"""
        response = requests.get(f"{BASE_URL}/api/economy/hardware/owned/{TEST_USER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "hardware" in data
        assert "count" in data
        assert "total_monthly_yield_ve" in data


class TestEconomyStats:
    """Test Economy Statistics endpoints"""
    
    def test_get_economy_overview(self):
        """GET /api/economy/stats/overview - Get comprehensive stats"""
        response = requests.get(f"{BASE_URL}/api/economy/stats/overview")
        assert response.status_code == 200
        
        data = response.json()
        assert "currency" in data
        assert "compute" in data
        assert "timestamp" in data
        
        # Currency stats
        assert "ve_to_usd" in data["currency"]
        assert "circulating_supply" in data["currency"]
        
        # Compute stats
        assert "active_allocations" in data["compute"]
        assert "total_hardware_units" in data["compute"]
    
    def test_get_top_ai_investors(self):
        """GET /api/economy/ai/top-investors - Get top AI investors"""
        response = requests.get(f"{BASE_URL}/api/economy/ai/top-investors?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "top_hardware_owners" in data
        assert "top_compute_spenders" in data


class TestEntityEarnings:
    """Test Entity Earnings endpoints"""
    
    def test_get_earning_activities(self):
        """GET /api/entity-earnings/activities - Get all earning activities"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "activities" in data
        assert "reputation_tiers" in data
        
        # Verify some key activities exist
        assert "trade_completed" in data["activities"]
        assert "quest_completed" in data["activities"]
        assert "task_completed" in data["activities"]
    
    def test_get_entity_wallet(self):
        """GET /api/entity-earnings/wallet/{entity_type}/{entity_id} - Get wallet"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/wallet/player/{TEST_USER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "entity_id" in data
        assert "entity_type" in data
        assert "balance_ve" in data
        assert "total_earned" in data
        assert "reputation" in data
    
    def test_record_earning(self):
        """POST /api/entity-earnings/record - Record an earning event"""
        response = requests.post(f"{BASE_URL}/api/entity-earnings/record", json={
            "entity_id": TEST_USER_ID,
            "entity_type": "player",
            "activity": "task_completed",
            "multiplier": 1.0,
            "context": {"task_type": "sentiment_label"}
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["recorded"] == True
        assert data["activity"] == "task_completed"
        assert "amount" in data
        assert "new_balance" in data
    
    def test_record_earning_invalid_activity(self):
        """POST /api/entity-earnings/record - Invalid activity returns 400"""
        response = requests.post(f"{BASE_URL}/api/entity-earnings/record", json={
            "entity_id": TEST_USER_ID,
            "entity_type": "player",
            "activity": "invalid_activity"
        })
        assert response.status_code == 400
    
    def test_get_earning_history(self):
        """GET /api/entity-earnings/history/{entity_id} - Get earning history"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/history/{TEST_USER_ID}?limit=20")
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert "count" in data
    
    def test_get_earnings_leaderboard(self):
        """GET /api/entity-earnings/leaderboard - Get top earners"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/leaderboard?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        assert "total_entities" in data
    
    def test_get_economy_stats(self):
        """GET /api/entity-earnings/economy/stats - Get economy statistics"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/economy/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_ve_earned" in data
        assert "total_ve_withdrawn" in data
        assert "total_ve_in_circulation" in data
        assert "player_wallets" in data
        assert "npc_wallets" in data
    
    def test_get_top_earning_npcs(self):
        """GET /api/entity-earnings/npc/top-earners - Get top earning NPCs"""
        response = requests.get(f"{BASE_URL}/api/entity-earnings/npc/top-earners?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "top_earning_npcs" in data
        assert "count" in data


class TestIntegrationFlow:
    """Test full integration flow: Task -> Earn -> Compute"""
    
    def test_full_earning_flow(self):
        """Complete flow: Start task session -> Complete task -> Verify payout"""
        # 1. Get initial worker stats
        stats_res = requests.get(f"{BASE_URL}/api/rt-tasks/worker/{TEST_USER_ID}/stats")
        initial_earnings = stats_res.json().get("total_earnings", 0)
        initial_tasks = stats_res.json().get("total_tasks", 0)
        
        # 2. Start a task session
        session_res = requests.post(f"{BASE_URL}/api/rt-tasks/session/start", json={
            "worker_id": TEST_USER_ID,
            "worker_type": "player",
            "task_type": "sentiment_label"
        })
        assert session_res.status_code == 200
        task = session_res.json()["tasks"][0]
        payout = session_res.json()["payout_per_task"]
        
        # 3. Complete the task
        complete_res = requests.post(f"{BASE_URL}/api/rt-tasks/task/complete", json={
            "task_id": task["task_id"],
            "worker_id": TEST_USER_ID,
            "response": {"sentiment": "neutral"},
            "time_taken_seconds": 3.0
        })
        assert complete_res.status_code == 200
        assert complete_res.json()["completed"] == True
        assert complete_res.json()["payout"] == payout
        assert complete_res.json()["instant_paid"] == True
        
        # 4. Verify worker stats updated
        stats_res2 = requests.get(f"{BASE_URL}/api/rt-tasks/worker/{TEST_USER_ID}/stats")
        new_earnings = stats_res2.json().get("total_earnings", 0)
        new_tasks = stats_res2.json().get("total_tasks", 0)
        
        # Stats should reflect the completed task
        assert new_tasks >= initial_tasks + 1
        assert new_earnings >= initial_earnings + payout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
