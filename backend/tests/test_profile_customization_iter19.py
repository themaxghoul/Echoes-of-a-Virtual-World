"""
Profile Customization Feature Tests - Iteration 19
Tests for:
- GET /api/profile/customization-options - Returns all available options
- GET /api/profile/customization/{user_id} - Returns current user profile settings
- PUT /api/profile/customization/{user_id} - Updates profile settings
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProfileCustomizationOptions:
    """Test GET /api/profile/customization-options endpoint"""
    
    def test_get_customization_options_returns_chat_colors(self):
        """Verify chat_colors are returned with expected colors"""
        response = requests.get(f"{BASE_URL}/api/profile/customization-options")
        assert response.status_code == 200
        data = response.json()
        
        assert "chat_colors" in data
        chat_colors = data["chat_colors"]
        assert "default" in chat_colors
        assert "gold" in chat_colors
        assert "crimson" in chat_colors
        assert "emerald" in chat_colors
        assert chat_colors["default"] == "#FFFFFF"
        assert chat_colors["gold"] == "#FFD700"
        print(f"✓ Chat colors returned: {len(chat_colors)} colors")
    
    def test_get_customization_options_returns_model_presets(self):
        """Verify model_presets are returned with expected presets"""
        response = requests.get(f"{BASE_URL}/api/profile/customization-options")
        assert response.status_code == 200
        data = response.json()
        
        assert "model_presets" in data
        presets = data["model_presets"]
        assert "human_male" in presets
        assert "human_female" in presets
        assert "elf_male" in presets
        assert "dwarf_male" in presets
        assert "orc" in presets
        assert "demon" in presets
        assert "angel" in presets
        assert "robot" in presets
        assert "ghost" in presets
        assert "beast" in presets
        
        # Verify preset structure
        assert presets["human_male"]["base"] == "humanoid"
        assert presets["elf_male"]["ears"] == "pointed"
        print(f"✓ Model presets returned: {len(presets)} presets")
    
    def test_get_customization_options_returns_color_fields(self):
        """Verify color_fields are returned"""
        response = requests.get(f"{BASE_URL}/api/profile/customization-options")
        assert response.status_code == 200
        data = response.json()
        
        assert "color_fields" in data
        color_fields = data["color_fields"]
        assert "skin_color" in color_fields
        assert "hair_color" in color_fields
        assert "eye_color" in color_fields
        assert "accent_color" in color_fields
        print(f"✓ Color fields returned: {color_fields}")
    
    def test_get_customization_options_returns_limits(self):
        """Verify max lengths are returned"""
        response = requests.get(f"{BASE_URL}/api/profile/customization-options")
        assert response.status_code == 200
        data = response.json()
        
        assert "max_bio_length" in data
        assert "max_status_length" in data
        assert data["max_bio_length"] == 500
        assert data["max_status_length"] == 100
        print("✓ Max lengths returned correctly")


class TestProfileCustomizationGet:
    """Test GET /api/profile/customization/{user_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def test_user(self):
        """Create a test user for profile customization tests"""
        unique_id = str(uuid.uuid4())[:8]
        username = f"TEST_profile_{unique_id}"
        
        # Register user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": "TestPass123!",
            "display_name": f"Test Profile User {unique_id}"
        })
        
        if response.status_code == 200:
            user_data = response.json()
            return {"id": user_data["user"]["id"], "username": username}
        elif response.status_code == 400:
            # User might exist, try login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "username": username,
                "password": "TestPass123!"
            })
            if login_response.status_code == 200:
                return {"id": login_response.json()["user"]["id"], "username": username}
        
        pytest.skip("Could not create test user")
    
    def test_get_profile_customization_returns_defaults(self, test_user):
        """Verify default profile settings are returned for new user"""
        response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        assert data["user_id"] == test_user["id"]
        assert "display_name" in data
        assert "bio" in data
        assert "chat_color" in data
        assert data["chat_color"] == "default"
        assert "model_preset" in data
        assert data["model_preset"] == "human_male"
        assert "model_colors" in data
        assert "show_online" in data
        assert data["show_online"] == True
        assert "allow_whispers" in data
        assert data["allow_whispers"] == True
        print(f"✓ Profile defaults returned for user {test_user['id']}")
    
    def test_get_profile_customization_returns_model_colors(self, test_user):
        """Verify model_colors structure is correct"""
        response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert response.status_code == 200
        data = response.json()
        
        model_colors = data["model_colors"]
        assert "skin_color" in model_colors
        assert "hair_color" in model_colors
        assert "eye_color" in model_colors
        assert "accent_color" in model_colors
        print(f"✓ Model colors structure correct: {model_colors}")
    
    def test_get_profile_customization_404_for_invalid_user(self):
        """Verify 404 is returned for non-existent user"""
        response = requests.get(f"{BASE_URL}/api/profile/customization/invalid-user-id-12345")
        assert response.status_code == 404
        print("✓ 404 returned for invalid user")


