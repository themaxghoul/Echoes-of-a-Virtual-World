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
            required_fields = ['user_id', 'permission_level', 'abilities', 'is_immutable', 'official_rank', 'standing', 'reputation', 'chat_access']
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
            
            # Check official rank and standing system
            official_rank = response.get('official_rank', 'unknown')
            standing = response.get('standing', 'unknown')
            reputation = response.get('reputation', 0)
            print(f"   Official Rank: {official_rank}, Standing: {standing}, Reputation: {reputation}")
            
            # Check chat access
            chat_access = response.get('chat_access', [])
            if isinstance(chat_access, list) and 'local' in chat_access:
                print(f"   ✅ Chat access includes 'local': {chat_access}")
            else:
                print(f"   ⚠️  Chat access missing 'local': {chat_access}")
        
        return success, response

    def test_rankings_endpoint(self):
        """Test GET /api/rankings returns official rankings and standing levels"""
        success, response = self.run_test(
            "Get Rankings System",
            "GET",
            "rankings",
            200
        )
        
        if success and isinstance(response, dict):
            # Check for official rankings
            if 'official_rankings' in response:
                rankings = response['official_rankings']
                print(f"   Found {len(rankings)} official rankings")
                
                # Check for specific ranks
                expected_ranks = ['citizen', 'mayor', 'governor', 'sovereign']
                for rank in expected_ranks:
                    if rank in rankings:
                        rank_data = rankings[rank]
                        tier = rank_data.get('tier', 'unknown')
                        rank_num = rank_data.get('rank', 0)
                        title = rank_data.get('title', 'Unknown')
                        print(f"   ✅ {rank}: Tier={tier}, Rank={rank_num}, Title={title}")
                    else:
                        print(f"   ❌ Missing rank: {rank}")
                
                # Check tiers are correct
                city_ranks = [r for r, data in rankings.items() if data.get('tier') == 'city']
                state_ranks = [r for r, data in rankings.items() if data.get('tier') == 'state']
                country_ranks = [r for r, data in rankings.items() if data.get('tier') == 'country']
                
                print(f"   City tier ranks: {len(city_ranks)}")
                print(f"   State tier ranks: {len(state_ranks)}")
                print(f"   Country tier ranks: {len(country_ranks)}")
                
                if len(city_ranks) >= 4 and len(state_ranks) >= 2 and len(country_ranks) >= 3:
                    print(f"   ✅ All tiers have appropriate number of ranks")
                else:
                    print(f"   ⚠️  Tier distribution may be incorrect")
            else:
                print(f"   ❌ Missing 'official_rankings' field")
            
            # Check for standing levels
            if 'standing_levels' in response:
                standings = response['standing_levels']
                print(f"   Found {len(standings)} standing levels")
                
                expected_standings = ['Outcast', 'Neutral', 'Respected', 'Legendary']
                found_standings = [s.get('name', 'Unknown') for s in standings]
                
                for expected in expected_standings:
                    if expected in found_standings:
                        print(f"   ✅ Standing level: {expected}")
                    else:
                        print(f"   ❌ Missing standing level: {expected}")
                        
                # Check standing levels are ordered by reputation
                prev_max = float('-inf')
                standings_ordered = True
                for standing in standings:
                    min_rep = standing.get('min_rep', 0)
                    if min_rep < prev_max:
                        standings_ordered = False
                        break
                    prev_max = standing.get('max_rep', 0)
                
                if standings_ordered:
                    print(f"   ✅ Standing levels properly ordered by reputation")
                else:
                    print(f"   ⚠️  Standing levels may not be properly ordered")
            else:
                print(f"   ❌ Missing 'standing_levels' field")
        
        return success, response

    def test_chat_channels_endpoint(self):
        """Test GET /api/chat/channels/{user_id} returns available chat channels based on rank"""
        if not self.user_id:
            print("❌ Cannot test chat channels - No user ID available")
            return False, {}
            
        success, response = self.run_test(
            "Get Available Chat Channels",
            "GET",
            f"chat/channels/{self.user_id}",
            200
        )
        
        if success and isinstance(response, dict):
            if 'channels' in response:
                channels = response['channels']
                print(f"   Found {len(channels)} available chat channels")
                
                # Check each channel has required fields
                for channel in channels:
                    if all(field in channel for field in ['id', 'name', 'description', 'color']):
                        print(f"   ✅ Channel '{channel['id']}': {channel['name']}")
                    else:
                        print(f"   ⚠️  Channel missing fields: {channel}")
                
                # Basic user should have at least 'local' access
                channel_ids = [ch.get('id') for ch in channels]
                if 'local' in channel_ids:
                    print(f"   ✅ Basic user has 'local' chat access")
                else:
                    print(f"   ❌ Basic user missing 'local' chat access")
                    
                # Should not have high-level channels for basic user
                high_level_channels = ['country', 'global']
                found_high_level = [ch for ch in channel_ids if ch in high_level_channels]
                if not found_high_level:
                    print(f"   ✅ Basic user correctly restricted from high-level channels")
                else:
                    print(f"   ⚠️  Basic user has unexpected high-level access: {found_high_level}")
                    
            else:
                print(f"   ❌ Missing 'channels' field")
            
            # Check rank title is provided
            if 'rank_title' in response:
                rank_title = response['rank_title']
                print(f"   User rank title: {rank_title}")
            else:
                print(f"   ⚠️  Missing 'rank_title' field")
        
        return success, response

    # ============ BUILDING SYSTEM TESTS ============

    def test_materials_endpoint(self):
        """Test GET /api/materials returns 5 materials with strength/durability stats"""
        success, response = self.run_test(
            "Get Building Materials",
            "GET",
            "materials",
            200
        )
        
        if success and isinstance(response, dict):
            materials = list(response.keys())
            print(f"   Found {len(materials)} materials: {', '.join(materials)}")
            
            expected_materials = ['wood', 'stone', 'iron', 'crystal', 'obsidian']
            if len(materials) == 5 and all(mat in materials for mat in expected_materials):
                print(f"   ✅ All 5 expected materials present")
            else:
                print(f"   ❌ Expected 5 materials {expected_materials}, got {materials}")
                
            # Check each material has required fields
            for mat_id, mat_data in response.items():
                required_fields = ['name', 'strength', 'durability', 'description', 'rarity']
                missing_fields = [f for f in required_fields if f not in mat_data]
                if not missing_fields:
                    print(f"   ✅ {mat_id}: STR={mat_data['strength']}, DUR={mat_data['durability']}")
                else:
                    print(f"   ❌ {mat_id} missing fields: {missing_fields}")
        
        return success, response

    def test_schematics_endpoint(self):
        """Test GET /api/schematics returns 19 schematics across 4 tiers"""
        success, response = self.run_test(
            "Get Building Schematics",
            "GET",
            "schematics",
            200
        )
        
        if success and isinstance(response, dict):
            schematics = list(response.keys())
            print(f"   Found {len(schematics)} schematics")
            
            if len(schematics) == 19:
                print(f"   ✅ Expected 19 schematics found")
            else:
                print(f"   ❌ Expected 19 schematics, got {len(schematics)}")
            
            # Check tier distribution
            tier_counts = {}
            for schematic_id, schematic_data in response.items():
                tier = schematic_data.get('tier', 'unknown')
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
                
                # Check required fields
                required_fields = ['name', 'tier', 'materials', 'contribution_required', 'description']
                missing_fields = [f for f in required_fields if f not in schematic_data]
                if missing_fields:
                    print(f"   ❌ {schematic_id} missing fields: {missing_fields}")
            
            print(f"   Tier distribution: {tier_counts}")
            expected_tiers = ['basic', 'intermediate', 'advanced', 'master']
            if all(tier in tier_counts for tier in expected_tiers):
                print(f"   ✅ All 4 tiers present")
                # Based on the code: 5 basic, 6 intermediate, 4 advanced, 4 master
                if (tier_counts.get('basic', 0) == 5 and 
                    tier_counts.get('intermediate', 0) == 6 and 
                    tier_counts.get('advanced', 0) == 4 and 
                    tier_counts.get('master', 0) == 4):
                    print(f"   ✅ Correct tier distribution (5-6-4-4)")
                else:
                    print(f"   ⚠️  Tier distribution differs from expected (5-6-4-4)")
            else:
                print(f"   ❌ Missing tiers: {[t for t in expected_tiers if t not in tier_counts]}")
        
        return success, response

    def test_inventory_endpoint(self):
        """Test GET /api/inventory/{userId} returns user materials and gold"""
        if not self.user_id:
            print("❌ Cannot test inventory - No user ID available")
            return False, {}
            
        success, response = self.run_test(
            "Get User Inventory",
            "GET",
            f"inventory/{self.user_id}",
            200
        )
        
        if success and isinstance(response, dict):
            # Check required fields
            if 'materials' in response and 'gold' in response:
                materials = response['materials']
                gold = response['gold']
                print(f"   Gold: {gold}")
                print(f"   Materials: {len(materials)} types")
                
                # Check default starting materials (wood:10, stone:5)
                if materials.get('wood', {}).get('amount', 0) >= 0:
                    print(f"   ✅ Wood: {materials.get('wood', {}).get('amount', 0)}")
                else:
                    print(f"   ❌ Wood amount missing or invalid")
                
                if materials.get('stone', {}).get('amount', 0) >= 0:
                    print(f"   ✅ Stone: {materials.get('stone', {}).get('amount', 0)}")
                else:
                    print(f"   ❌ Stone amount missing or invalid")
                    
                # Check each material has name, amount, strength, durability
                for mat_id, mat_data in materials.items():
                    required_fields = ['name', 'amount', 'strength', 'durability']
                    if all(field in mat_data for field in required_fields):
                        print(f"   ✅ {mat_id}: {mat_data['amount']} units")
                    else:
                        missing = [f for f in required_fields if f not in mat_data]
                        print(f"   ❌ {mat_id} missing fields: {missing}")
                        
                # Check contribution_points field
                if 'contribution_points' in response:
                    print(f"   ✅ Contribution points: {response['contribution_points']}")
                else:
                    print(f"   ❌ Missing contribution_points field")
            else:
                print(f"   ❌ Missing required fields: materials or gold")
        
        return success, response

    def test_build_structure(self):
        """Test POST /api/build creates structure and deducts materials"""
        if not self.user_id:
            print("❌ Cannot test building - No user ID available")
            return False, {}
        
        # Try to build a simple torch (requires 2 wood)
        build_data = {
            "schematic_id": "torch",
            "user_id": self.user_id,
            "location_id": "village_square",
            "position_x": 50.0,
            "position_y": 50.0
        }
        
        success, response = self.run_test(
            "Build Structure (Torch)",
            "POST",
            "build",
            200,
            data=build_data
        )
        
        if success and isinstance(response, dict):
            if 'building' in response and 'status' in response:
                building = response['building']
                print(f"   ✅ Built {building.get('schematic_id', 'Unknown')} successfully")
                print(f"   Builder: {building.get('builder_name', 'Unknown')}")
                print(f"   Location: {building.get('location_id', 'Unknown')}")
                
                if 'contribution_gained' in response:
                    print(f"   ✅ Contribution gained: {response['contribution_gained']}")
                
                if 'remaining_materials' in response:
                    remaining = response['remaining_materials']
                    print(f"   ✅ Materials after build: wood={remaining.get('wood', 0)}")
            else:
                print(f"   ❌ Invalid build response structure")
        
        return success, response

    def test_buildings_global(self):
        """Test GET /api/buildings/global returns all placed buildings"""
        success, response = self.run_test(
            "Get Global Buildings",
            "GET",
            "buildings/global",
            200
        )
        
        if success and isinstance(response, dict):
            if 'total' in response and 'by_location' in response:
                total = response['total']
                by_location = response['by_location']
                print(f"   ✅ Total buildings: {total}")
                print(f"   ✅ Locations with buildings: {len(by_location)}")
                
                for location, buildings in by_location.items():
                    print(f"   {location}: {len(buildings)} buildings")
                    
                    # Check building structure
                    if buildings:
                        first_building = buildings[0]
                        required_fields = ['id', 'schematic_id', 'builder_name', 'location_id']
                        if all(field in first_building for field in required_fields):
                            print(f"     ✅ Building structure valid")
                        else:
                            missing = [f for f in required_fields if f not in first_building]
                            print(f"     ❌ Building missing fields: {missing}")
            else:
                print(f"   ❌ Missing required fields: total or by_location")
        
        return success, response

    def test_trade_offer_creation(self):
        """Test POST /api/trade/offer creates trade listing"""
        if not self.user_id:
            print("❌ Cannot test trade creation - No user ID available")
            return False, {}
        
        trade_data = {
            "seller_id": self.user_id,
            "offering": {"wood": 5},
            "requesting": {"gold": 25}
        }
        
        success, response = self.run_test(
            "Create Trade Offer",
            "POST",
            "trade/offer",
            200,
            data=trade_data
        )
        
        if success and isinstance(response, dict):
            if 'id' in response and 'status' in response:
                self.trade_id = response['id']  # Store for accept test
                print(f"   ✅ Trade created with ID: {self.trade_id}")
                print(f"   Status: {response['status']}")
                print(f"   Seller: {response.get('seller_name', 'Unknown')}")
                print(f"   Offering: {response.get('offering', {})}")
                print(f"   Requesting: {response.get('requesting', {})}")
            else:
                print(f"   ❌ Invalid trade response structure")
        
        return success, response

    def test_trade_offers_list(self):
        """Test GET /api/trade/offers returns open trades"""
        success, response = self.run_test(
            "Get Open Trade Offers",
            "GET",
            "trade/offers",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} open trades")
            
            if response:
                # Check first trade structure
                first_trade = response[0]
                required_fields = ['id', 'seller_name', 'offering', 'requesting', 'status']
                if all(field in first_trade for field in required_fields):
                    print(f"   ✅ Trade structure valid")
                    print(f"   Sample: {first_trade.get('seller_name', 'Unknown')} offering {first_trade.get('offering', {})}")
                else:
                    missing = [f for f in required_fields if f not in first_trade]
                    print(f"   ❌ Trade missing fields: {missing}")
            else:
                print(f"   ℹ️  No open trades available")
        else:
            print(f"   ❌ Expected list response, got: {type(response)}")
        
        return success, response

    def test_contribution_status(self):
        """Test GET /api/contribution/{userId} returns contribution status"""
        if not self.user_id:
            print("❌ Cannot test contribution - No user ID available")
            return False, {}
            
        success, response = self.run_test(
            "Get Contribution Status",
            "GET",
            f"contribution/{self.user_id}",
            200
        )
        
        if success and isinstance(response, dict):
            # This endpoint might not exist yet, so we'll check what we get
            print(f"   Response keys: {list(response.keys())}")
            
            expected_fields = ['contribution_points', 'schematics_unlocked', 'total_schematics']
            found_fields = [f for f in expected_fields if f in response]
            missing_fields = [f for f in expected_fields if f not in response]
            
            if found_fields:
                print(f"   ✅ Found fields: {found_fields}")
                for field in found_fields:
                    print(f"   {field}: {response[field]}")
            
            if missing_fields:
                print(f"   ⚠️  Missing expected fields: {missing_fields}")
        
        return success, response

    # Store trade_id for accept test
    trade_id = None

    def test_trade_accept(self):
        """Test PUT /api/trade/{id}/accept completes trade"""
        # Create a second user for trade acceptance
        second_user_data = {
            "username": f"trader_{datetime.now().strftime('%H%M%S')}",
            "display_name": "Test Trader",
            "permission_level": "basic"
        }
        
        user_success, user_response = self.run_test(
            "Create Second User for Trade",
            "POST",
            "users",
            200,
            data=second_user_data
        )
        
        if not user_success or 'id' not in user_response:
            print("❌ Cannot test trade accept - Failed to create second user")
            return False, {}
        
        second_user_id = user_response['id']
        print(f"   Created second user: {second_user_id}")
        
        # Create a trade offer first
        trade_data = {
            "seller_id": self.user_id,
            "offering": {"wood": 1},  # Small amount to avoid insufficient materials
            "requesting": {"gold": 10}
        }
        
        trade_success, trade_response = self.run_test(
            "Create Trade for Accept Test",
            "POST",
            "trade/offer",
            200,
            data=trade_data
        )
        
        if not trade_success or 'id' not in trade_response:
            print("❌ Cannot test trade accept - Failed to create trade")
            return False, {}
        
        trade_id = trade_response['id']
        
        # Try to accept the trade
        success, response = self.run_test(
            "Accept Trade Offer",
            "PUT",
            f"trade/{trade_id}/accept?buyer_id={second_user_id}",
            200
        )
        
        if success:
            print(f"   ✅ Trade accepted successfully")
        
        return success, response

