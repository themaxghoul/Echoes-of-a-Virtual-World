"""
AI Digest Summary System
========================
Provides a comprehensive, machine-readable digest of the current
game state for AI models to understand fluently.

This endpoint generates structured summaries optimized for:
- LLM context injection
- NPC behavior modeling
- Game state serialization
- Cross-system synchronization
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/digest", tags=["AI Digest Summary"])

# Current version info
VERSION_INFO = {
    "version": "0.1.0",
    "codename": "The Echoes",
    "release_stage": "pre-release",
    "target_platform": "itch.io"
}


@router.get("/full")
async def get_full_digest():
    """
    Generate a complete AI-digestible summary of the current game version.
    Optimized for LLM context injection and NPC behavior modeling.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Gather statistics
    total_users = await db.user_profiles.count_documents({})
    total_characters = await db.characters.count_documents({})
    total_conversations = await db.conversations.count_documents({})
    total_memories = await db.npc_memories.count_documents({})
    total_bounties = await db.bounties.count_documents({})
    
    digest = {
        "digest_version": "1.0",
        "generated_at": timestamp,
        "game_identity": {
            "title": "AI Village: The Echoes",
            "version": VERSION_INFO["version"],
            "codename": VERSION_INFO["codename"],
            "release_stage": VERSION_INFO["release_stage"],
            "developer": "ApexForge Collective",
            "genre": ["Virtual World", "AI Simulation", "Sandbox RPG", "Economy Simulation"]
        },
        
        "core_loop": {
            "description": "Players inhabit a persistent virtual world alongside evolving AI NPCs. Core activities include exploration, trading, building, crafting, completing tasks for VE$ (real-value currency), and developing relationships with AI companions.",
            "primary_activities": [
                "Story Mode exploration with AI NPCs",
                "2D Isometric building and property ownership",
                "Task completion for VE$ earnings (real money value)",
                "AI Partner programs for passive income",
                "Quest and bounty completion",
                "Material gathering and crafting",
                "Multiplayer chat and social interaction"
            ],
            "currencies": {
                "gold": "In-game currency for NPC trades and basic purchases",
                "ve_dollars": "VE$ - Real-value currency, withdrawable via Stripe or crypto"
            }
        },
        
        "game_modes": {
            "active": [
                {
                    "mode": "Story Mode (2D Chat Adventure)",
                    "status": "fully_playable",
                    "description": "Text-based adventure with AI narrator and NPCs. All maps open. Skills gain XP through conversation and actions."
                },
                {
                    "mode": "2D Isometric Building",
                    "status": "fully_playable",
                    "description": "Grid-based building system. Purchase plots, place prefabs, earn daily income from buildings."
                }
            ],
            "coming_soon": [
                {
                    "mode": "First Person 3D (Web)",
                    "status": "development",
                    "description": "Immersive 3D browser experience with top-down stylized world map."
                },
                {
                    "mode": "Unity 3D",
                    "status": "development",
                    "description": "High-fidelity Unity client with cross-platform character sync."
                }
            ]
        },
        
        "world_structure": {
            "name": "The Echoes",
            "type": "Single persistent seed world",
            "regions": [
                {"id": "village_square", "name": "The Hollow Square", "type": "hub", "terrain": "cobblestone"},
                {"id": "oracle_sanctum", "name": "Oracle's Sanctum", "type": "mystical", "terrain": "mystical_stone"},
                {"id": "the_forge", "name": "The Ember Forge", "type": "crafting", "terrain": "volcanic"},
                {"id": "ancient_library", "name": "Ancient Library", "type": "knowledge", "terrain": "marble"},
                {"id": "wanderers_rest", "name": "Wanderer's Rest", "type": "social", "terrain": "forest_clearing"},
                {"id": "shadow_grove", "name": "Shadow Grove", "type": "dangerous", "terrain": "dark_forest"},
                {"id": "watchtower", "name": "The Watchtower", "type": "defense", "terrain": "highland"},
                {"id": "outer_realms", "name": "Outer Realms", "type": "endgame", "terrain": "ethereal"}
            ],
            "time_system": "Dynamic day/night with danger scaling",
            "demon_system": "Biblical demons spawn during night/witching hour"
        },
        
        "npc_system": {
            "architecture": "Fully autonomous AI with persistent memory",
            "memory_model": {
                "type": "delocalized",
                "description": "NPCs only recall events they personally witnessed OR received evidence about. Memory does NOT spread automatically - it requires explicit transfer through gossip, evidence, or confession.",
                "reliability_decay": True,
                "propagation_limit": 5
            },
            "personality_traits": 8,
            "free_will_scale": "0.0 to 1.0",
            "capabilities": [
                "Independent decision making",
                "AI-to-AI conversations",
                "Emotional state tracking",
                "Relationship memory",
                "Economic participation (earn VE$)",
                "Autonomous actions (20+ types)"
            ],
            "notable_npcs": [
                "Elder Morvain (Village leader)",
                "Lyra the Wanderer (Explorer)",
                "Kael Ironbrand (Forge master)",
                "Archivist Nyx (Knowledge keeper)",
                "Oracle Veythra (Prophecy and divination)",
                "The Hooded Stranger (Mysterious)"
            ]
        },
        
        "memory_delocalization": {
            "concept": "Memory states are NOT centralized. Each NPC maintains individual memory that only updates when they personally encounter information.",
            "rules": [
                "Witnessed events have 100% reliability",
                "Gossip/rumors have 70% base reliability, decreasing with each transfer",
                "Evidence-based memories have 90% reliability",
                "Memory degrades after 5 propagation hops",
                "NPCs can be deceived with fabricated information",
                "Physical evidence can be destroyed to prevent memory spread"
            ],
            "implications": [
                "Secrets remain hidden unless witnesses talk",
                "Players can manipulate information flow",
                "False information can spread organically",
                "NPC knowledge is verifiable and traceable"
            ]
        },
        
        "first_discovery_system": {
            "concept": "New spells, materials, or combinations cannot be automated on first attempt",
            "rules": [
                "Untested experiments require an animate entity (human player) present",
                "Valid roles: Experiment Manager (cannot automate), Assistant, Machine Operator",
                "After first successful discovery, subsequent runs MAY be automated",
                "First discoverer receives permanent credit, bonus VE$, and potential royalties"
            ],
            "purpose": "Prevents AFK farming of new discoveries, rewards genuine exploration"
        },
        
        "economic_system": {
            "task_marketplace": {
                "description": "Hybrid marketplace for human and AI tasks",
                "payment_types": ["VE$ only", "Stripe (real money)", "Hybrid (both)"],
                "platform_fee": "10%",
                "categories": 10,
                "difficulty_multipliers": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
            },
            "ai_partners": {
                "description": "AI programs that generate passive income",
                "programs": 10,
                "trust_levels": 6,
                "earnings_multiplier": "0.6x (Stranger) to 1.5x (Soulbound)"
            },
            "bounty_board": {
                "description": "Exclusive in-game tasks that cannot be automated",
                "types": ["Rescue Mission", "Scout Uncharted", "Dangerous Recon", "Diplomatic Meeting", "Artifact Recovery", "Monster Bounty", "First Discovery"],
                "ve_multipliers": [1.2, 1.3, 1.5, 1.6, 1.8, 2.0]
            },
            "compute_marketplace": {
                "description": "Buy cloud compute or hardware for passive income",
                "cloud_tiers": 6,
                "self_hardware": 5
            }
        },
        
        "materials_and_crafting": {
            "material_categories": ["basic", "metal", "crystal", "organic", "essence", "alchemical"],
            "component_categories": ["structural", "magical", "decorative", "mechanical"],
            "rarity_tiers": ["common", "uncommon", "rare", "epic", "legendary", "mythic"],
            "notable_materials": [
                "Mithril (lightweight magical metal)",
                "Adamantine (nearly indestructible)",
                "Echo Crystal (mana storage)",
                "Void Obsidian (shadow affinity)",
                "Phoenix Feather (rebirth chance)",
                "Chaos Essence (unstable void energy)"
            ]
        },
        
        "progression_systems": {
            "skills": {
                "total_skills": 30,
                "categories": 6,
                "trees": 5,
                "skills_per_tree": 7
            },
            "titles": {
                "total_titles": 31,
                "categories": 6,
                "rarities": 7,
                "max_buff": "1000% (10x multiplier)"
            },
            "ranks": {
                "progression": "F → E → D → C → B → A → S → SS → SSS → ★1 → ★2 → ★∞",
                "rebirth": "Achievement-based, not death-based",
                "first_rebirth": "Requires SSS rank (1,000,000 XP)"
            }
        },
        
        "admin_system": {
            "supreme_admin": {
                "username": "sirix_1",
                "permission_level": 999,
                "abilities": ["all", "immutable", "supreme_override"],
                "is_transcendent": True,
                "special_access": "Exclusive private realm"
            },
            "permission_hierarchy": ["basic (1)", "advanced (2)", "admin (3)", "sirix_1 (999)"]
        },
        
        "multiplayer": {
            "chat_channels": ["Global", "Region", "Party", "Whisper"],
            "features": ["WebSocket real-time", "Typing indicators", "Party system", "Block system"],
            "world_type": "Persistent single-seed (all players share one world)"
        },
        
        "technical_stack": {
            "frontend": "React (PWA)",
            "backend": "FastAPI (Python)",
            "database": "MongoDB",
            "realtime": "WebSockets",
            "payments": "Stripe Connect",
            "ai_integration": "LiteLLM with Emergent Key"
        },
        
        "current_statistics": {
            "total_users": total_users,
            "total_characters": total_characters,
            "total_conversations": total_conversations,
            "npc_memories": total_memories,
            "active_bounties": total_bounties
        },
        
        "api_summary": {
            "core_endpoints": [
                "/api/chat - NPC conversations",
                "/api/characters - Character management",
                "/api/npc-memory/* - Delocalized memory system",
                "/api/materials/* - Materials and crafting",
                "/api/task-marketplace/* - Task system",
                "/api/bounty-board/* - Exclusive bounties",
                "/api/skill-trees/* - Progression",
                "/api/ranks/* - Adventurer ranks"
            ]
        },
        
        "ai_context_notes": {
            "for_npcs": "When roleplaying NPCs, remember they only know what their personal memory contains. Query /api/npc-memory/{npc_id}/memories before responding as an NPC.",
            "for_storytelling": "The world operates on delocalized memory - information doesn't magically spread. Dramatic tension can build around who knows what.",
            "for_economy": "VE$ has real value. NPCs and players both participate in the economy. First discoveries grant lasting benefits."
        }
    }
    
    return digest