class TestProfileCustomizationUpdate:
    """Test PUT /api/profile/customization/{user_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def test_user(self):
        """Create a test user for profile update tests"""
        unique_id = str(uuid.uuid4())[:8]
        username = f"TEST_update_{unique_id}"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": "TestPass123!",
            "display_name": f"Update Test User {unique_id}"
        })
        
        if response.status_code == 200:
            user_data = response.json()
            return {"id": user_data["user"]["id"], "username": username}
        elif response.status_code == 400:
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "username": username,
                "password": "TestPass123!"
            })
            if login_response.status_code == 200:
                return {"id": login_response.json()["user"]["id"], "username": username}
        
        pytest.skip("Could not create test user")
    
    def test_update_display_name(self, test_user):
        """Test updating display name"""
        new_name = f"Updated Name {uuid.uuid4().hex[:4]}"
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"display_name": new_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == True
        assert "display_name" in data["fields_updated"]
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["display_name"] == new_name
        print(f"✓ Display name updated to: {new_name}")
    
    def test_update_display_name_validation_too_short(self, test_user):
        """Test display name validation - too short"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"display_name": "A"}
        )
        assert response.status_code == 400
        print("✓ Display name too short rejected")
    
    def test_update_display_name_validation_too_long(self, test_user):
        """Test display name validation - too long"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"display_name": "A" * 31}
        )
        assert response.status_code == 400
        print("✓ Display name too long rejected")
    
    def test_update_bio(self, test_user):
        """Test updating bio"""
        new_bio = "This is my test bio for profile customization testing."
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"bio": new_bio}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["bio"] == new_bio
        print(f"✓ Bio updated")
    
    def test_update_chat_color(self, test_user):
        """Test updating chat color"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"chat_color": "gold"}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["chat_color"] == "gold"
        print("✓ Chat color updated to gold")
    
    def test_update_model_preset(self, test_user):
        """Test updating model preset"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"model_preset": "elf_male"}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["model_preset"] == "elf_male"
        print("✓ Model preset updated to elf_male")
    
    def test_update_model_preset_invalid(self, test_user):
        """Test invalid model preset is rejected"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"model_preset": "invalid_preset"}
        )
        assert response.status_code == 400
        print("✓ Invalid model preset rejected")
    
    def test_update_model_colors(self, test_user):
        """Test updating model colors"""
        new_colors = {
            "skin_color": "#FFCC99",
            "hair_color": "#000000",
            "eye_color": "#0000FF",
            "accent_color": "#FF0000"
        }
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"model_colors": new_colors}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["model_colors"] == new_colors
        print(f"✓ Model colors updated: {new_colors}")
    
    def test_update_status_message(self, test_user):
        """Test updating status message"""
        status = "Testing profile customization!"
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"status_message": status}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["status_message"] == status
        print(f"✓ Status message updated")
    
    def test_update_privacy_settings(self, test_user):
        """Test updating privacy settings"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"show_online": False, "allow_whispers": False}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        data = get_response.json()
        assert data["show_online"] == False
        assert data["allow_whispers"] == False
        print("✓ Privacy settings updated")
    
    def test_update_profile_picture(self, test_user):
        """Test updating profile picture URL"""
        pic_url = "https://example.com/avatar.png"
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"profile_picture": pic_url}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["profile_picture"] == pic_url
        print("✓ Profile picture URL updated")
    
    def test_update_title_display(self, test_user):
        """Test updating title display"""
        title = "Dragon Slayer"
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={"title_display": title}
        )
        assert response.status_code == 200
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/profile/customization/{test_user['id']}")
        assert get_response.json()["title_display"] == title
        print(f"✓ Title display updated to: {title}")
    
    def test_update_multiple_fields(self, test_user):
        """Test updating multiple fields at once"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/{test_user['id']}",
            json={
                "display_name": "Multi Update Test",
                "bio": "Testing multiple field updates",
                "chat_color": "emerald",
                "model_preset": "dwarf_male"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["fields_updated"]) >= 4
        print(f"✓ Multiple fields updated: {data['fields_updated']}")
    
    def test_update_404_for_invalid_user(self):
        """Test 404 for non-existent user"""
        response = requests.put(
            f"{BASE_URL}/api/profile/customization/invalid-user-id-12345",
            json={"display_name": "Test"}
        )
        assert response.status_code == 404
        print("✓ 404 returned for invalid user on update")


class TestProfileCustomizationIntegration:
    """Integration tests for profile customization with existing user"""
    
    def test_login_and_get_profile(self):
        """Test login with sirix_1 and get profile customization"""
        # Login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sirix_1",
            "password": os.environ.get("SIRIX_ADMIN_PASSWORD", "test_password")
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login with sirix_1")
        
        user_id = login_response.json()["user"]["id"]
        
        # Get profile customization
        profile_response = requests.get(f"{BASE_URL}/api/profile/customization/{user_id}")
        assert profile_response.status_code == 200
        data = profile_response.json()
        
        assert data["user_id"] == user_id
        assert "display_name" in data
        assert "chat_color" in data
        assert "model_preset" in data
        print(f"✓ Profile customization retrieved for sirix_1: {data['display_name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
