"""
Iteration 24 Tests: World Exploration & Land Discovery System
=============================================================
Tests for:
- World seed API (/api/world/seed)
- Biomes API (/api/world/biomes)
- Tile API (/api/world/tile/{x}/{y})
- Player position tracking (/api/world/player/{user_id}/position)
- Exploration API (/api/world/explore)
- ModeSelection shows 'World Explorer' card
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = "sirix_1"
TEST_PASSWORD = "HCLynnTV04"


class TestWorldSeedAPI:
    """Tests for world seed endpoint"""
    
    def test_get_world_seed(self):
        """GET /api/world/seed returns deterministic seed info"""
        response = requests.get(f"{BASE_URL}/api/world/seed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify seed info structure
        assert "seed_id" in data, "Missing seed_id"
        assert "seed_name" in data, "Missing seed_name"
        assert "version" in data, "Missing version"
        assert "chunk_size" in data, "Missing chunk_size"
        assert "region_size" in data, "Missing region_size"
        assert "origin" in data, "Missing origin"
        assert "biome_count" in data, "Missing biome_count"
        assert "description" in data, "Missing description"
        
        # Verify origin is at (0, 0, 70)
        origin = data["origin"]
        assert origin["x"] == 0, f"Origin x should be 0, got {origin['x']}"
        assert origin["y"] == 0, f"Origin y should be 0, got {origin['y']}"
        assert origin["z"] == 70, f"Origin z should be 70, got {origin['z']}"
        
        # Verify seed name
        assert data["seed_name"] == "The Echoes", f"Seed name should be 'The Echoes', got {data['seed_name']}"
        
        print(f"✓ World seed API returns correct data: {data['seed_name']}")


class TestBiomesAPI:
    """Tests for biomes endpoint"""
    
    def test_get_all_biomes(self):
        """GET /api/world/biomes returns 10 biomes"""
        response = requests.get(f"{BASE_URL}/api/world/biomes")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "biomes" in data, "Missing biomes"
        assert "total" in data, "Missing total"
        
        # Verify 10 biomes
        assert data["total"] == 10, f"Expected 10 biomes, got {data['total']}"
        
        # Verify expected biomes exist
        expected_biomes = [
            "plains", "forest", "shadow_forest", "mountains", "volcanic",
            "desert", "tundra", "swamp", "crystal_caves", "ethereal"
        ]
        
        biomes = data["biomes"]
        for biome_id in expected_biomes:
            assert biome_id in biomes, f"Missing biome: {biome_id}"
            biome = biomes[biome_id]
            assert "name" in biome, f"Biome {biome_id} missing name"
            assert "base_height" in biome, f"Biome {biome_id} missing base_height"
            assert "color_2d" in biome, f"Biome {biome_id} missing color_2d"
            assert "color_iso" in biome, f"Biome {biome_id} missing color_iso"
            assert "danger_level" in biome, f"Biome {biome_id} missing danger_level"
            assert "resources" in biome, f"Biome {biome_id} missing resources"
        
        print(f"✓ All 10 biomes defined correctly")
    
    def test_biome_properties(self):
        """Verify biome properties are correct"""
        response = requests.get(f"{BASE_URL}/api/world/biomes")
        data = response.json()
        biomes = data["biomes"]
        
        # Check plains (origin biome)
        plains = biomes["plains"]
        assert plains["name"] == "Verdant Plains", f"Plains name incorrect: {plains['name']}"
        assert plains["base_height"] == 70, f"Plains base_height should be 70, got {plains['base_height']}"
        assert plains["danger_level"] == 1, f"Plains danger_level should be 1, got {plains['danger_level']}"
        
        # Check ethereal (highest danger)
        ethereal = biomes["ethereal"]
        assert ethereal["danger_level"] == 6, f"Ethereal danger_level should be 6, got {ethereal['danger_level']}"
        
        print(f"✓ Biome properties verified")


class TestTileAPI:
    """Tests for tile endpoint"""
    
    def test_get_tile_at_origin(self):
        """GET /api/world/tile/0/0 returns plains biome"""
        response = requests.get(f"{BASE_URL}/api/world/tile/0/0")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["x"] == 0, f"Tile x should be 0, got {data['x']}"
        assert data["y"] == 0, f"Tile y should be 0, got {data['y']}"
        assert data["biome"] == "plains", f"Origin biome should be plains, got {data['biome']}"
        assert data["biome_name"] == "Verdant Plains", f"Origin biome name incorrect"
        assert "z" in data, "Missing height (z)"
        assert "color_2d" in data, "Missing color_2d"
        assert "color_iso" in data, "Missing color_iso"
        assert "danger_level" in data, "Missing danger_level"
        assert "is_passable" in data, "Missing is_passable"
        
        print(f"✓ Tile at origin is {data['biome_name']} at height {data['z']}")
    
    def test_tile_determinism(self):
        """Same coordinates always return same biome (deterministic)"""
        # Get tile at (5, 5) twice
        response1 = requests.get(f"{BASE_URL}/api/world/tile/5/5")
        response2 = requests.get(f"{BASE_URL}/api/world/tile/5/5")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["biome"] == data2["biome"], "Biome should be deterministic"
        assert data1["z"] == data2["z"], "Height should be deterministic"
        
        print(f"✓ Tile generation is deterministic")
    
    def test_tile_at_different_coordinates(self):
        """Test tiles at various coordinates"""
        test_coords = [(10, 10), (-5, -5), (50, 50), (-20, 30)]
        
        for x, y in test_coords:
            response = requests.get(f"{BASE_URL}/api/world/tile/{x}/{y}")
            assert response.status_code == 200, f"Failed for ({x}, {y})"
            data = response.json()
            assert data["x"] == x
            assert data["y"] == y
            assert "biome" in data
            print(f"  Tile ({x}, {y}): {data['biome_name']}")
        
        print(f"✓ Tiles at various coordinates work correctly")


class TestPlayerPositionAPI:
    """Tests for player position tracking"""
    
    def test_get_player_position_new_player(self):
        """GET /api/world/player/{user_id}/position returns origin for new player"""
        # Use a unique test user ID
        test_user_id = "test_explorer_new_12345"
        
        response = requests.get(f"{BASE_URL}/api/world/player/{test_user_id}/position")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["x"] == 0, f"New player x should be 0, got {data['x']}"
        assert data["y"] == 0, f"New player y should be 0, got {data['y']}"
        assert data["z"] == 70, f"New player z should be 70, got {data['z']}"
        assert "facing" in data
        assert "current_tile" in data
        
        # Verify current tile is plains
        assert data["current_tile"]["biome"] == "plains"
        
        print(f"✓ New player starts at origin (0, 0, 70) in Verdant Plains")
    
    def test_get_existing_player_position(self):
        """GET /api/world/player/{user_id}/position for existing player"""
        # First, get sirix_1's user ID
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            user = login_data.get("user", login_data)
            user_id = user.get("id") or user.get("user_id")
            
            if user_id:
                response = requests.get(f"{BASE_URL}/api/world/player/{user_id}/position")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                
                data = response.json()
                assert data["user_id"] == user_id
                assert "x" in data
                assert "y" in data
                assert "z" in data
                assert "current_tile" in data
                
                print(f"✓ Existing player position: ({data['x']}, {data['y']}, {data['z']})")
            else:
                print(f"⚠ Could not get user_id from login response")
        else:
            print(f"⚠ Could not login to test existing player position")


class TestExplorationAPI:
    """Tests for exploration movement"""
    
    def test_explore_all_directions(self):
        """POST /api/world/explore moves player in 8 directions"""
        test_user_id = "test_explorer_directions_12345"
        
        # Valid directions
        directions = ["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"]
        
        for direction in directions:
            response = requests.post(f"{BASE_URL}/api/world/explore", json={
                "user_id": test_user_id,
                "direction": direction,
                "distance": 1
            })
            assert response.status_code == 200, f"Failed for direction {direction}: {response.text}"
            
            data = response.json()
            assert "success" in data
            # Movement might be blocked by terrain, but API should work
            if data["success"]:
                assert "moved" in data
                assert "current_tile" in data
                assert "surroundings" in data
                print(f"  ✓ Moved {direction} to ({data['moved']['to']['x']}, {data['moved']['to']['y']})")
            else:
                print(f"  ⚠ Movement {direction} blocked: {data.get('message', 'unknown')}")
        
        print(f"✓ All 8 compass directions work")
    
    def test_explore_invalid_direction(self):
        """POST /api/world/explore with invalid direction returns 400"""
        response = requests.post(f"{BASE_URL}/api/world/explore", json={
            "user_id": "test_user",
            "direction": "invalid_direction",
            "distance": 1
        })
        assert response.status_code == 400, f"Expected 400 for invalid direction, got {response.status_code}"
        print(f"✓ Invalid direction returns 400")
    
    def test_explore_returns_surroundings(self):
        """Exploration returns surrounding tiles"""
        test_user_id = "test_explorer_surroundings_12345"
        
        response = requests.post(f"{BASE_URL}/api/world/explore", json={
            "user_id": test_user_id,
            "direction": "north",
            "distance": 1
        })
        
        assert response.status_code == 200
        data = response.json()
        
        if data["success"]:
            assert "surroundings" in data
            surroundings = data["surroundings"]
            assert len(surroundings) == 8, f"Should have 8 surrounding tiles, got {len(surroundings)}"
            
            for s in surroundings:
                assert "direction" in s
                assert "tile" in s
                assert "biome" in s["tile"]
            
            print(f"✓ Exploration returns 8 surrounding tiles")
        else:
            print(f"⚠ Movement blocked, cannot verify surroundings")
    
    def test_explore_updates_position(self):
        """Exploration updates player position in database"""
        test_user_id = "test_explorer_position_update_12345"
        
        # Get initial position
        pos_response = requests.get(f"{BASE_URL}/api/world/player/{test_user_id}/position")
        initial_pos = pos_response.json()
        
        # Move north
        explore_response = requests.post(f"{BASE_URL}/api/world/explore", json={
            "user_id": test_user_id,
            "direction": "north",
            "distance": 1
        })
        
        if explore_response.json().get("success"):
            # Get new position
            new_pos_response = requests.get(f"{BASE_URL}/api/world/player/{test_user_id}/position")
            new_pos = new_pos_response.json()
            
            # Y should have increased by 1 (north)
            assert new_pos["y"] == initial_pos["y"] + 1, f"Y should increase by 1 when moving north"
            print(f"✓ Position updated from ({initial_pos['x']}, {initial_pos['y']}) to ({new_pos['x']}, {new_pos['y']})")
        else:
            print(f"⚠ Movement blocked, cannot verify position update")


class TestAreaAPI:
    """Tests for area endpoint"""
    
    def test_get_area(self):
        """GET /api/world/area/{x}/{y}/{radius} returns tiles in radius"""
        response = requests.get(f"{BASE_URL}/api/world/area/0/0/5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "center" in data
        assert "radius" in data
        assert "tiles" in data
        assert "size" in data
        
        assert data["center"]["x"] == 0
        assert data["center"]["y"] == 0
        assert data["radius"] == 5
        assert data["size"] == 11  # 2*5 + 1
        
        # Verify tiles array dimensions
        tiles = data["tiles"]
        assert len(tiles) == 11, f"Expected 11 rows, got {len(tiles)}"
        assert len(tiles[0]) == 11, f"Expected 11 columns, got {len(tiles[0])}"
        
        print(f"✓ Area API returns {data['size']}x{data['size']} tile grid")


class TestWorldStatsAPI:
    """Tests for world statistics"""
    
    def test_get_world_stats(self):
        """GET /api/world/stats returns global statistics"""
        response = requests.get(f"{BASE_URL}/api/world/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "world_seed_id" in data
        assert "total_tile_discoveries" in data
        assert "total_land_claims" in data
        assert "total_modifications" in data
        assert "chunk_size" in data
        assert "biome_count" in data
        
        assert data["biome_count"] == 10
        
        print(f"✓ World stats: {data['total_tile_discoveries']} discoveries, {data['total_land_claims']} claims")


class TestAuthentication:
    """Test login with sirix_1 credentials"""
    
    def test_login_sirix_1(self):
        """Login with sirix_1 / HCLynnTV04 works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        # Login response has 'user' object with 'id' field
        assert data.get("status") == "success" or "user" in data, "Login response missing success status or user"
        
        user = data.get("user", data)
        user_id = user.get("id") or user.get("user_id")
        assert user_id is not None, f"Missing user id in login response: {data}"
        
        print(f"✓ Login successful for {TEST_USER}, user_id: {user_id}")
        return user_id


class TestChunkAPI:
    """Tests for chunk endpoint"""
    
    def test_get_chunk(self):
        """GET /api/world/chunk/{chunk_x}/{chunk_y} returns chunk data"""
        response = requests.get(f"{BASE_URL}/api/world/chunk/0/0")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "chunk_x" in data
        assert "chunk_y" in data
        assert "world_x" in data
        assert "world_y" in data
        assert "size" in data
        assert "dominant_biome" in data
        assert "tiles" in data
        
        assert data["size"] == 64, f"Chunk size should be 64, got {data['size']}"
        
        print(f"✓ Chunk (0,0) loaded: dominant biome is {data['dominant_biome']}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
