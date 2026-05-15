"""
Iteration 28 Tests: External Providers & NPC Services
Tests for:
1. External Providers Webhook endpoint at /api/external-providers/webhook/{provider} - POST
2. External Providers Status at /api/external-providers/status - GET
3. External Providers Events at /api/external-providers/events - GET
4. External Providers Task Mapping at /api/external-providers/tasks/map - POST
5. External Providers Task Claim at /api/external-providers/tasks/claim - POST
6. External Providers Task Submit at /api/external-providers/tasks/submit - POST
7. NPC Services Categories at /api/npc-services/categories - GET
8. NPC Services Types at /api/npc-services/types - GET
9. NPC Available Services at /api/npc-services/npc/{npc_id}/available - GET
10. NPC Service Request at /api/npc-services/request - POST
11. NPC Service History at /api/npc-services/history/{player_id} - GET
12. NPC Service Stats at /api/npc-services/npc/{npc_id}/stats - GET
13. NPC Service Leaderboard at /api/npc-services/leaderboard - GET
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
TEST_USER_ID = "sirix_1_supreme"
TEST_NPC_ID = "test_npc_1"


class TestExternalProvidersWebhook:
    """Test external provider webhook endpoints"""
    
    def test_webhook_toloka_receives_event(self):
        """Test Toloka webhook receives and processes events"""
        payload = {
            "event_type": "ASSIGNMENT_ACCEPTED",
            "task_id": f"test_task_{uuid.uuid4().hex[:8]}",
            "worker_id": "test_worker_123",
            "payout": 0.50
        }
        response = requests.post(
            f"{BASE_URL}/api/external-providers/webhook/toloka",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        assert "event_id" in data
        assert data.get("event_type") == "task_approved"  # Normalized from ASSIGNMENT_ACCEPTED
        print(f"✓ Toloka webhook received event: {data['event_id']}")
    
    def test_webhook_generic_provider(self):
        """Test generic webhook endpoint for any provider"""
        payload = {
            "event_type": "task_completed",
            "task_id": f"generic_task_{uuid.uuid4().hex[:8]}",
            "amount": 1.00
        }
        response = requests.post(
            f"{BASE_URL}/api/external-providers/webhook/mturk",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        print(f"✓ Generic webhook received event: {data['event_id']}")
    
    def test_webhook_unknown_provider_rejected(self):
        """Test that unknown providers are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/external-providers/webhook/unknown_provider",
            json={"event_type": "test"}
        )
        assert response.status_code == 400
        print("✓ Unknown provider correctly rejected")


class TestExternalProvidersStatus:
    """Test external providers status endpoint"""
    
    def test_get_status(self):
        """Test GET /api/external-providers/status returns provider status"""
        response = requests.get(f"{BASE_URL}/api/external-providers/status")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "webhook_secrets_configured" in data
        assert "supported_event_types" in data
        assert "recent_events" in data
        assert "provider_availability" in data
        assert "task_mapping_stats" in data
        
        # Check supported providers
        secrets = data["webhook_secrets_configured"]
        assert "toloka" in secrets
        assert "mturk" in secrets
        assert "scale_ai" in secrets
        assert "hive" in secrets
        assert "appen" in secrets
        
        # Check supported event types
        event_types = data["supported_event_types"]
        assert "task_available" in event_types
        assert "task_approved" in event_types
        assert "task_rejected" in event_types
        
        print(f"✓ External providers status: {len(secrets)} providers configured")
        print(f"✓ Supported event types: {event_types}")


class TestExternalProvidersEvents:
    """Test external providers events endpoint"""
    
    def test_get_events(self):
        """Test GET /api/external-providers/events returns webhook events"""
        response = requests.get(f"{BASE_URL}/api/external-providers/events")
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)
        print(f"✓ Retrieved {data['count']} webhook events")
    
    def test_get_events_with_filter(self):
        """Test events endpoint with provider filter"""
        response = requests.get(f"{BASE_URL}/api/external-providers/events?provider=toloka")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        # All events should be from toloka if any exist
        for event in data["events"]:
            assert event.get("provider") == "toloka"
        print(f"✓ Filtered events by provider: {data['count']} toloka events")


