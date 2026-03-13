import requests
import sys
import json
from datetime import datetime

class AIVillageAPITester:
    def __init__(self, base_url="https://story-realm-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.character_id = None
        self.user_id = f"test_user_{datetime.now().strftime('%H%M%S')}"
        self.conversation_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Timeout (30s)")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )

    def test_get_locations(self):
        """Test GET /api/locations"""
        success, response = self.run_test(
            "Get Village Locations",
            "GET", 
            "locations",
            200
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            print(f"   Found {len(response)} locations")
            # Check if required fields exist in first location
            first_loc = response[0]
            required_fields = ['id', 'name', 'description', 'atmosphere']
            missing_fields = [f for f in required_fields if f not in first_loc]
            if missing_fields:
                print(f"   ⚠️  Missing fields in location: {missing_fields}")
            else:
                print(f"   ✅ Location structure valid")
        
        return success, response

    def test_create_character(self):
        """Test POST /api/characters"""
        character_data = {
            "user_id": self.user_id,
            "name": "Test Wanderer",
            "background": "A mysterious traveler testing the AI Village systems.",
            "traits": ["Curious", "Brave"],
            "appearance": "A figure cloaked in digital mist."
        }
        
        success, response = self.run_test(
            "Create Character",
            "POST",
            "characters", 
            200,  # Backend returns 200, not 201
            data=character_data
        )
        
        if success and 'id' in response:
            self.character_id = response['id']
            print(f"   Created character ID: {self.character_id}")
        
        return success, response

    def test_get_character(self):
        """Test GET /api/character/{character_id}"""
        if not self.character_id:
            print("❌ Cannot test - No character ID available")
            return False, {}
            
        return self.run_test(
            "Get Character by ID",
            "GET",
            f"character/{self.character_id}",
            200
        )

    def test_update_character_location(self):
        """Test PUT /api/character/{character_id}/location"""
        if not self.character_id:
            print("❌ Cannot test - No character ID available")
            return False, {}
        
        return self.run_test(
            "Update Character Location",
            "PUT",
            f"character/{self.character_id}/location?location_id=the_forge",
            200
        )

    def test_chat_functionality(self):
        """Test POST /api/chat with AI integration"""
        if not self.character_id:
            print("❌ Cannot test - No character ID available")
            return False, {}
        
        chat_data = {
            "character_id": self.character_id,
            "location_id": "village_square", 
            "message": "Hello! I am testing the AI storytelling system."
        }
        
        print(f"   Testing AI chat (may take 10-15 seconds)...")
        success, response = self.run_test(
            "AI Chat Response",
            "POST",
            "chat",
            200,
            data=chat_data
        )
        
        if success and 'conversation_id' in response and 'response' in response:
            self.conversation_id = response['conversation_id']
            print(f"   Conversation ID: {self.conversation_id}")
            print(f"   AI Response length: {len(response['response'])} characters")
            if len(response['response']) > 50:
                print(f"   ✅ AI generated meaningful response")
            else:
                print(f"   ⚠️  AI response seems short: {response['response']}")
        
        return success, response

    def test_get_conversations(self):
        """Test GET /api/conversations/{character_id}"""
        if not self.character_id:
            print("❌ Cannot test - No character ID available") 
            return False, {}
        
        return self.run_test(
            "Get Character Conversations",
            "GET",
            f"conversations/{self.character_id}",
            200
        )

    def test_dataspace_stats(self):
        """Test GET /api/dataspace/stats"""
        return self.run_test(
            "Get Dataspace Stats",
            "GET",
            "dataspace/stats",
            200
        )

    def test_get_dataspace(self):
        """Test GET /api/dataspace"""
        return self.run_test(
            "Get Dataspace Entries", 
            "GET",
            "dataspace",
            200
        )

def main():
    """Run all API tests"""
    print("🚀 Starting AI Village Backend API Tests")
    print("=" * 50)
    
    tester = AIVillageAPITester()
    
    # Core API tests
    tests = [
        tester.test_root_endpoint,
        tester.test_get_locations,
        tester.test_create_character,
        tester.test_get_character,
        tester.test_update_character_location,
        tester.test_chat_functionality,  # This tests the AI integration
        tester.test_get_conversations,
        tester.test_dataspace_stats,
        tester.test_get_dataspace,
    ]
    
    # Execute tests
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All backend tests passed!")
        return 0
    else:
        failed = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())