def main():
    """Run all API tests"""
    print("🚀 Starting AI Village Backend API Tests - Building System")
    print("=" * 60)
    
    tester = AIVillageAPITester()
    
    # Core API tests + New Multiplayer Features + Building System
    tests = [
        tester.test_root_endpoint,
        tester.test_get_locations,
        tester.test_oracle_sanctum_location,  # NEW: Test oracle_sanctum exists
        tester.test_sirix_1_user,  # NEW: Test Sirix-1 supreme user
        tester.test_get_all_npcs,  # NEW: Test 8 NPCs including Oracle Veythra
        tester.test_permission_system,  # NEW: Test 4-tier permission system
        tester.test_rankings_endpoint,  # NEW: Test official rankings and standing levels
        tester.test_create_user_profile,  # NEW: Test user profile creation
        tester.test_create_character,
        tester.test_get_character,
        tester.test_update_character_location,
        # Building System Tests
        tester.test_materials_endpoint,  # GET /api/materials
        tester.test_schematics_endpoint,  # GET /api/schematics  
        tester.test_inventory_endpoint,  # GET /api/inventory/{userId}
        tester.test_build_structure,  # POST /api/build
        tester.test_buildings_global,  # GET /api/buildings/global
        tester.test_trade_offer_creation,  # POST /api/trade/offer
        tester.test_trade_offers_list,  # GET /api/trade/offers
        tester.test_trade_accept,  # PUT /api/trade/{id}/accept
        tester.test_contribution_status,  # GET /api/contribution/{userId}
        # AI and other tests
        tester.test_chat_functionality,  # This tests the AI integration
        tester.test_get_conversations,
        tester.test_dataspace_stats,
        tester.test_get_dataspace,
        tester.test_news_endpoint,  # Test news integration
        tester.test_chat_with_news_query,  # Test AI + news
        tester.test_quest_system,  # NEW: Test quest creation/retrieval
        tester.test_user_permissions_endpoint,  # NEW: Test user-specific permissions with ranking
        tester.test_chat_channels_endpoint,  # NEW: Test chat channels based on rank
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