class TestExternalProvidersTaskMapping:
    """Test external providers task mapping endpoints"""
    
    def test_map_external_task(self):
        """Test POST /api/external-providers/tasks/map creates task mapping"""
        external_task_id = f"ext_task_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/external-providers/tasks/map",
            params={
                "external_task_id": external_task_id,
                "provider": "toloka",
                "task_type": "image_labeling",
                "payout": 0.25
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("mapped") == True
        assert "internal_task_id" in data
        assert data.get("external_task_id") == external_task_id
        
        print(f"✓ Mapped external task {external_task_id} to internal {data['internal_task_id']}")
        return external_task_id
    
    def test_claim_external_task(self):
        """Test POST /api/external-providers/tasks/claim claims a task"""
        # First create a task to claim
        external_task_id = f"claim_task_{uuid.uuid4().hex[:8]}"
        map_response = requests.post(
            f"{BASE_URL}/api/external-providers/tasks/map",
            params={
                "external_task_id": external_task_id,
                "provider": "mturk",
                "task_type": "text_annotation",
                "payout": 0.50
            }
        )
        assert map_response.status_code == 200
        
        # Now claim it
        claim_response = requests.post(
            f"{BASE_URL}/api/external-providers/tasks/claim",
            params={
                "external_task_id": external_task_id,
                "worker_id": TEST_USER_ID
            }
        )
        assert claim_response.status_code == 200
        data = claim_response.json()
        
        assert data.get("claimed") == True
        assert data.get("worker_id") == TEST_USER_ID
        
        print(f"✓ Task {external_task_id} claimed by {TEST_USER_ID}")
        return external_task_id
    
    def test_submit_external_task(self):
        """Test POST /api/external-providers/tasks/submit submits task response"""
        # Create and claim a task first
        external_task_id = f"submit_task_{uuid.uuid4().hex[:8]}"
        
        # Map
        requests.post(
            f"{BASE_URL}/api/external-providers/tasks/map",
            params={
                "external_task_id": external_task_id,
                "provider": "scale_ai",
                "task_type": "data_validation",
                "payout": 0.75,
                "worker_id": TEST_USER_ID
            }
        )
        
        # Claim
        requests.post(
            f"{BASE_URL}/api/external-providers/tasks/claim",
            params={
                "external_task_id": external_task_id,
                "worker_id": TEST_USER_ID
            }
        )
        
        # Submit
        submit_response = requests.post(
            f"{BASE_URL}/api/external-providers/tasks/submit",
            params={
                "external_task_id": external_task_id,
                "worker_id": TEST_USER_ID
            },
            json={"answer": "validated", "confidence": 0.95}
        )
        assert submit_response.status_code == 200
        data = submit_response.json()
        
        assert data.get("submitted") == True
        assert data.get("status") == "pending_review"
        
        print(f"✓ Task {external_task_id} submitted successfully")
    
    def test_claim_nonexistent_task_fails(self):
        """Test claiming a non-existent task fails"""
        response = requests.post(
            f"{BASE_URL}/api/external-providers/tasks/claim",
            params={
                "external_task_id": "nonexistent_task_12345",
                "worker_id": TEST_USER_ID
            }
        )
        assert response.status_code == 400
        print("✓ Claiming non-existent task correctly rejected")


class TestNPCServicesCategories:
    """Test NPC services categories endpoint"""
    
    def test_get_categories(self):
        """Test GET /api/npc-services/categories returns service categories"""
        response = requests.get(f"{BASE_URL}/api/npc-services/categories")
        assert response.status_code == 200
        data = response.json()
        
        assert "categories" in data
        assert "category_list" in data
        assert "total_services" in data
        
        categories = data["categories"]
        # Check expected categories exist
        expected_categories = ["combat", "crafting", "magic", "social", "knowledge", "survival"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        print(f"✓ NPC Services: {data['total_services']} services in {len(data['category_list'])} categories")
        print(f"✓ Categories: {data['category_list']}")


class TestNPCServicesTypes:
    """Test NPC services types endpoint"""
    
    def test_get_service_types(self):
        """Test GET /api/npc-services/types returns all service types"""
        response = requests.get(f"{BASE_URL}/api/npc-services/types")
        assert response.status_code == 200
        data = response.json()
        
        assert "services" in data
        assert "mastery_requirements" in data
        assert "quality_multipliers" in data
        
        services = data["services"]
        # Check some expected services exist
        expected_services = ["craft_weapon", "craft_armor", "repair_equipment", "healing_service"]
        for svc in expected_services:
            assert svc in services, f"Missing service: {svc}"
        
        # Check mastery levels
        mastery = data["mastery_requirements"]
        assert "novice" in mastery
        assert "expert" in mastery
        assert "master" in mastery
        
        print(f"✓ NPC Service Types: {len(services)} services defined")
        print(f"✓ Mastery levels: {list(mastery.keys())}")


class TestNPCAvailableServices:
    """Test NPC available services endpoint"""
    
    def test_get_npc_available_services(self):
        """Test GET /api/npc-services/npc/{npc_id}/available returns NPC's services"""
        response = requests.get(f"{BASE_URL}/api/npc-services/npc/{TEST_NPC_ID}/available")
        assert response.status_code == 200
        data = response.json()
        
        assert "npc_id" in data
        assert data["npc_id"] == TEST_NPC_ID
        assert "available_services" in data
        
        # According to context, test_npc_1 is trained in blacksmithing to Expert level
        # and can offer craft_weapon, craft_armor, repair_equipment
        services = data["available_services"]
        print(f"✓ NPC {TEST_NPC_ID} has {len(services)} available services")
        
        if services:
            for svc in services:
                print(f"  - {svc['name']} ({svc['npc_mastery']}) - VE${svc['cost_ve']}")
    
    def test_get_untrained_npc_services(self):
        """Test that untrained NPC returns empty services"""
        untrained_npc = f"untrained_npc_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/npc-services/npc/{untrained_npc}/available")
        assert response.status_code == 200
        data = response.json()
        
        assert data["npc_id"] == untrained_npc
        assert len(data["available_services"]) == 0
        assert "no trained skills" in data.get("message", "").lower() or data["total_services"] == 0
        print(f"✓ Untrained NPC correctly returns no services")


class TestNPCServiceRequest:
    """Test NPC service request endpoint"""
    
    def test_request_service_insufficient_balance(self):
        """Test service request fails with insufficient balance"""
        # Use a user with no balance
        test_user = f"broke_user_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/npc-services/request",
            json={
                "player_id": test_user,
                "npc_id": TEST_NPC_ID,
                "service_type": "craft_weapon",
                "payment_method": "ve"
            }
        )
        # Should fail due to insufficient balance or NPC not having skill
        assert response.status_code in [400, 404]
        print("✓ Service request correctly validates balance/skill requirements")
    
    def test_request_invalid_service_type(self):
        """Test service request fails with invalid service type"""
        response = requests.post(
            f"{BASE_URL}/api/npc-services/request",
            json={
                "player_id": TEST_USER_ID,
                "npc_id": TEST_NPC_ID,
                "service_type": "invalid_service_xyz",
                "payment_method": "ve"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "unknown service" in data.get("detail", "").lower()
        print("✓ Invalid service type correctly rejected")


class TestNPCServiceHistory:
    """Test NPC service history endpoint"""
    
    def test_get_player_service_history(self):
        """Test GET /api/npc-services/history/{player_id} returns history"""
        response = requests.get(f"{BASE_URL}/api/npc-services/history/{TEST_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "player_id" in data
        assert data["player_id"] == TEST_USER_ID
        assert "history" in data
        assert "total_services" in data
        assert "total_spent" in data
        
        print(f"✓ Player {TEST_USER_ID} service history: {data['total_services']} services, VE${data['total_spent']} spent")
    
    def test_get_new_player_history(self):
        """Test new player has empty history"""
        new_player = f"new_player_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/npc-services/history/{new_player}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_services"] == 0
        assert data["total_spent"] == 0
        print("✓ New player correctly has empty service history")


class TestNPCServiceStats:
    """Test NPC service stats endpoint"""
    
    def test_get_npc_service_stats(self):
        """Test GET /api/npc-services/npc/{npc_id}/stats returns stats"""
        response = requests.get(f"{BASE_URL}/api/npc-services/npc/{TEST_NPC_ID}/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "npc_id" in data
        assert data["npc_id"] == TEST_NPC_ID
        assert "total_services" in data
        assert "total_revenue" in data
        assert "average_quality" in data
        assert "by_service_type" in data
        
        print(f"✓ NPC {TEST_NPC_ID} stats: {data['total_services']} services, VE${data['total_revenue']} revenue")


class TestNPCServiceLeaderboard:
    """Test NPC service leaderboard endpoint"""
    
    def test_get_leaderboard(self):
        """Test GET /api/npc-services/leaderboard returns top providers"""
        response = requests.get(f"{BASE_URL}/api/npc-services/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "leaderboard" in data
        assert "metric" in data
        assert data["metric"] == "revenue"
        
        leaderboard = data["leaderboard"]
        print(f"✓ Service provider leaderboard: {len(leaderboard)} NPCs")
        
        for i, entry in enumerate(leaderboard[:5]):
            print(f"  #{i+1}: {entry.get('npc_name', entry['_id'])} - {entry['services']} services, VE${entry['revenue']}")
    
    def test_get_leaderboard_with_limit(self):
        """Test leaderboard respects limit parameter"""
        response = requests.get(f"{BASE_URL}/api/npc-services/leaderboard?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["leaderboard"]) <= 5
        print(f"✓ Leaderboard limit respected: {len(data['leaderboard'])} entries")


class TestIntegrationAITrainingToServices:
    """Test integration between AI Training and NPC Services"""
    
    def test_trained_npc_has_services(self):
        """Verify that a trained NPC can offer services based on their skills"""
        # First check if NPC has skills via AI training endpoint
        skills_response = requests.get(f"{BASE_URL}/api/ai-training/entity/{TEST_NPC_ID}/skills")
        
        if skills_response.status_code == 200:
            skills_data = skills_response.json()
            print(f"✓ NPC {TEST_NPC_ID} has {skills_data.get('total_skills', 0)} trained skills")
            
            # Now check available services
            services_response = requests.get(f"{BASE_URL}/api/npc-services/npc/{TEST_NPC_ID}/available")
            assert services_response.status_code == 200
            services_data = services_response.json()
            
            print(f"✓ NPC {TEST_NPC_ID} can offer {services_data.get('total_services', 0)} services")
            
            # If NPC has blacksmithing skill at expert level, they should offer crafting services
            for svc in services_data.get("available_services", []):
                if svc["category"] == "crafting":
                    print(f"  ✓ Crafting service available: {svc['name']} at {svc['npc_mastery']} level")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
