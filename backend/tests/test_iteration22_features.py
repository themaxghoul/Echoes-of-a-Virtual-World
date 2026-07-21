"""
Test Iteration 22 Features:
1. NPC Memory Delocalization System (/api/npc-memory/*)
2. Extended Materials & Components (/api/materials/*)
3. AI Digest Summary (/api/digest/*)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestNPCMemoryDelocalization:
    """Tests for NPC Memory Delocalization System"""
    
    def test_get_event_types(self):
        """Test GET /api/npc-memory/event-types returns event types and evidence types"""
        response = requests.get(f"{BASE_URL}/api/npc-memory/event-types")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify event_types structure
        assert "event_types" in data
        event_types = data["event_types"]
        assert "witnessed_action" in event_types
        assert "heard_rumor" in event_types
        assert "received_evidence" in event_types
        assert "fabricated_info" in event_types
        assert "confession" in event_types
        assert "deduced" in event_types
        
        # Verify witnessed_action has correct properties
        witnessed = event_types["witnessed_action"]
        assert witnessed["reliability"] == 1.0
        assert "decay_rate" in witnessed
        assert "description" in witnessed
        
        # Verify evidence_types structure
        assert "evidence_types" in data
        evidence_types = data["evidence_types"]
        assert "physical_item" in evidence_types
        assert "written_document" in evidence_types
        assert "magical_imprint" in evidence_types
        assert "witness_testimony" in evidence_types
        assert "divine_revelation" in evidence_types
        
        # Verify propagation_rules
        assert "propagation_rules" in data
        rules = data["propagation_rules"]
        assert "gossip_chance" in rules
        assert "max_propagation_hops" in rules
        assert rules["max_propagation_hops"] == 5
    
    def test_get_memory_system_stats(self):
        """Test GET /api/npc-memory/stats returns system statistics"""
        response = requests.get(f"{BASE_URL}/api/npc-memory/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_world_events" in data
        assert "total_npc_memories" in data
        assert "active_evidence" in data
        assert "memory_breakdown" in data
        assert "system_description" in data


class TestMaterialsAndComponents:
    """Tests for Extended Materials & Components System"""
    
    def test_list_all_materials(self):
        """Test GET /api/materials/list returns 27 materials in 6 categories"""
        response = requests.get(f"{BASE_URL}/api/materials/list")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify total count
        assert "total" in data
        assert data["total"] == 27
        
        # Verify materials structure
        assert "materials" in data
        materials = data["materials"]
        assert len(materials) == 27
        
        # Verify categories
        assert "categories" in data
        categories = data["categories"]
        assert len(categories) == 6
        expected_categories = {"basic", "metal", "crystal", "organic", "essence", "alchemical"}
        assert set(categories) == expected_categories
        
        # Verify rarity colors
        assert "rarity_colors" in data
        rarity_colors = data["rarity_colors"]
        assert "common" in rarity_colors
        assert "uncommon" in rarity_colors
        assert "rare" in rarity_colors
        assert "epic" in rarity_colors
        assert "legendary" in rarity_colors
        assert "mythic" in rarity_colors
        
        # Verify specific materials exist
        assert "timber" in materials
        assert "mithril" in materials
        assert "echo_crystal" in materials
        assert "phoenix_feather" in materials
        assert "chaos_essence" in materials
    
    def test_list_all_components(self):
        """Test GET /api/materials/components returns craftable components"""
        response = requests.get(f"{BASE_URL}/api/materials/components")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify total count
        assert "total" in data
        assert data["total"] == 16
        
        # Verify components structure
        assert "components" in data
        components = data["components"]
        assert len(components) == 16
        
        # Verify categories
        assert "categories" in data
        categories = data["categories"]
        expected_categories = {"structural", "magical", "decorative", "mechanical"}
        assert set(categories) == expected_categories
        
        # Verify specific components exist
        assert "wooden_beam" in components
        assert "rune_stone" in components
        assert "clockwork_core" in components
        
        # Verify component has crafting recipe
        wooden_beam = components["wooden_beam"]
        assert "crafting_recipe" in wooden_beam
        assert "timber" in wooden_beam["crafting_recipe"]
    
    def test_get_specific_material(self):
        """Test GET /api/materials/{material_id} returns material details"""
        response = requests.get(f"{BASE_URL}/api/materials/mithril")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "mithril"
        assert data["name"] == "Mithril"
        assert data["category"] == "metal"
        assert data["rarity"] == "legendary"
        assert "magical_properties" in data
        assert data["magical_properties"]["weight_reduction"] == 0.5
    
    def test_get_specific_component(self):
        """Test GET /api/materials/component/{component_id} returns component details"""
        response = requests.get(f"{BASE_URL}/api/materials/component/clockwork_core")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "clockwork_core"
        assert data["name"] == "Clockwork Core"
        assert data["category"] == "mechanical"
        assert "crafting_recipe" in data
        assert data["min_skill_level"] == 9
    
    def test_get_materials_by_location(self):
        """Test GET /api/materials/by-location/{location_id} returns gatherable materials"""
        response = requests.get(f"{BASE_URL}/api/materials/by-location/shadow_grove")
        assert response.status_code == 200
        
        data = response.json()
        assert data["location_id"] == "shadow_grove"
        assert "materials" in data
        assert "count" in data
        
        # Shadow grove should have timber, clay, ancient_bark, shadow_essence, bloodstone
        material_ids = [m["id"] for m in data["materials"]]
        assert "timber" in material_ids
        assert "ancient_bark" in material_ids
        assert "shadow_essence" in material_ids
    
    def test_get_materials_by_rarity(self):
        """Test GET /api/materials/by-rarity/{rarity} returns materials of that rarity"""
        response = requests.get(f"{BASE_URL}/api/materials/by-rarity/legendary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["rarity"] == "legendary"
        assert "color" in data
        assert "materials" in data
        
        # All returned materials should be legendary
        for material in data["materials"]:
            assert material["rarity"] == "legendary"
    
    def test_get_crafting_tree(self):
        """Test GET /api/materials/crafting-tree/{material_id} returns full crafting tree"""
        response = requests.get(f"{BASE_URL}/api/materials/crafting-tree/steel")
        assert response.status_code == 200
        
        data = response.json()
        assert "crafting_tree" in data
        tree = data["crafting_tree"]
        assert tree["id"] == "steel"
        assert tree["type"] == "material"
        assert "requires" in tree


class TestAIDigestSummary:
    """Tests for AI Digest Summary System"""
    
    def test_get_compact_digest(self):
        """Test GET /api/digest/compact returns minimal AI digest"""
        response = requests.get(f"{BASE_URL}/api/digest/compact")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required fields
        assert "game" in data
        assert "AI Village: The Echoes" in data["game"]
        
        assert "core" in data
        assert "memory" in data
        assert "DELOCALIZED" in data["memory"]
        
        assert "first_discovery" in data
        assert "modes" in data
        assert len(data["modes"]) >= 2
        
        assert "regions" in data
        assert data["regions"] == 8
        
        assert "currencies" in data
        assert "gold" in data["currencies"]
        assert "VE$" in data["currencies"]
        
        assert "admin" in data
        assert "sirix_1" in data["admin"]
        
        assert "generated" in data
    
    def test_get_full_digest(self):
        """Test GET /api/digest/full returns comprehensive game state digest"""
        response = requests.get(f"{BASE_URL}/api/digest/full")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify digest version and timestamp
        assert "digest_version" in data
        assert data["digest_version"] == "1.0"
        assert "generated_at" in data
        
        # Verify game identity
        assert "game_identity" in data
        identity = data["game_identity"]
        assert identity["title"] == "AI Village: The Echoes"
        assert identity["version"] == "0.1.0"
        assert identity["codename"] == "The Echoes"
        
        # Verify core loop
        assert "core_loop" in data
        core = data["core_loop"]
        assert "description" in core
        assert "primary_activities" in core
        assert "currencies" in core
        
        # Verify game modes
        assert "game_modes" in data
        modes = data["game_modes"]
        assert "active" in modes
        assert "coming_soon" in modes
        
        # Verify world structure
        assert "world_structure" in data
        world = data["world_structure"]
        assert world["name"] == "The Echoes"
        assert "regions" in world
        assert len(world["regions"]) == 8
        
        # Verify NPC system
        assert "npc_system" in data
        npc = data["npc_system"]
        assert "memory_model" in npc
        assert npc["memory_model"]["type"] == "delocalized"
        
        # Verify memory delocalization
        assert "memory_delocalization" in data
        memory = data["memory_delocalization"]
        assert "rules" in memory
        assert "implications" in memory
        
        # Verify economic system
        assert "economic_system" in data
        economy = data["economic_system"]
        assert "task_marketplace" in economy
        assert "ai_partners" in economy
        assert "bounty_board" in economy
        
        # Verify materials and crafting
        assert "materials_and_crafting" in data
        materials = data["materials_and_crafting"]
        assert "material_categories" in materials
        assert len(materials["material_categories"]) == 6
        
        # Verify current statistics
        assert "current_statistics" in data
        stats = data["current_statistics"]
        assert "total_users" in stats
        assert "total_characters" in stats
        
        # Verify AI context notes
        assert "ai_context_notes" in data
        notes = data["ai_context_notes"]
        assert "for_npcs" in notes
        assert "for_storytelling" in notes
        assert "for_economy" in notes
    
    def test_get_world_state_digest(self):
        """Test GET /api/digest/world-state returns current world state"""
        response = requests.get(f"{BASE_URL}/api/digest/world-state")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "timestamp" in data
        assert "world" in data
        assert data["world"] == "The Echoes"
        assert "state" in data
        assert "simulation_notes" in data
    
    def test_get_npc_context_digest(self):
        """Test GET /api/digest/for-npc/{npc_id} returns NPC-specific context"""
        response = requests.get(f"{BASE_URL}/api/digest/for-npc/elder_morvain")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "npc_id" in data
        assert data["npc_id"] == "elder_morvain"
        assert "knowledge_scope" in data
        assert "context_note" in data
        assert "ONLY reference information" in data["context_note"]


class TestMaterialNotFound:
    """Tests for error handling"""
    
    def test_material_not_found(self):
        """Test GET /api/materials/{invalid_id} returns 404"""
        response = requests.get(f"{BASE_URL}/api/materials/nonexistent_material")
        assert response.status_code == 404
    
    def test_component_not_found(self):
        """Test GET /api/materials/component/{invalid_id} returns 404"""
        response = requests.get(f"{BASE_URL}/api/materials/component/nonexistent_component")
        assert response.status_code == 404
    
    def test_invalid_rarity(self):
        """Test GET /api/materials/by-rarity/{invalid} returns 400"""
        response = requests.get(f"{BASE_URL}/api/materials/by-rarity/invalid_rarity")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
