# AI World Engine - Dynamic World State Management
# Enables NPCs to commit real actions, spawn events, and change the world

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import random
import logging

world_engine_router = APIRouter(prefix="/world-engine", tags=["world-engine"])

logger = logging.getLogger(__name__)

# ============ World Event Types ============

class EventType(str, Enum):
    BOSS_SPAWN = "boss_spawn"
    INVASION = "invasion"
    DIPLOMATIC_CRISIS = "diplomatic_crisis"
    RESOURCE_DISCOVERY = "resource_discovery"
    PLAGUE = "plague"
    FESTIVAL = "festival"
    MERCHANT_CARAVAN = "merchant_caravan"
    NATURAL_DISASTER = "natural_disaster"
    PROPHECY = "prophecy"
    REBELLION = "rebellion"
    ALLIANCE_OFFER = "alliance_offer"
    WAR_DECLARATION = "war_declaration"
    MYSTERIOUS_STRANGER = "mysterious_stranger"
    ARTIFACT_APPEARANCE = "artifact_appearance"
    PORTAL_OPENING = "portal_opening"

class EventSeverity(str, Enum):
    MINOR = "minor"       # Local effect, 1 location
    MODERATE = "moderate" # Regional effect, 2-3 locations
    MAJOR = "major"       # Wide effect, all locations
    CATASTROPHIC = "catastrophic" # World-altering

# ============ Boss Definitions ============

WORLD_BOSSES = {
    "shadow_lord": {
        "name": "Malachar the Shadow Lord",
        "title": "Ruler of the Void",
        "health": 5000,
        "damage": 100,
        "defense": 50,
        "abilities": ["void_strike", "shadow_army", "darkness_aura", "soul_drain"],
        "spawn_locations": ["shadow_grove", "watchtower"],
        "loot": {"obsidian": 50, "essence": 200, "gold": 1000, "artifacts": 3},
        "dialogue": {
            "spawn": "Mortals... your light fades. The void consumes all.",
            "taunt": "Your struggles amuse me. Dance, little souls.",
            "damaged": "You dare wound ME? I am eternal darkness!",
            "defeat": "This... changes nothing. The shadows will return..."
        },
        "diplomatic": False,
        "can_negotiate": False
    },
    "demon_prince": {
        "name": "Azrael, Prince of Flames",
        "title": "Herald of the Burning Abyss",
        "health": 4000,
        "damage": 120,
        "defense": 30,
        "abilities": ["hellfire_rain", "summon_demons", "infernal_pact", "corrupting_touch"],
        "spawn_locations": ["the_forge", "village_square"],
        "loot": {"iron": 100, "essence": 150, "gold": 800, "artifacts": 2},
        "dialogue": {
            "spawn": "The flames of hell have come to cleanse this land!",
            "taunt": "Burn! BURN! Let me hear your screams!",
            "damaged": "Pain... is just fuel for my flames!",
            "defeat": "My father will avenge me... the abyss never forgets..."
        },
        "diplomatic": True,
        "can_negotiate": True,
        "negotiation_demands": ["souls", "territory", "artifacts"]
    },
    "ancient_dragon": {
        "name": "Vyrmathax the Eternal",
        "title": "Last of the Elder Dragons",
        "health": 8000,
        "damage": 150,
        "defense": 80,
        "abilities": ["dragon_breath", "wing_buffet", "ancient_magic", "time_distortion"],
        "spawn_locations": ["watchtower", "ancient_library"],
        "loot": {"crystal": 100, "obsidian": 75, "gold": 2000, "artifacts": 5},
        "dialogue": {
            "spawn": "I have slumbered for millennia. Who disturbs my rest?",
            "taunt": "Insects. I have seen civilizations rise and fall.",
            "damaged": "Impressive... for mortals. But futile.",
            "defeat": "At last... I may rest... guard my hoard well..."
        },
        "diplomatic": True,
        "can_negotiate": True,
        "negotiation_demands": ["knowledge", "respect", "treasure"]
    },
    "lich_king": {
        "name": "Netharis the Undying",
        "title": "Master of the Dead",
        "health": 3500,
        "damage": 80,
        "defense": 40,
        "abilities": ["raise_dead", "death_coil", "phylactery_shield", "life_drain"],
        "spawn_locations": ["ancient_library", "oracle_sanctum"],
        "loot": {"essence": 300, "crystal": 50, "gold": 600, "artifacts": 2},
        "dialogue": {
            "spawn": "Death is not the end... it is merely a new beginning.",
            "taunt": "Join my legion. Eternal service... or eternal torment.",
            "damaged": "This body is merely a vessel. I cannot truly die.",
            "defeat": "Find my phylactery... if you dare. I will return."
        },
        "diplomatic": True,
        "can_negotiate": True,
        "negotiation_demands": ["corpses", "dark_knowledge", "souls"]
    },
    "merchant_king": {
        "name": "Goldric the Magnificent",
        "title": "Master of Coin and Contract",
        "health": 2000,
        "damage": 40,
        "defense": 100,
        "abilities": ["bribe", "mercenary_army", "golden_shield", "economic_warfare"],
        "spawn_locations": ["village_square", "wanderers_rest"],
        "loot": {"gold": 5000, "trade_goods": 100},
        "dialogue": {
            "spawn": "Everything has a price. What's yours?",
            "taunt": "Money talks. And mine is SCREAMING.",
            "damaged": "Guards! I'm paying you triple!",
            "defeat": "Fine! Take my gold! But remember... wealth always returns to the wise."
        },
        "diplomatic": True,
        "can_negotiate": True,
        "negotiation_demands": ["trade_rights", "monopoly", "tribute"]
    }
}

