"""
Test P2 Features - Iteration 17
- World Map UI with 8 regions
- Unity WebGL integration framework
- Enhanced micro-task providers with realistic simulated data
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USERNAME = "sirix_1"
TEST_PASSWORD = os.environ.get("SIRIX_ADMIN_PASSWORD", "test_password")
WORLD_ID = "main-story-realm"


class TestWorldMapAPI:
    """World Map API tests - 8 regions with terrain and roads"""
    
    def test_world_map_config(self):
        """Test world map config returns 8 regions and terrain types"""
        response = requests.get(f"{BASE_URL}/api/world-map/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "regions" in data, "Response should contain regions"
        assert "terrain_types" in data, "Response should contain terrain_types"
        
        # Verify 8 regions exist
        regions = data["regions"]
        expected_regions = [
            "village_square", "oracle_sanctum", "the_forge", "ancient_library",
            "wanderers_rest", "shadow_grove", "watchtower", "outer_realms"
        ]
        for region_id in expected_regions:
            assert region_id in regions, f"Region {region_id} should exist"
            region = regions[region_id]
            assert "name" in region, f"Region {region_id} should have name"
            assert "position" in region, f"Region {region_id} should have position"
            assert "size" in region, f"Region {region_id} should have size"
            assert "terrain" in region, f"Region {region_id} should have terrain"
            assert "color" in region, f"Region {region_id} should have color"
            assert "connectedTo" in region, f"Region {region_id} should have connectedTo"
        
        print(f"PASS: World map config returns {len(regions)} regions with terrain types")
    
    def test_world_map_get_or_create(self):
        """Test getting world map - auto-creates if not exists"""
        response = requests.get(f"{BASE_URL}/api/world-map/{WORLD_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "world_id" in data, "Response should contain world_id"
        assert "seed" in data, "Response should contain seed"
        assert "regions" in data, "Response should contain regions"
        assert "roads" in data, "Response should contain roads"
        
        # Verify roads connect regions
        roads = data["roads"]
        assert len(roads) > 0, "Map should have roads connecting regions"
        for road in roads:
            assert "from_region" in road, "Road should have from_region"
            assert "to_region" in road, "Road should have to_region"
            assert "from_pos" in road, "Road should have from_pos"
            assert "to_pos" in road, "Road should have to_pos"
        
        print(f"PASS: World map has {len(roads)} roads connecting regions")
    
    def test_world_map_entities(self):
        """Test getting entities on the map"""
        response = requests.get(f"{BASE_URL}/api/world-map/{WORLD_ID}/entities")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "entities" in data, "Response should contain entities"
        assert "count" in data, "Response should contain count"
        
        print(f"PASS: World map entities endpoint returns {data['count']} entities")
    
    def test_world_map_region_details(self):
        """Test getting region details with NPCs and entities"""
        region_id = "village_square"
        response = requests.get(f"{BASE_URL}/api/world-map/{WORLD_ID}/region/{region_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "region_id" in data, "Response should contain region_id"
        assert "region" in data, "Response should contain region"
        assert "entities" in data, "Response should contain entities"
        assert "buildings" in data, "Response should contain buildings"
        assert "npcs" in data, "Response should contain npcs"
        assert "entity_count" in data, "Response should contain entity_count"
        assert "building_count" in data, "Response should contain building_count"
        
        # Verify region data
        region = data["region"]
        assert region["name"] == "The Hollow Square", f"Expected 'The Hollow Square', got {region.get('name')}"
        assert "connectedTo" in region, "Region should have connectedTo"
        
        print(f"PASS: Region details for {region_id} - {data['entity_count']} entities, {data['building_count']} buildings")
    
    def test_world_map_region_not_found(self):
        """Test 404 for non-existent region"""
        response = requests.get(f"{BASE_URL}/api/world-map/{WORLD_ID}/region/nonexistent_region")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent region returns 404")
    
    def test_world_map_stats(self):
        """Test world map statistics"""
        response = requests.get(f"{BASE_URL}/api/world-map/{WORLD_ID}/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total_entities" in data, "Response should contain total_entities"
        assert "total_buildings" in data, "Response should contain total_buildings"
        assert "total_modifications" in data, "Response should contain total_modifications"
        
        print(f"PASS: World map stats - {data['total_entities']} entities, {data['total_buildings']} buildings")
    
    def test_world_map_export(self):
        """Test exporting map for 3D engine"""
        response = requests.get(f"{BASE_URL}/api/world-map/{WORLD_ID}/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "version" in data, "Export should contain version"
        assert "world_id" in data, "Export should contain world_id"
        assert "seed" in data, "Export should contain seed"
        assert "dimensions" in data, "Export should contain dimensions"
        assert "regions" in data, "Export should contain regions"
        assert "terrain_types" in data, "Export should contain terrain_types"
        assert "roads" in data, "Export should contain roads"
        
        print(f"PASS: World map export for engine - version {data['version']}")


class TestUnityWebGLAPI:
    """Unity WebGL integration framework tests"""
    
    def test_unity_config(self):
        """Test Unity config returns supported platforms and features"""
        response = requests.get(f"{BASE_URL}/api/unity/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "supported_platforms" in data, "Response should contain supported_platforms"
        assert "features" in data, "Response should contain features"
        assert "api_version" in data, "Response should contain api_version"
        assert "sync_interval_ms" in data, "Response should contain sync_interval_ms"
        
        # Verify platforms
        platforms = data["supported_platforms"]
        assert "windows" in platforms, "Should support windows"
        assert "mac" in platforms, "Should support mac"
        assert "linux" in platforms, "Should support linux"
        assert "webgl" in platforms, "Should support webgl"
        
        # Verify features
        features = data["features"]
        assert "cross_platform_sync" in features, "Should have cross_platform_sync feature"
        assert "real_time_chat" in features, "Should have real_time_chat feature"
        assert "3d_combat" in features, "Should have 3d_combat feature"
        
        print(f"PASS: Unity config - {len(platforms)} platforms, {len(features)} features")
    
    def test_unity_downloads(self):
        """Test Unity download links"""
        response = requests.get(f"{BASE_URL}/api/unity/downloads")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "windows" in data, "Response should contain windows download"
        assert "mac" in data, "Response should contain mac download"
        assert "linux" in data, "Response should contain linux download"
        assert "version" in data, "Response should contain version"
        assert "release_date" in data, "Response should contain release_date"
        assert "changelog" in data, "Response should contain changelog"
        assert "requirements" in data, "Response should contain requirements"
        
        print(f"PASS: Unity downloads - version {data['version']}, released {data['release_date']}")
    
    def test_unity_stats(self):
        """Test Unity platform statistics"""
        response = requests.get(f"{BASE_URL}/api/unity/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "active_sessions" in data, "Response should contain active_sessions"
        assert "platforms" in data, "Response should contain platforms"
        assert "total_sessions_ever" in data, "Response should contain total_sessions_ever"
        assert "timestamp" in data, "Response should contain timestamp"
        
        print(f"PASS: Unity stats - {data['active_sessions']} active sessions")


class TestEnhancedTaskProviders:
    """Enhanced micro-task providers with realistic simulated data"""
    
    def test_task_types(self):
        """Test all task types are available"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "task_types" in data, "Response should contain task_types"
        assert "providers" in data, "Response should contain providers"
        
        task_types = data["task_types"]
        
        # Verify enhanced task types exist
        expected_types = [
            "sentiment_label", "content_rating", "npc_dialogue_rating",
            "response_ranking", "world_description", "spam_detection",
            "text_categorization", "image_tagging", "image_comparison"
        ]
        
        for task_type in expected_types:
            assert task_type in task_types, f"Task type {task_type} should exist"
            task = task_types[task_type]
            assert "name" in task, f"Task {task_type} should have name"
            assert "description" in task, f"Task {task_type} should have description"
            assert "payout_per_task" in task, f"Task {task_type} should have payout_per_task"
            assert "skill_xp" in task, f"Task {task_type} should have skill_xp"
        
        print(f"PASS: {len(task_types)} task types available with payouts and skill XP")
    
    def test_task_providers(self):
        """Test task providers configuration"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/types")
        assert response.status_code == 200
        
        data = response.json()
        providers = data["providers"]
        
        # Verify providers
        assert "internal" in providers, "Should have internal provider"
        assert "clickworker" in providers, "Should have clickworker provider"
        assert "toloka" in providers, "Should have toloka provider"
        assert "appen" in providers, "Should have appen provider"
        
        print(f"PASS: {len(providers)} task providers configured")
    
    def test_start_sentiment_task_session(self):
        """Test starting a sentiment labeling task session with realistic data"""
        response = requests.post(
            f"{BASE_URL}/api/rt-tasks/session/start",
            json={
                "worker_id": "test_worker_sentiment",
                "worker_type": "player",
                "task_type": "sentiment_label"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "session_id" in data, "Response should contain session_id"
        assert "tasks" in data, "Response should contain tasks"
        assert "payout_per_task" in data, "Response should contain payout_per_task"
        assert "estimated_hourly" in data, "Response should contain estimated_hourly"
        
        # Verify tasks have realistic sentiment data
        tasks = data["tasks"]
        assert len(tasks) > 0, "Should have tasks in batch"
        
        for task in tasks:
            task_data = task["data"]
            assert "text" in task_data, "Sentiment task should have text"
            assert "options" in task_data, "Sentiment task should have options"
            assert "instructions" in task_data, "Sentiment task should have instructions"
            assert "provider_hint" in task_data, "Sentiment task should have provider_hint"
            # Verify ground truth for quality tracking
            assert "_ground_truth" in task_data, "Sentiment task should have _ground_truth"
            assert task_data["_ground_truth"] in ["positive", "negative", "neutral"]
        
        print(f"PASS: Sentiment task session started with {len(tasks)} realistic tasks")
        return data["session_id"]
    
    def test_start_content_rating_session(self):
        """Test content rating task with realistic samples"""
        response = requests.post(
            f"{BASE_URL}/api/rt-tasks/session/start",
            json={
                "worker_id": "test_worker_content",
                "worker_type": "player",
                "task_type": "content_rating"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        tasks = data["tasks"]
        
        for task in tasks:
            task_data = task["data"]
            assert "content_preview" in task_data, "Content task should have content_preview"
            assert "content_type" in task_data, "Content task should have content_type"
            assert "options" in task_data, "Content task should have options"
            assert "_ground_truth" in task_data, "Content task should have _ground_truth"
            assert task_data["_ground_truth"] in ["safe", "questionable", "unsafe"]
        
        print(f"PASS: Content rating session with {len(tasks)} tasks including ground truth")
    
    def test_start_npc_dialogue_rating_session(self):
        """Test NPC dialogue rating task with game-specific samples"""
        response = requests.post(
            f"{BASE_URL}/api/rt-tasks/session/start",
            json={
                "worker_id": "test_worker_npc",
                "worker_type": "player",
                "task_type": "npc_dialogue_rating"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        tasks = data["tasks"]
        
        for task in tasks:
            task_data = task["data"]
            assert "npc_name" in task_data, "NPC task should have npc_name"
            assert "dialogue" in task_data, "NPC task should have dialogue"
            assert "context" in task_data, "NPC task should have context"
            assert "criteria" in task_data, "NPC task should have criteria"
            assert "scale" in task_data, "NPC task should have scale"
            assert "provider_hint" in task_data, "NPC task should have provider_hint"
            
            # Verify criteria for rating
            criteria = task_data["criteria"]
            assert "naturalness" in criteria, "Should rate naturalness"
            assert "relevance" in criteria, "Should rate relevance"
            assert "engagement" in criteria, "Should rate engagement"
        
        print(f"PASS: NPC dialogue rating session with {len(tasks)} game-specific tasks")
    
    def test_start_response_ranking_session(self):
        """Test AI response ranking task"""
        response = requests.post(
            f"{BASE_URL}/api/rt-tasks/session/start",
            json={
                "worker_id": "test_worker_ranking",
                "worker_type": "player",
                "task_type": "response_ranking"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        tasks = data["tasks"]
        
        for task in tasks:
            task_data = task["data"]
            assert "prompt" in task_data, "Ranking task should have prompt"
            assert "responses" in task_data, "Ranking task should have responses"
            assert "criteria" in task_data, "Ranking task should have criteria"
            assert len(task_data["responses"]) >= 2, "Should have multiple responses to rank"
        
        print(f"PASS: Response ranking session with {len(tasks)} RLHF-style tasks")
    
    def test_start_world_description_session(self):
        """Test world description writing task"""
        response = requests.post(
            f"{BASE_URL}/api/rt-tasks/session/start",
            json={
                "worker_id": "test_worker_world",
                "worker_type": "player",
                "task_type": "world_description"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        tasks = data["tasks"]
        
        for task in tasks:
            task_data = task["data"]
            assert "location_name" in task_data, "World task should have location_name"
            assert "style" in task_data, "World task should have style"
            assert "required_elements" in task_data, "World task should have required_elements"
            assert "requirements" in task_data, "World task should have requirements"
            
            # Verify requirements
            reqs = task_data["requirements"]
            assert "min_words" in reqs, "Should have min_words requirement"
            assert "max_words" in reqs, "Should have max_words requirement"
        
        print(f"PASS: World description session with {len(tasks)} creative writing tasks")
    
    def test_complete_task(self):
        """Test completing a task and receiving payout"""
        # Start a session first
        start_response = requests.post(
            f"{BASE_URL}/api/rt-tasks/session/start",
            json={
                "worker_id": "test_worker_complete",
                "worker_type": "player",
                "task_type": "sentiment_label"
            }
        )
        assert start_response.status_code == 200
        
        session_data = start_response.json()
        task = session_data["tasks"][0]
        task_id = task["task_id"]
        
        # Complete the task
        complete_response = requests.post(
            f"{BASE_URL}/api/rt-tasks/task/complete",
            json={
                "task_id": task_id,
                "worker_id": "test_worker_complete",
                "response": {"sentiment": "positive"},
                "time_taken_seconds": 5.0
            }
        )
        assert complete_response.status_code == 200, f"Expected 200, got {complete_response.status_code}"
        
        data = complete_response.json()
        assert data["completed"] == True, "Task should be marked completed"
        assert "payout" in data, "Response should contain payout"
        assert "skill_xp" in data, "Response should contain skill_xp"
        
        print(f"PASS: Task completed with payout {data['payout']} VE$")
    
    def test_worker_stats(self):
        """Test getting worker statistics"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/worker/test_worker_complete/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "worker_id" in data, "Response should contain worker_id"
        assert "total_tasks" in data, "Response should contain total_tasks"
        assert "total_earnings" in data, "Response should contain total_earnings"
        
        print(f"PASS: Worker stats - {data['total_tasks']} tasks, {data['total_earnings']} VE$ earned")
    
    def test_platform_stats(self):
        """Test platform-wide statistics"""
        response = requests.get(f"{BASE_URL}/api/rt-tasks/platform/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "tasks_completed_hour" in data, "Response should contain tasks_completed_hour"
        assert "tasks_completed_day" in data, "Response should contain tasks_completed_day"
        assert "active_workers" in data, "Response should contain active_workers"
        assert "task_types_available" in data, "Response should contain task_types_available"
        
        print(f"PASS: Platform stats - {data['task_types_available']} task types available")


class TestModeSelectionIntegration:
    """Test Mode Selection page integration with new features"""
    
    def test_auth_login(self):
        """Test login to get user context"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.status_code}"
        
        data = response.json()
        assert "user" in data, "Response should contain user"
        assert "id" in data["user"], "User should contain id"
        print(f"PASS: Login successful for {TEST_USERNAME}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
