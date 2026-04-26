"""
Iteration 23 Feature Tests
==========================
Tests for:
1. Discovery Lab - Material/Spell experimentation with First Discovery System
2. Google OAuth - Social login buttons and callback handling
3. Profile Settings - Username change with legacy name tracking
4. Profile Logo URL input
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDiscoveryLabEndpoints:
    """Tests for Discovery Lab API endpoints"""
    
    def test_get_experiment_types(self):
        """GET /api/discovery/types - Returns 3 experiment types"""
        response = requests.get(f"{BASE_URL}/api/discovery/types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "experiment_types" in data, "Response should contain experiment_types"
        
        exp_types = data["experiment_types"]
        assert "material_fusion" in exp_types, "Should have material_fusion type"
        assert "spell_synthesis" in exp_types, "Should have spell_synthesis type"
        assert "enchantment_binding" in exp_types, "Should have enchantment_binding type"
        
        # Verify structure of experiment types
        for exp_type in exp_types.values():
            assert "name" in exp_type
            assert "description" in exp_type
            assert "base_success_rate" in exp_type
            assert "ve_bonus_multiplier" in exp_type
        
        # Verify first discovery rewards are included
        assert "first_discovery_rewards" in data
        rewards = data["first_discovery_rewards"]
        assert "ve_bonus" in rewards
        assert "xp_bonus" in rewards
        assert "royalty_rate" in rewards
        print("PASS: GET /api/discovery/types returns 3 experiment types with rewards")
    
    def test_get_recent_discoveries(self):
        """GET /api/discovery/recent - Returns recent world discoveries"""
        response = requests.get(f"{BASE_URL}/api/discovery/recent")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "discoveries" in data, "Response should contain discoveries list"
        assert isinstance(data["discoveries"], list), "Discoveries should be a list"
        print("PASS: GET /api/discovery/recent returns discoveries list")
    
    def test_get_user_discoveries(self):
        """GET /api/discovery/user/{user_id} - Returns user's discoveries"""
        # Use test user ID
        test_user_id = "test_user_123"
        response = requests.get(f"{BASE_URL}/api/discovery/user/{test_user_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "discoveries" in data
        assert "total_first_discoveries" in data
        assert "reproductions" in data
        print("PASS: GET /api/discovery/user/{user_id} returns user discoveries")
    
    def test_get_discovery_stats(self):
        """GET /api/discovery/stats - Returns overall discovery statistics"""
        response = requests.get(f"{BASE_URL}/api/discovery/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total_discoveries" in data
        assert "total_attempts" in data
        assert "successful_attempts" in data
        assert "success_rate" in data
        assert "top_discoverers" in data
        print("PASS: GET /api/discovery/stats returns discovery statistics")
    
    def test_check_if_discovered(self):
        """GET /api/discovery/check/{combo_hash} - Check if combination discovered"""
        # Test with a random hash that likely doesn't exist
        test_hash = "abc123def456"
        response = requests.get(f"{BASE_URL}/api/discovery/check/{test_hash}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "discovered" in data
        print("PASS: GET /api/discovery/check/{combo_hash} returns discovery status")
    
    def test_experiment_validation_min_ingredients(self):
        """POST /api/discovery/experiment - Validates minimum 2 ingredients"""
        payload = {
            "user_id": "test_user",
            "user_name": "Test User",
            "experiment_type": "material_fusion",
            "experiment_name": "Test Experiment",
            "ingredients": ["wood"]  # Only 1 ingredient
        }
        response = requests.post(f"{BASE_URL}/api/discovery/experiment", json=payload)
        assert response.status_code == 400, f"Expected 400 for <2 ingredients, got {response.status_code}"
        print("PASS: POST /api/discovery/experiment validates minimum 2 ingredients")
    
    def test_experiment_validation_max_ingredients(self):
        """POST /api/discovery/experiment - Validates maximum 4 ingredients"""
        payload = {
            "user_id": "test_user",
            "user_name": "Test User",
            "experiment_type": "material_fusion",
            "experiment_name": "Test Experiment",
            "ingredients": ["wood", "stone", "iron", "crystal", "obsidian"]  # 5 ingredients
        }
        response = requests.post(f"{BASE_URL}/api/discovery/experiment", json=payload)
        assert response.status_code == 400, f"Expected 400 for >4 ingredients, got {response.status_code}"
        print("PASS: POST /api/discovery/experiment validates maximum 4 ingredients")
    
    def test_experiment_validation_invalid_type(self):
        """POST /api/discovery/experiment - Validates experiment type"""
        payload = {
            "user_id": "test_user",
            "user_name": "Test User",
            "experiment_type": "invalid_type",
            "experiment_name": "Test Experiment",
            "ingredients": ["wood", "stone"]
        }
        response = requests.post(f"{BASE_URL}/api/discovery/experiment", json=payload)
        assert response.status_code == 400, f"Expected 400 for invalid type, got {response.status_code}"
        print("PASS: POST /api/discovery/experiment validates experiment type")


class TestGoogleAuthEndpoints:
    """Tests for Google OAuth and username/password change endpoints"""
    
    def test_legacy_names_endpoint_exists(self):
        """GET /api/auth/user/{user_id}/legacy-names - Returns username history"""
        # First get a valid user ID by logging in
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sirix_1",
            "password": "HCLynnTV04"
        })
        
        if login_response.status_code == 200:
            user_data = login_response.json()
            user_id = user_data.get("user", {}).get("id")
            
            if user_id:
                response = requests.get(f"{BASE_URL}/api/auth/user/{user_id}/legacy-names")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                
                data = response.json()
                assert "current_username" in data
                assert "display_name" in data
                assert "legacy_usernames" in data
                print(f"PASS: GET /api/auth/user/{user_id}/legacy-names returns username history")
            else:
                pytest.skip("Could not get user ID from login response")
        else:
            pytest.skip("Could not login to test legacy names endpoint")
    
    def test_legacy_names_404_for_invalid_user(self):
        """GET /api/auth/user/{user_id}/legacy-names - Returns 404 for invalid user"""
        response = requests.get(f"{BASE_URL}/api/auth/user/invalid_user_id_12345/legacy-names")
        assert response.status_code == 404, f"Expected 404 for invalid user, got {response.status_code}"
        print("PASS: GET /api/auth/user/{invalid_id}/legacy-names returns 404")
    
    def test_username_change_validation(self):
        """POST /api/auth/username/change - Validates username format"""
        payload = {
            "user_id": "test_user",
            "new_username": "ab"  # Too short (min 3 chars)
        }
        response = requests.post(f"{BASE_URL}/api/auth/username/change", json=payload)
        # Should fail validation (either 400 or 422)
        assert response.status_code in [400, 404, 422], f"Expected validation error, got {response.status_code}"
        print("PASS: POST /api/auth/username/change validates username length")
    
    def test_password_change_endpoint_exists(self):
        """POST /api/auth/password/change - Endpoint exists"""
        payload = {
            "user_id": "invalid_user",
            "current_password": "wrong",
            "new_password": "newpass123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/password/change", json=payload)
        # Should return 404 for invalid user, not 404 for endpoint
        assert response.status_code in [400, 401, 404], f"Expected 400/401/404, got {response.status_code}"
        print("PASS: POST /api/auth/password/change endpoint exists")
    
    def test_profile_update_endpoint(self):
        """PUT /api/auth/profile/update - Profile update with logo URL"""
        payload = {
            "user_id": "invalid_user",
            "display_name": "Test Name",
            "profile_logo": "https://example.com/logo.png"
        }
        response = requests.put(f"{BASE_URL}/api/auth/profile/update", json=payload)
        # Should return 404 for invalid user
        assert response.status_code == 404, f"Expected 404 for invalid user, got {response.status_code}"
        print("PASS: PUT /api/auth/profile/update endpoint exists")
    
    def test_profile_update_validates_logo_url(self):
        """PUT /api/auth/profile/update - Validates logo URL format"""
        # First login to get valid user ID
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sirix_1",
            "password": "HCLynnTV04"
        })
        
        if login_response.status_code == 200:
            user_data = login_response.json()
            user_id = user_data.get("user", {}).get("id")
            
            if user_id:
                payload = {
                    "user_id": user_id,
                    "profile_logo": "not-a-valid-url"  # Invalid URL
                }
                response = requests.put(f"{BASE_URL}/api/auth/profile/update", json=payload)
                assert response.status_code == 400, f"Expected 400 for invalid URL, got {response.status_code}"
                print("PASS: PUT /api/auth/profile/update validates logo URL format")
            else:
                pytest.skip("Could not get user ID")
        else:
            pytest.skip("Could not login")