# ============ Diplomatic Factions ============

FACTIONS = {
    "village_council": {
        "name": "Village Council",
        "description": "The governing body of the village",
        "alignment": "lawful_good",
        "resources": {"gold": 1000, "soldiers": 50},
        "relations": {"shadow_cult": -50, "merchant_guild": 30, "mage_circle": 20},
        "leader": "Elder Morin",
        "demands": ["peace", "prosperity", "protection"]
    },
    "shadow_cult": {
        "name": "Cult of the Void",
        "description": "Dark worshippers seeking to unleash ancient evils",
        "alignment": "chaotic_evil",
        "resources": {"essence": 500, "cultists": 30},
        "relations": {"village_council": -50, "demon_horde": 40},
        "leader": "High Priest Vex",
        "demands": ["sacrifices", "territory", "artifacts"]
    },
    "merchant_guild": {
        "name": "Merchant's Consortium",
        "description": "Traders seeking profit above all else",
        "alignment": "true_neutral",
        "resources": {"gold": 5000, "mercenaries": 20},
        "relations": {"village_council": 30, "bandit_clan": -20},
        "leader": "Guildmaster Helena",
        "demands": ["trade_routes", "tax_exemption", "monopoly"]
    },
    "demon_horde": {
        "name": "Legions of the Abyss",
        "description": "Demonic forces from the lower planes",
        "alignment": "chaotic_evil",
        "resources": {"demons": 100, "hellfire": 200},
        "relations": {"village_council": -80, "shadow_cult": 40},
        "leader": "Archdemon Bael",
        "demands": ["souls", "destruction", "conquest"]
    },
    "mage_circle": {
        "name": "Circle of Echoes",
        "description": "Mystical order preserving ancient knowledge",
        "alignment": "lawful_neutral",
        "resources": {"essence": 300, "mages": 15, "artifacts": 10},
        "relations": {"village_council": 20, "shadow_cult": -30},
        "leader": "Archmage Seraphina",
        "demands": ["knowledge", "magical_items", "research_access"]
    }
}

# ============ Dynamic Event Templates ============

