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

    def test_news_endpoint(self):
        """Test GET /api/news for world news integration"""
        success, response = self.run_test(
            "Get World News Headlines",
            "GET",
            "news",
            200
        )
        
        if success and isinstance(response, dict):
            if 'headlines' in response and isinstance(response['headlines'], list):
                print(f"   Found {len(response['headlines'])} news headlines")
                if len(response['headlines']) > 0:
                    print(f"   Sample headline: {response['headlines'][0][:50]}...")
                    print(f"   ✅ News integration working")
                else:
                    print(f"   ⚠️  No headlines returned")
            else:
                print(f"   ❌ Invalid response format: missing 'headlines' field")
        
        return success, response

    def test_chat_with_news_query(self):
        """Test AI chat with news-related query"""
        if not self.character_id:
            print("❌ Cannot test - No character ID available")
            return False, {}
        
        news_chat_data = {
            "character_id": self.character_id,
            "location_id": "village_square", 
            "message": "What news from the outer world?"
        }
        
        print(f"   Testing AI chat with news query (may take 10-15 seconds)...")
        success, response = self.run_test(
            "AI Chat with News Query",
            "POST",
            "chat",
            200,
            data=news_chat_data
        )
        
        if success and 'response' in response:
            ai_response = response['response'].lower()
            news_keywords = ['news', 'world', 'outer', 'realm', 'beyond', 'distant', 'happening']
            found_keywords = [kw for kw in news_keywords if kw in ai_response]
            
            print(f"   AI Response length: {len(response['response'])} characters")
            if found_keywords:
                print(f"   ✅ AI response includes news context (keywords: {', '.join(found_keywords)})")
            else:
                print(f"   ⚠️  AI response may not include news context")
        
        return success, response

    # NEW FEATURE TESTS - Multiplayer & Expansion Features
    
    def test_sirix_1_user(self):
        """Test that Sirix-1 supreme user exists"""
        success, response = self.run_test(
            "Get Sirix-1 Supreme User",
            "GET",
            "users/sirix_1",
            200
        )
        
        if success and isinstance(response, dict):
            # Verify required fields
            required_checks = {
                'username': 'sirix_1',
                'permission_level': 'sirix_1', 
                'is_immutable': True
            }
            
            for field, expected_value in required_checks.items():
                if field in response:
                    if response[field] == expected_value:
                        print(f"   ✅ {field}: {response[field]}")
                    else:
                        print(f"   ❌ {field}: Expected {expected_value}, got {response[field]}")
                else:
                    print(f"   ❌ Missing field: {field}")
                    
            # Check resources (should have high values)
            if 'resources' in response:
                resources = response['resources']
                if resources.get('gold', 0) >= 999999:
                    print(f"   ✅ Supreme resources: {resources.get('gold', 0)} gold")
                else:
                    print(f"   ⚠️  Expected supreme resources, got: {resources}")
        
        return success, response

    def test_get_all_npcs(self):
        """Test GET /api/npcs returns all NPCs including Oracle Veythra"""
        success, response = self.run_test(
            "Get All NPCs",
            "GET",
            "npcs",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} NPCs")
            
            # Check for minimum 8 NPCs
            if len(response) >= 8:
                print(f"   ✅ Has required 8+ NPCs")
            else:
                print(f"   ❌ Expected 8+ NPCs, got {len(response)}")
            
            # Look for Oracle Veythra
            oracle_found = False
            for npc in response:
                if npc.get('name') == 'Oracle Veythra':
                    oracle_found = True
                    if npc.get('is_oracle') == True:
                        print(f"   ✅ Oracle Veythra found with is_oracle=True")
                    else:
                        print(f"   ❌ Oracle Veythra found but is_oracle={npc.get('is_oracle')}")
                    break
            
            if not oracle_found:
                print(f"   ❌ Oracle Veythra NPC not found")
                
            # List all NPC names
            npc_names = [npc.get('name', 'Unknown') for npc in response]
            print(f"   NPCs: {', '.join(npc_names)}")
        
        return success, response

    def test_oracle_sanctum_location(self):
        """Test that oracle_sanctum location exists"""
        success, response = self.run_test(
            "Get Locations (check for oracle_sanctum)",
            "GET", 
            "locations",
            200
        )
        
        if success and isinstance(response, list):
            oracle_sanctum_found = False
            for location in response:
                if location.get('id') == 'oracle_sanctum':
                    oracle_sanctum_found = True
                    print(f"   ✅ oracle_sanctum location found")
                    print(f"   Name: {location.get('name')}")
                    if 'Oracle Veythra' in location.get('npcs', []):
                        print(f"   ✅ Oracle Veythra present in oracle_sanctum")
                    else:
                        print(f"   ⚠️  Oracle Veythra not in oracle_sanctum NPCs: {location.get('npcs', [])}")
                    break
            
            if not oracle_sanctum_found:
                print(f"   ❌ oracle_sanctum location not found")
                locations = [loc.get('id', 'Unknown') for loc in response]
                print(f"   Available locations: {', '.join(locations)}")
        
        return success, response

    def test_permission_system(self):
        """Test GET /api/permissions returns all 4 permission tiers"""
        success, response = self.run_test(
            "Get Permission System",
            "GET",
            "permissions",
            200
        )
        
        if success and isinstance(response, dict):
            expected_levels = ['basic', 'advanced', 'admin', 'sirix_1']
            found_levels = list(response.keys())
            
            print(f"   Found permission levels: {', '.join(found_levels)}")
            
            for level in expected_levels:
                if level in response:
                    print(f"   ✅ {level} permission tier exists")
                    # Check if it has required fields
                    perm_data = response[level]
                    if 'level' in perm_data and 'abilities' in perm_data:
                        print(f"      Level: {perm_data['level']}, Abilities: {len(perm_data['abilities'])}")
                    else:
                        print(f"      ⚠️  Missing required fields in {level}")
                else:
                    print(f"   ❌ {level} permission tier missing")
            
            # Check sirix_1 specific properties
            if 'sirix_1' in response:
                sirix_data = response['sirix_1']
                if sirix_data.get('level') == 999 and 'all' in sirix_data.get('abilities', []):
                    print(f"   ✅ sirix_1 has supreme level (999) and 'all' abilities")
                else:
                    print(f"   ⚠️  sirix_1 configuration: level={sirix_data.get('level')}, abilities={sirix_data.get('abilities')}")
        
        return success, response

    def test_create_user_profile(self):
        """Test POST /api/users - user profile creation"""
        profile_data = {
            "username": f"test_profile_{datetime.now().strftime('%H%M%S')}",
            "display_name": "Test Profile User",
            "permission_level": "basic"
        }
        
        success, response = self.run_test(
            "Create User Profile",
            "POST",
            "users",
            200,
            data=profile_data
        )
        
        if success and isinstance(response, dict):
            # Store user ID for further tests
            if 'id' in response:
                self.user_id = response['id']
                print(f"   Created profile ID: {self.user_id}")
                
                # Verify default resources
                if 'resources' in response:
                    resources = response['resources']
                    if resources.get('gold') == 100:
                        print(f"   ✅ Default resources: {resources}")
                    else:
                        print(f"   ⚠️  Unexpected default resources: {resources}")
        
        return success, response

    def test_quest_system(self):
        """Test quest creation and retrieval"""
        if not self.user_id:
            print("❌ Cannot test quests - No user ID available")
            return False, {}
            
        quest_data = {
            "title": "Test Quest - API Validation",
            "description": "A quest created by the testing system to validate quest functionality.",
            "creator_id": self.user_id,
            "creator_type": "player", 
            "location_id": "village_square",
            "rewards": {"gold": 25, "xp": 15},
            "use_personal_resources": True
        }
        
        # First try to create quest
        success, response = self.run_test(
            "Create Quest",
            "POST",
            "quests",
            200,
            data=quest_data
        )
        
        quest_id = None
        if success and 'id' in response:
            quest_id = response['id']
            print(f"   Created quest ID: {quest_id}")
        
        # Test quest retrieval
        get_success, get_response = self.run_test(
            "Get All Quests",
            "GET",
            "quests",
            200
        )
        
        if get_success and isinstance(get_response, list):
            print(f"   Found {len(get_response)} total quests")
            if quest_id:
                # Look for our quest
                our_quest = None
                for q in get_response:
                    if q.get('id') == quest_id:
                        our_quest = q
                        break
                
                if our_quest:
                    print(f"   ✅ Our test quest found in quest list")
                    print(f"   Status: {our_quest.get('status')}, Rewards: {our_quest.get('rewards')}")
                else:
                    print(f"   ⚠️  Our test quest not found in quest list")
        
        return success and get_success, response

    def test_user_permissions_endpoint(self):
        """Test GET /api/permissions/{user_id}"""
        if not self.user_id:
            print("❌ Cannot test user permissions - No user ID available")
            return False, {}
            
        success, response = self.run_test(
            "Get User Permissions",
            "GET",
            f"permissions/{self.user_id}",
            200
        )
        
        if success and isinstance(response, dict):
            required_fields = ['user_id', 'permission_level', 'abilities', 'is_immutable']
            for field in required_fields:
                if field in response:
                    print(f"   ✅ {field}: {response[field]}")
                else:
                    print(f"   ❌ Missing field: {field}")
            
            # Check if basic user has correct permissions
            if response.get('permission_level') == 'basic':
                expected_abilities = ['explore', 'talk', 'trade', 'view_quests']
                user_abilities = response.get('abilities', [])
                if all(ability in user_abilities for ability in expected_abilities):
                    print(f"   ✅ Basic user has correct abilities")
                else:
                    print(f"   ⚠️  Basic abilities mismatch. Expected: {expected_abilities}, Got: {user_abilities}")
        
        return success, response

def main():
    """Run all API tests"""
    print("🚀 Starting AI Village Backend API Tests - Multiplayer Expansion")
    print("=" * 60)
    
    tester = AIVillageAPITester()
    
    # Core API tests + New Multiplayer Features
    tests = [
        tester.test_root_endpoint,
        tester.test_get_locations,
        tester.test_oracle_sanctum_location,  # NEW: Test oracle_sanctum exists
        tester.test_sirix_1_user,  # NEW: Test Sirix-1 supreme user
        tester.test_get_all_npcs,  # NEW: Test 8 NPCs including Oracle Veythra
        tester.test_permission_system,  # NEW: Test 4-tier permission system
        tester.test_create_user_profile,  # NEW: Test user profile creation
        tester.test_create_character,
        tester.test_get_character,
        tester.test_update_character_location,
        tester.test_chat_functionality,  # This tests the AI integration
        tester.test_get_conversations,
        tester.test_dataspace_stats,
        tester.test_get_dataspace,
        tester.test_news_endpoint,  # Test news integration
        tester.test_chat_with_news_query,  # Test AI + news
        tester.test_quest_system,  # NEW: Test quest creation/retrieval
        tester.test_user_permissions_endpoint,  # NEW: Test user-specific permissions
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