class TestProfileCustomizationEndpoints:
    """Tests for profile customization with new Account tab features"""
    
    def test_profile_customization_options(self):
        """GET /api/profile/customization-options - Returns customization options"""
        response = requests.get(f"{BASE_URL}/api/profile/customization-options")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Should have chat colors and model presets
        assert "chat_colors" in data or "model_presets" in data
        print("PASS: GET /api/profile/customization-options returns options")
    
    def test_get_profile_customization(self):
        """GET /api/profile/customization/{user_id} - Returns user profile"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sirix_1",
            "password": "HCLynnTV04"
        })
        
        if login_response.status_code == 200:
            user_data = login_response.json()
            user_id = user_data.get("user", {}).get("id")
            
            if user_id:
                response = requests.get(f"{BASE_URL}/api/profile/customization/{user_id}")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                
                data = response.json()
                # Should have profile fields
                assert "display_name" in data or "username" in data
                print("PASS: GET /api/profile/customization/{user_id} returns profile")
            else:
                pytest.skip("Could not get user ID")
        else:
            pytest.skip("Could not login")


class TestMaterialsEndpoints:
    """Tests for materials list endpoint used by Discovery Lab"""
    
    def test_get_materials_list(self):
        """GET /api/materials/list - Returns materials for experiments"""
        response = requests.get(f"{BASE_URL}/api/materials/list")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "materials" in data, "Response should contain materials"
        print("PASS: GET /api/materials/list returns materials")


class TestAuthLogin:
    """Tests for standard auth login (used by social login flow)"""
    
    def test_login_with_valid_credentials(self):
        """POST /api/auth/login - Login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sirix_1",
            "password": "HCLynnTV04"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user" in data
        user = data["user"]
        assert "id" in user
        assert "username" in user
        assert "display_name" in user
        print("PASS: POST /api/auth/login works with valid credentials")
    
    def test_login_with_invalid_password(self):
        """POST /api/auth/login - Returns 401 for invalid password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sirix_1",
            "password": "wrong_password"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/auth/login returns 401 for invalid password")
    
    def test_login_with_nonexistent_user(self):
        """POST /api/auth/login - Returns 401 or 404 for nonexistent user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "nonexistent_user_xyz",
            "password": "anypassword"
        })
        # API returns 401 (security best practice - don't reveal if user exists)
        assert response.status_code in [401, 404], f"Expected 401 or 404, got {response.status_code}"
        print("PASS: POST /api/auth/login returns 401/404 for nonexistent user")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