EVENT_TEMPLATES = {
    "boss_spawn": {
        "title": "{boss_name} Emerges!",
        "description": "{boss_title} has appeared at {location}! Heroes must unite to face this threat.",
        "duration_minutes": 60,
        "rewards_multiplier": 3.0,
        "participation_required": 3
    },
    "diplomatic_crisis": {
        "title": "Diplomatic Crisis: {faction_a} vs {faction_b}",
        "description": "Tensions have erupted between {faction_a} and {faction_b}. War looms unless mediators intervene.",
        "duration_minutes": 120,
        "resolution_options": ["negotiate", "side_with_a", "side_with_b", "sabotage_both"],
        "consequences": {
            "negotiate": {"reputation_both": 20, "gold": 500},
            "side_with_a": {"reputation_a": 50, "reputation_b": -50},
            "side_with_b": {"reputation_a": -50, "reputation_b": 50},
            "sabotage_both": {"reputation_both": -30, "chaos": 50}
        }
    },
    "invasion": {
        "title": "Invasion! {enemy} attacks {location}!",
        "description": "A horde of {enemy} has begun attacking {location}. Defend the village!",
        "duration_minutes": 30,
        "waves": 5,
        "enemies_per_wave": 10
    },
    "prophecy": {
        "title": "The Oracle Speaks",
        "description": "Oracle Veythra has received a vision: '{prophecy_text}'",
        "duration_minutes": 1440,  # 24 hours
        "effects": ["world_modifier"]
    },
    "artifact_appearance": {
        "title": "Artifact Discovered: {artifact_name}",
        "description": "A powerful artifact '{artifact_name}' has been discovered at {location}. Multiple factions seek it.",
        "duration_minutes": 180,
        "claimants": ["village_council", "shadow_cult", "merchant_guild"]
    }
}

# ============ Models ============

class WorldEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    severity: EventSeverity
    title: str
    description: str
    location_ids: List[str]
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ends_at: Optional[str] = None
    status: str = "active"  # active, resolved, failed, expired
    participants: List[str] = Field(default_factory=list)
    boss_id: Optional[str] = None
    faction_ids: List[str] = Field(default_factory=list)
    resolution: Optional[Dict[str, Any]] = None
    rewards_distributed: bool = False

class BossInstance(BaseModel):
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    boss_key: str
    current_health: int
    max_health: int
    location_id: str
    spawned_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "alive"  # alive, defeated, fled, negotiated
    damage_dealt_by: Dict[str, int] = Field(default_factory=dict)  # player_id: damage
    in_negotiation: bool = False
    negotiation_terms: Optional[Dict[str, Any]] = None

class DiplomaticAction(BaseModel):
    user_id: str
    action_type: str  # negotiate, declare_war, offer_alliance, demand, gift
    target_faction: str
    terms: Optional[Dict[str, Any]] = None

class AIWorldAction(BaseModel):
    """Action that AI NPCs can commit to change the world"""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    actor_type: str  # npc, villager, boss, faction
    actor_id: str
    action_type: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    executed: bool = False
    result: Optional[Dict[str, Any]] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ World State ============

# In-memory world state (persisted to DB periodically)
WORLD_STATE = {
    "current_events": [],
    "active_bosses": {},
    "faction_relations": {},
    "world_modifiers": [],
    "chaos_level": 0,  # 0-100, affects spawn rates
    "prosperity_level": 50,  # 0-100, affects prices and moods
    "danger_level": 20,  # 0-100, affects demon spawns
    "last_major_event": None
}

# ============ World Engine Core ============