@router.get("/compact")
async def get_compact_digest():
    """
    Generate a minimal digest for quick context injection.
    Suitable for LLM prompts with limited token budgets.
    """
    return {
        "game": "AI Village: The Echoes v0.1.0",
        "core": "Virtual world with autonomous AI NPCs, real-value economy (VE$), building, quests",
        "memory": "DELOCALIZED - NPCs only know witnessed/evidence-received events",
        "first_discovery": "New experiments require human present; automation allowed after first success",
        "modes": ["Story Mode (active)", "2D Building (active)", "3D (coming soon)"],
        "regions": 8,
        "currencies": {"gold": "in-game", "VE$": "real-withdrawable"},
        "admin": "sirix_1 (level 999, supreme)",
        "generated": datetime.now(timezone.utc).isoformat()
    }


@router.get("/for-npc/{npc_id}")
async def get_npc_context_digest(npc_id: str):
    """
    Generate a context digest specifically for an NPC's perspective.
    Includes only what the NPC would know based on their memories.
    """
    # Get NPC memories
    cursor = db.npc_memories.find(
        {"npc_id": npc_id, "reliability": {"$gte": 0.3}},
        {"_id": 0}
    )
    memories = await cursor.to_list(length=100)
    
    # Get NPC info
    npc_info = await db.npcs.find_one({"npc_id": npc_id}, {"_id": 0})
    
    # Compile known entities
    known_actors = set()
    known_locations = set()
    known_events = []
    
    for mem in memories:
        if mem.get("actor_name"):
            known_actors.add(mem["actor_name"])
        if mem.get("target_name"):
            known_actors.add(mem["target_name"])
        if mem.get("location_name"):
            known_locations.add(mem["location_name"])
        known_events.append({
            "what": f"{mem.get('actor_name', 'Someone')} {mem.get('action', 'did something')}",
            "where": mem.get("location_name"),
            "reliability": mem.get("reliability", 0),
            "source": mem.get("memory_type")
        })
    
    return {
        "npc_id": npc_id,
        "npc_info": npc_info,
        "knowledge_scope": {
            "known_individuals": list(known_actors),
            "known_locations": list(known_locations),
            "memory_count": len(memories),
            "average_reliability": sum(m.get("reliability", 0) for m in memories) / max(len(memories), 1)
        },
        "known_events": sorted(known_events, key=lambda x: -x.get("reliability", 0))[:20],
        "context_note": "This NPC should ONLY reference information from their known events. They do not have access to centralized world knowledge."
    }


@router.get("/world-state")
async def get_world_state_digest():
    """
    Get current world state for AI world simulation.
    """
    # Get recent world events
    cursor = db.world_events.find({}, {"_id": 0}).sort("timestamp", -1).limit(50)
    recent_events = await cursor.to_list(length=50)
    
    # Get active bounties
    bounties = await db.bounties.find(
        {"status": "available"},
        {"_id": 0}
    ).to_list(length=20)
    
    # Get online users (simplified)
    online_count = await db.user_sessions.count_documents({"active": True})
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "world": "The Echoes",
        "state": {
            "online_players": online_count,
            "recent_events_count": len(recent_events),
            "active_bounties": len(bounties)
        },
        "recent_events": recent_events[:10],
        "available_bounties": bounties,
        "simulation_notes": [
            "World operates on delocalized memory",
            "Day/night cycle affects danger levels",
            "NPCs make autonomous decisions",
            "Economy is shared between players and AI"
        ]
    }
