"""
Test Conversation History Feature - Iteration 12
Tests for Chat History page, conversation APIs, and resume functionality
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-realm-ai.preview.emergentagent.com').rstrip('/')

# Test data
TEST_PLAYER_ID = f"test-player-{uuid.uuid4().hex[:8]}"
TEST_CHARACTER_ID = f"test-char-{uuid.uuid4().hex[:8]}"
TEST_CONVERSATION_ID = None


class TestConversationHistoryAPIs:
    """Test conversation history endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.player_id = TEST_PLAYER_ID
        self.character_id = TEST_CHARACTER_ID
        self.conversation_id = None
    
    def test_01_create_conversation(self):
        """Test POST /api/conversations/create - Create a new conversation"""
        global TEST_CONVERSATION_ID
        
        response = requests.post(f"{BASE_URL}/api/conversations/create", json={
            "player_id": self.player_id,
            "character_id": self.character_id,
            "npc_id": "elder-morvain",
            "npc_name": "Elder Morvain",
            "location_id": "village_square",
            "location_name": "The Hollow Square"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["created"] == True
        assert "conversation_id" in data
        assert data["conversation"]["player_id"] == self.player_id
        assert data["conversation"]["npc_name"] == "Elder Morvain"
        assert data["conversation"]["location_name"] == "The Hollow Square"
        
        TEST_CONVERSATION_ID = data["conversation_id"]
        self.conversation_id = TEST_CONVERSATION_ID
        print(f"Created conversation: {TEST_CONVERSATION_ID}")
    
    def test_02_add_messages_bulk(self):
        """Test POST /api/conversations/{id}/messages/bulk - Add multiple messages"""
        global TEST_CONVERSATION_ID
        
        if not TEST_CONVERSATION_ID:
            pytest.skip("No conversation ID from previous test")
        
        response = requests.post(f"{BASE_URL}/api/conversations/{TEST_CONVERSATION_ID}/messages/bulk", json=[
            {"role": "user", "content": "Hello Elder Morvain, I seek wisdom about the echoes."},
            {"role": "assistant", "content": "Greetings, young traveler. The echoes of the past whisper many secrets to those who listen."},
            {"role": "user", "content": "What secrets do they hold?"},
            {"role": "assistant", "content": "They speak of ancient times, of heroes and villains, of magic that once flowed freely through these lands."}
        ])
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["added"] == True
        assert data["count"] == 4
        print(f"Added 4 messages to conversation")
    
    def test_03_get_player_conversations_by_npc(self):
        """Test GET /api/conversations/player/{id}?group_by=npc - Get conversations grouped by NPC"""
        response = requests.get(f"{BASE_URL}/api/conversations/player/{self.player_id}?group_by=npc")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["group_by"] == "npc"
        assert "groups" in data
        assert data["total_conversations"] >= 1
        
        # Verify NPC grouping structure
        if data["groups"]:
            group = data["groups"][0]
            assert "npc_name" in group
            assert "conversations" in group
            assert "total_messages" in group
            print(f"Found {len(data['groups'])} NPC groups with {data['total_conversations']} total conversations")
    
    def test_04_get_player_conversations_by_session(self):
        """Test GET /api/conversations/player/{id}?group_by=session - Get conversations grouped by date"""
        response = requests.get(f"{BASE_URL}/api/conversations/player/{self.player_id}?group_by=session")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["group_by"] == "session"
        assert "groups" in data
        
        # Verify session grouping structure
        if data["groups"]:
            group = data["groups"][0]
            assert "date" in group
            assert "conversations" in group
            assert "total_messages" in group
            print(f"Found {len(data['groups'])} session groups")
    
    def test_05_get_player_stats(self):
        """Test GET /api/conversations/player/{id}/stats - Get conversation statistics"""
        response = requests.get(f"{BASE_URL}/api/conversations/player/{self.player_id}/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_conversations" in data
        assert "total_messages" in data
        assert "unique_npcs" in data
        assert "unique_locations" in data
        assert "unique_npcs_count" in data
        assert "unique_locations_count" in data
        
        assert data["total_conversations"] >= 1
        assert data["total_messages"] >= 4
        print(f"Stats: {data['total_conversations']} conversations, {data['total_messages']} messages, {data['unique_npcs_count']} NPCs")
    
    def test_06_get_conversation_detail(self):
        """Test GET /api/conversations/{id} - Get full conversation with messages"""
        global TEST_CONVERSATION_ID
        
        if not TEST_CONVERSATION_ID:
            pytest.skip("No conversation ID from previous test")
        
        response = requests.get(f"{BASE_URL}/api/conversations/{TEST_CONVERSATION_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "conversation" in data
        conv = data["conversation"]
        assert conv["conversation_id"] == TEST_CONVERSATION_ID
        assert "messages" in conv
        assert len(conv["messages"]) >= 4
        print(f"Conversation has {len(conv['messages'])} messages")
    
    def test_07_resume_conversation(self):
        """Test POST /api/conversations/resume - Resume a conversation"""
        global TEST_CONVERSATION_ID
        
        if not TEST_CONVERSATION_ID:
            pytest.skip("No conversation ID from previous test")
        
        response = requests.post(f"{BASE_URL}/api/conversations/resume", json={
            "conversation_id": TEST_CONVERSATION_ID,
            "player_id": self.player_id
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["resumed"] == True
        assert data["conversation_id"] == TEST_CONVERSATION_ID
        assert data["npc_name"] == "Elder Morvain"
        assert data["location_name"] == "The Hollow Square"
        assert "context_messages" in data
        assert data["can_continue"] == True
        print(f"Resume returned {len(data['context_messages'])} context messages")
    
    def test_08_search_conversations(self):
        """Test GET /api/conversations/player/{id}/search - Search conversations"""
        response = requests.get(f"{BASE_URL}/api/conversations/player/{self.player_id}/search?query=wisdom")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "query" in data
        assert data["query"] == "wisdom"
        assert "results" in data
        assert "total_results" in data
        print(f"Search found {data['total_results']} results for 'wisdom'")
    
    def test_09_add_single_message(self):
        """Test POST /api/conversations/{id}/message - Add a single message"""
        global TEST_CONVERSATION_ID
        
        if not TEST_CONVERSATION_ID:
            pytest.skip("No conversation ID from previous test")
        
        response = requests.post(f"{BASE_URL}/api/conversations/{TEST_CONVERSATION_ID}/message", json={
            "role": "user",
            "content": "Thank you for sharing your wisdom, Elder."
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["added"] == True
        assert "message_id" in data
        assert "timestamp" in data
        print(f"Added single message with ID: {data['message_id']}")
    
    def test_10_end_conversation(self):
        """Test POST /api/conversations/{id}/end - End a conversation"""
        global TEST_CONVERSATION_ID
        
        if not TEST_CONVERSATION_ID:
            pytest.skip("No conversation ID from previous test")
        
        response = requests.post(f"{BASE_URL}/api/conversations/{TEST_CONVERSATION_ID}/end")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ended"] == True
        assert data["conversation_id"] == TEST_CONVERSATION_ID
        print(f"Conversation ended successfully")
    
    def test_11_conversation_not_found(self):
        """Test 404 for non-existent conversation"""
        response = requests.get(f"{BASE_URL}/api/conversations/non-existent-id-12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent conversation")
    
    def test_12_resume_not_found(self):
        """Test 404 for resuming non-existent conversation"""
        response = requests.post(f"{BASE_URL}/api/conversations/resume", json={
            "conversation_id": "non-existent-id-12345",
            "player_id": self.player_id
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for resuming non-existent conversation")


class TestConversationHistoryWithMultipleNPCs:
    """Test conversation history with multiple NPCs for grouping"""
    
    def test_create_multiple_conversations(self):
        """Create conversations with different NPCs to test grouping"""
        player_id = f"test-multi-{uuid.uuid4().hex[:8]}"
        
        npcs = [
            {"npc_id": "lyra", "npc_name": "Lyra the Wanderer", "location_id": "wanderers_rest", "location_name": "The Wanderer's Rest"},
            {"npc_id": "kael", "npc_name": "Kael Ironbrand", "location_id": "the_forge", "location_name": "The Ember Forge"},
            {"npc_id": "oracle", "npc_name": "Oracle Veythra", "location_id": "oracle_sanctum", "location_name": "The Oracle's Sanctum"}
        ]
        
        for npc in npcs:
            # Create conversation
            response = requests.post(f"{BASE_URL}/api/conversations/create", json={
                "player_id": player_id,
                "character_id": "test-char",
                **npc
            })
            assert response.status_code == 200
            conv_id = response.json()["conversation_id"]
            
            # Add messages
            response = requests.post(f"{BASE_URL}/api/conversations/{conv_id}/messages/bulk", json=[
                {"role": "user", "content": f"Hello {npc['npc_name']}!"},
                {"role": "assistant", "content": f"Greetings, traveler. Welcome to {npc['location_name']}."}
            ])
            assert response.status_code == 200
        
        # Verify grouping by NPC
        response = requests.get(f"{BASE_URL}/api/conversations/player/{player_id}?group_by=npc")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_npcs"] == 3, f"Expected 3 NPCs, got {data['total_npcs']}"
        assert data["total_conversations"] == 3
        print(f"Created 3 conversations with different NPCs, grouped correctly")
        
        # Verify stats
        response = requests.get(f"{BASE_URL}/api/conversations/player/{player_id}/stats")
        assert response.status_code == 200
        stats = response.json()
        
        assert stats["unique_npcs_count"] == 3
        assert stats["unique_locations_count"] == 3
        assert stats["total_messages"] == 6
        print(f"Stats verified: 3 NPCs, 3 locations, 6 messages")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