@world_engine_router.get("/state")
async def get_world_state():
    """Get current world state"""
    db = get_db()
    
    # Get active events
    active_events = await db.world_events.find(
        {"status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    # Get active bosses
    active_bosses = await db.boss_instances.find(
        {"status": "alive"},
        {"_id": 0}
    ).to_list(10)
    
    # Get faction states
    factions = await db.faction_states.find({}, {"_id": 0}).to_list(20)
    
    return {
        "world_state": {
            "chaos_level": WORLD_STATE["chaos_level"],
            "prosperity_level": WORLD_STATE["prosperity_level"],
            "danger_level": WORLD_STATE["danger_level"]
        },
        "active_events": active_events,
        "active_bosses": active_bosses,
        "factions": factions if factions else list(FACTIONS.values()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@world_engine_router.post("/spawn-boss")
async def spawn_boss(boss_key: str, location_id: str, triggered_by: Optional[str] = None):
    """Spawn a world boss at a location"""
    db = get_db()
    
    if boss_key not in WORLD_BOSSES:
        raise HTTPException(status_code=404, detail=f"Unknown boss: {boss_key}")
    
    boss_data = WORLD_BOSSES[boss_key]
    
    # Check if boss already active
    existing = await db.boss_instances.find_one({
        "boss_key": boss_key,
        "status": "alive"
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="This boss is already active in the world")
    
    # Create boss instance
    boss_instance = BossInstance(
        boss_key=boss_key,
        current_health=boss_data["health"],
        max_health=boss_data["health"],
        location_id=location_id
    )
    
    await db.boss_instances.insert_one(boss_instance.dict())
    
    # Create world event
    event = WorldEvent(
        event_type=EventType.BOSS_SPAWN,
        severity=EventSeverity.MAJOR,
        title=f"{boss_data['name']} Emerges!",
        description=f"{boss_data['title']} has appeared at {location_id}! {boss_data['dialogue']['spawn']}",
        location_ids=[location_id],
        boss_id=boss_instance.instance_id
    )
    
    await db.world_events.insert_one(event.dict())
    
    # Increase world danger
    WORLD_STATE["danger_level"] = min(100, WORLD_STATE["danger_level"] + 20)
    
    logger.info(f"Boss spawned: {boss_data['name']} at {location_id}")
    
    return {
        "boss_spawned": True,
        "instance_id": boss_instance.instance_id,
        "boss": boss_data,
        "event_id": event.event_id,
        "message": boss_data["dialogue"]["spawn"]
    }

@world_engine_router.post("/attack-boss/{instance_id}")
async def attack_boss(instance_id: str, attacker_id: str, damage: int):
    """Attack a boss and track damage"""
    db = get_db()
    
    boss = await db.boss_instances.find_one({"instance_id": instance_id})
    if not boss:
        raise HTTPException(status_code=404, detail="Boss not found")
    
    if boss["status"] != "alive":
        raise HTTPException(status_code=400, detail=f"Boss is {boss['status']}")
    
    boss_data = WORLD_BOSSES[boss["boss_key"]]
    
    # Apply damage
    new_health = max(0, boss["current_health"] - damage)
    
    # Track damage by player
    damage_dealt = boss.get("damage_dealt_by", {})
    damage_dealt[attacker_id] = damage_dealt.get(attacker_id, 0) + damage
    
    # Update boss
    update_data = {
        "current_health": new_health,
        "damage_dealt_by": damage_dealt
    }
    
    response_dialogue = boss_data["dialogue"]["damaged"]
    
    # Check if defeated
    if new_health <= 0:
        update_data["status"] = "defeated"
        update_data["defeated_at"] = datetime.now(timezone.utc).isoformat()
        response_dialogue = boss_data["dialogue"]["defeat"]
        
        # Distribute loot
        await distribute_boss_loot(db, boss, boss_data)
        
        # Update world state
        WORLD_STATE["danger_level"] = max(0, WORLD_STATE["danger_level"] - 15)
        WORLD_STATE["prosperity_level"] = min(100, WORLD_STATE["prosperity_level"] + 10)
        
        # Close event
        await db.world_events.update_one(
            {"boss_id": instance_id},
            {"$set": {"status": "resolved", "resolution": {"type": "defeated", "by": attacker_id}}}
        )
    
    await db.boss_instances.update_one(
        {"instance_id": instance_id},
        {"$set": update_data}
    )
    
    return {
        "damage_dealt": damage,
        "boss_health": new_health,
        "boss_max_health": boss["max_health"],
        "status": update_data.get("status", "alive"),
        "dialogue": response_dialogue,
        "your_total_damage": damage_dealt[attacker_id]
    }

async def distribute_boss_loot(db, boss_instance, boss_data):
    """Distribute loot to players who participated"""
    damage_dealt = boss_instance.get("damage_dealt_by", {})
    total_damage = sum(damage_dealt.values())
    
    if total_damage == 0:
        return
    
    loot = boss_data.get("loot", {})
    
    for player_id, player_damage in damage_dealt.items():
        # Calculate share based on damage contribution
        share = player_damage / total_damage
        
        player_loot = {}
        for item, amount in loot.items():
            player_amount = int(amount * share)
            if player_amount > 0:
                player_loot[item] = player_amount
        
        # Add to player inventory
        if player_loot:
            await db.user_profiles.update_one(
                {"id": player_id},
                {
                    "$inc": {f"resources.{k}": v for k, v in player_loot.items() if k in ["gold", "essence", "artifacts"]},
                    "$inc": {f"materials.{k}": v for k, v in player_loot.items() if k in ["obsidian", "crystal", "iron"]}
                }
            )
            
            # Record loot
            await db.loot_drops.insert_one({
                "drop_id": str(uuid.uuid4()),
                "boss_instance_id": boss_instance["instance_id"],
                "player_id": player_id,
                "loot": player_loot,
                "damage_share": share,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

@world_engine_router.post("/negotiate-boss/{instance_id}")
async def negotiate_with_boss(instance_id: str, negotiator_id: str, offer: Dict[str, Any]):
    """Attempt to negotiate with a diplomatic boss"""
    db = get_db()
    
    boss = await db.boss_instances.find_one({"instance_id": instance_id})
    if not boss:
        raise HTTPException(status_code=404, detail="Boss not found")
    
    boss_data = WORLD_BOSSES[boss["boss_key"]]
    
    if not boss_data.get("can_negotiate"):
        return {
            "negotiation_possible": False,
            "dialogue": f"{boss_data['name']} cannot be reasoned with. Only steel will decide this.",
            "boss_response": "hostile"
        }
    
    # Check if offer meets demands
    demands = boss_data.get("negotiation_demands", [])
    offer_items = list(offer.keys())
    
    demands_met = sum(1 for d in demands if d in offer_items)
    
    if demands_met >= len(demands) * 0.5:  # Need to meet at least half
        # Negotiation successful
        await db.boss_instances.update_one(
            {"instance_id": instance_id},
            {"$set": {
                "status": "negotiated",
                "negotiation_terms": offer,
                "negotiated_with": negotiator_id,
                "negotiated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Close event
        await db.world_events.update_one(
            {"boss_id": instance_id},
            {"$set": {"status": "resolved", "resolution": {"type": "negotiated", "by": negotiator_id, "terms": offer}}}
        )
        
        return {
            "negotiation_possible": True,
            "negotiation_success": True,
            "dialogue": f"{boss_data['name']} considers your offer... 'Very well, mortal. We have a bargain. But know this - I will remember.'",
            "boss_response": "agreement",
            "terms_accepted": offer
        }
    else:
        return {
            "negotiation_possible": True,
            "negotiation_success": False,
            "dialogue": f"{boss_data['name']} laughs. 'You think such meager offerings will sway me? Bring me {', '.join(demands)} or face my wrath!'",
            "boss_response": "rejection",
            "demands": demands
        }

@world_engine_router.post("/create-event")
async def create_world_event(
    event_type: EventType,
    severity: EventSeverity,
    location_ids: List[str],
    custom_title: Optional[str] = None,
    custom_description: Optional[str] = None,
    duration_minutes: int = 60,
    triggered_by: Optional[str] = None
):
    """Create a dynamic world event"""
    db = get_db()
    
    template = EVENT_TEMPLATES.get(event_type.value, {})
    
    title = custom_title or template.get("title", f"{event_type.value} Event")
    description = custom_description or template.get("description", "A mysterious event unfolds...")
    
    ends_at = datetime.now(timezone.utc)
    from datetime import timedelta
    ends_at = (ends_at + timedelta(minutes=duration_minutes)).isoformat()
    
    event = WorldEvent(
        event_type=event_type,
        severity=severity,
        title=title,
        description=description,
        location_ids=location_ids,
        ends_at=ends_at
    )
    
    await db.world_events.insert_one(event.dict())
    
    # Adjust world state based on event type
    if event_type == EventType.INVASION:
        WORLD_STATE["danger_level"] = min(100, WORLD_STATE["danger_level"] + 15)
        WORLD_STATE["chaos_level"] = min(100, WORLD_STATE["chaos_level"] + 10)
    elif event_type == EventType.FESTIVAL:
        WORLD_STATE["prosperity_level"] = min(100, WORLD_STATE["prosperity_level"] + 10)
        WORLD_STATE["chaos_level"] = max(0, WORLD_STATE["chaos_level"] - 5)
    elif event_type == EventType.PLAGUE:
        WORLD_STATE["prosperity_level"] = max(0, WORLD_STATE["prosperity_level"] - 20)
    
    return {
        "event_created": True,
        "event": event.dict(),
        "world_state": {
            "chaos_level": WORLD_STATE["chaos_level"],
            "prosperity_level": WORLD_STATE["prosperity_level"],
            "danger_level": WORLD_STATE["danger_level"]
        }
    }

@world_engine_router.post("/diplomatic-action")
async def perform_diplomatic_action(action: DiplomaticAction):
    """Perform a diplomatic action with a faction"""
    db = get_db()
    
    if action.target_faction not in FACTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown faction: {action.target_faction}")
    
    faction = FACTIONS[action.target_faction]
    
    # Get or create faction state
    faction_state = await db.faction_states.find_one({"faction_id": action.target_faction})
    if not faction_state:
        faction_state = {
            "faction_id": action.target_faction,
            **faction,
            "player_relations": {}
        }
        await db.faction_states.insert_one(faction_state)
    
    player_relation = faction_state.get("player_relations", {}).get(action.user_id, 0)
    
    result = {"action": action.action_type, "faction": action.target_faction}
    
    if action.action_type == "negotiate":
        # Attempt negotiation
        success_chance = 0.5 + (player_relation / 200)  # Higher relation = better chance
        success = random.random() < success_chance
        
        if success:
            relation_change = random.randint(10, 25)
            result["success"] = True
            result["message"] = f"{faction['leader']} nods approvingly. 'Perhaps we can work together.'"
            result["relation_change"] = relation_change
        else:
            relation_change = random.randint(-15, -5)
            result["success"] = False
            result["message"] = f"{faction['leader']} frowns. 'Your proposal lacks merit.'"
            result["relation_change"] = relation_change
    
    elif action.action_type == "offer_alliance":
        if player_relation >= 50:
            result["success"] = True
            result["message"] = f"{faction['leader']} extends a hand. 'The {faction['name']} welcomes this alliance.'"
            result["relation_change"] = 30
            result["alliance_formed"] = True
        else:
            result["success"] = False
            result["message"] = f"{faction['leader']} laughs. 'You have not earned our trust yet.'"
            result["relation_change"] = 0
    
    elif action.action_type == "declare_war":
        result["success"] = True
        result["message"] = f"War declared! {faction['leader']} responds: 'So be it. The {faction['name']} will crush you.'"
        result["relation_change"] = -100
        result["war_declared"] = True
        
        # Create war event
        await create_world_event(
            event_type=EventType.WAR_DECLARATION,
            severity=EventSeverity.MAJOR,
            location_ids=["village_square"],
            custom_title=f"War with {faction['name']}!",
            custom_description=f"Player {action.user_id} has declared war on the {faction['name']}!",
            duration_minutes=1440
        )
    
    elif action.action_type == "gift":
        gift_value = action.terms.get("value", 0) if action.terms else 0
        relation_change = gift_value // 10
        result["success"] = True
        result["message"] = f"{faction['leader']} accepts your gift. 'Your generosity is noted.'"
        result["relation_change"] = relation_change
    
    # Update relation
    if "relation_change" in result:
        new_relation = player_relation + result["relation_change"]
        await db.faction_states.update_one(
            {"faction_id": action.target_faction},
            {"$set": {f"player_relations.{action.user_id}": new_relation}}
        )
        result["new_relation"] = new_relation
    
    # Record diplomatic action
    await db.diplomatic_actions.insert_one({
        "action_id": str(uuid.uuid4()),
        **action.dict(),
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return result

@world_engine_router.post("/ai-action")
async def execute_ai_action(action: AIWorldAction):
    """Execute an action by an AI (NPC, villager, or boss)"""
    db = get_db()
    
    result = {"executed": False, "effects": []}
    
    if action.action_type == "spawn_event":
        # AI triggers a world event
        event_type = action.parameters.get("event_type", "mysterious_stranger")
        location = action.parameters.get("location", "village_square")
        
        await create_world_event(
            event_type=EventType(event_type) if event_type in [e.value for e in EventType] else EventType.MYSTERIOUS_STRANGER,
            severity=EventSeverity.MINOR,
            location_ids=[location],
            triggered_by=action.actor_id
        )
        
        result["executed"] = True
        result["effects"].append(f"Event '{event_type}' created at {location}")
    
    elif action.action_type == "modify_prices":
        # AI adjusts market prices
        location = action.parameters.get("location")
        modifier = action.parameters.get("modifier", 1.0)
        
        await db.market_modifiers.update_one(
            {"location_id": location},
            {"$set": {"price_modifier": modifier, "set_by": action.actor_id}},
            upsert=True
        )
        
        result["executed"] = True
        result["effects"].append(f"Prices at {location} modified by {modifier}x")
    
    elif action.action_type == "spread_rumor":
        # AI spreads information
        rumor = action.parameters.get("rumor", "Strange things are afoot...")
        
        await db.world_rumors.insert_one({
            "rumor_id": str(uuid.uuid4()),
            "content": rumor,
            "source": action.actor_id,
            "source_type": action.actor_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "spread_count": 0
        })
        
        result["executed"] = True
        result["effects"].append(f"Rumor spread: '{rumor[:50]}...'")
    
    elif action.action_type == "change_mood":
        # AI changes its mood based on context
        new_mood = action.parameters.get("mood", "neutral")
        
        if action.actor_type == "villager":
            await db.ai_villagers.update_one(
                {"villager_id": action.actor_id},
                {"$set": {"mood": new_mood}}
            )
        
        result["executed"] = True
        result["effects"].append(f"Mood changed to {new_mood}")
    
    elif action.action_type == "request_help":
        # AI requests player help (creates quest)
        quest_title = action.parameters.get("title", "A Villager Needs Help")
        quest_desc = action.parameters.get("description", "Someone needs assistance.")
        
        await db.quests.insert_one({
            "id": str(uuid.uuid4()),
            "title": quest_title,
            "description": quest_desc,
            "creator_id": action.actor_id,
            "creator_type": action.actor_type,
            "location_id": action.parameters.get("location", "village_square"),
            "rewards": action.parameters.get("rewards", {"gold": 50, "xp": 25}),
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        result["executed"] = True
        result["effects"].append(f"Quest created: '{quest_title}'")
    
    # Record action
    action.executed = result["executed"]
    action.result = result
    await db.ai_world_actions.insert_one(action.dict())
    
    return result

@world_engine_router.get("/bosses")
async def list_bosses():
    """List all possible world bosses"""
    return {"bosses": WORLD_BOSSES}

@world_engine_router.get("/factions")
async def list_factions():
    """List all factions"""
    db = get_db()
    
    # Get faction states with player relations
    faction_states = await db.faction_states.find({}, {"_id": 0}).to_list(20)
    
    if not faction_states:
        return {"factions": FACTIONS}
    
    return {"factions": {f["faction_id"]: f for f in faction_states}}

@world_engine_router.get("/events/active")
async def get_active_events():
    """Get all currently active events"""
    db = get_db()
    
    events = await db.world_events.find(
        {"status": "active"},
        {"_id": 0}
    ).sort("started_at", -1).to_list(50)
    
    return {"events": events, "count": len(events)}

@world_engine_router.post("/trigger-random-event")
async def trigger_random_event(location_id: Optional[str] = None):
    """Trigger a random world event (for AI/system use)"""
    
    event_types = list(EventType)
    weights = [
        10,  # BOSS_SPAWN - rare
        15,  # INVASION
        20,  # DIPLOMATIC_CRISIS
        25,  # RESOURCE_DISCOVERY
        10,  # PLAGUE
        30,  # FESTIVAL
        35,  # MERCHANT_CARAVAN
        15,  # NATURAL_DISASTER
        20,  # PROPHECY
        10,  # REBELLION
        25,  # ALLIANCE_OFFER
        5,   # WAR_DECLARATION - very rare
        30,  # MYSTERIOUS_STRANGER
        20,  # ARTIFACT_APPEARANCE
        10,  # PORTAL_OPENING
    ]
    
    chosen_event = random.choices(event_types, weights=weights, k=1)[0]
    
    locations = ["village_square", "oracle_sanctum", "the_forge", "ancient_library", 
                 "wanderers_rest", "shadow_grove", "watchtower"]
    
    target_location = location_id or random.choice(locations)
    
    severity = random.choices(
        [EventSeverity.MINOR, EventSeverity.MODERATE, EventSeverity.MAJOR],
        weights=[50, 35, 15],
        k=1
    )[0]
    
    return await create_world_event(
        event_type=chosen_event,
        severity=severity,
        location_ids=[target_location],
        duration_minutes=random.randint(30, 180)
    )
