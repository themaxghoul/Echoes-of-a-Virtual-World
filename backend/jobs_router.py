# Job & Career System - Player-AI Symbiotic Economy
# Creates viable job paths that benefit both humans and AI

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import random
import logging

jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])

logger = logging.getLogger(__name__)

# ============ Job Definitions ============

class JobCategory(str, Enum):
    TASK_WORK = "task_work"        # VE$ earning through micro-tasks
    DATA_TRAINING = "data_training"  # Training AI through interactions
    COMMERCE = "commerce"          # Trading, merchant activities
    CONSTRUCTION = "construction"  # Building in 2D world
    EXPLORATION = "exploration"    # Discovering, resource gathering
    DIPLOMACY = "diplomacy"        # Faction relations
    SCHOLARSHIP = "scholarship"    # Teaching AI, knowledge work
    COMBAT = "combat"              # Fighting demons, protection
    CRAFTING = "crafting"          # Creating items
    MYSTICISM = "mysticism"        # Oracle work, prophecies

# Complete job definitions with progression
JOBS = {
    # ============ TASK WORK JOBS ============
    "data_labeler": {
        "id": "data_labeler",
        "name": "Data Labeler",
        "category": JobCategory.TASK_WORK,
        "description": "Label and categorize data to train AI systems. Your work directly improves AI intelligence.",
        "base_hourly_ve": 6.0,
        "ecosystem_points_per_hour": 10,
        "ai_benefit": "Improves AI pattern recognition and classification",
        "requirements": {"level": 1},
        "skills_gained": ["pattern_recognition", "attention_to_detail"],
        "progression": {
            1: {"title": "Trainee Labeler", "hourly_ve": 6.0, "tasks_required": 0},
            2: {"title": "Junior Labeler", "hourly_ve": 7.0, "tasks_required": 50},
            3: {"title": "Labeler", "hourly_ve": 8.0, "tasks_required": 200},
            4: {"title": "Senior Labeler", "hourly_ve": 10.0, "tasks_required": 500},
            5: {"title": "Master Labeler", "hourly_ve": 12.0, "tasks_required": 1000}
        }
    },
    "transcriber": {
        "id": "transcriber",
        "name": "Transcriber",
        "category": JobCategory.TASK_WORK,
        "description": "Convert audio and images to text. Your transcriptions help AI understand human language better.",
        "base_hourly_ve": 8.0,
        "ecosystem_points_per_hour": 12,
        "ai_benefit": "Improves AI language understanding and speech recognition",
        "requirements": {"level": 1, "skill": "language_proficiency"},
        "skills_gained": ["listening", "typing_speed", "language_mastery"],
        "progression": {
            1: {"title": "Novice Transcriber", "hourly_ve": 8.0, "tasks_required": 0},
            2: {"title": "Transcriber", "hourly_ve": 10.0, "tasks_required": 30},
            3: {"title": "Expert Transcriber", "hourly_ve": 12.0, "tasks_required": 100},
            4: {"title": "Master Transcriber", "hourly_ve": 15.0, "tasks_required": 300}
        }
    },
    "survey_taker": {
        "id": "survey_taker",
        "name": "Survey Specialist",
        "category": JobCategory.TASK_WORK,
        "description": "Complete market research surveys. Your opinions shape AI understanding of human preferences.",
        "base_hourly_ve": 5.0,
        "ecosystem_points_per_hour": 8,
        "ai_benefit": "Helps AI understand human preferences and opinions",
        "requirements": {"level": 1},
        "skills_gained": ["critical_thinking", "self_awareness"],
        "progression": {
            1: {"title": "Survey Taker", "hourly_ve": 5.0, "tasks_required": 0},
            2: {"title": "Survey Specialist", "hourly_ve": 7.0, "tasks_required": 100},
            3: {"title": "Research Contributor", "hourly_ve": 10.0, "tasks_required": 500}
        }
    },
    
    # ============ DATA TRAINING JOBS ============
    "ai_trainer": {
        "id": "ai_trainer",
        "name": "AI Trainer",
        "category": JobCategory.DATA_TRAINING,
        "description": "Directly interact with and train AI villagers. Your conversations become their learning material.",
        "base_hourly_ve": 10.0,
        "ecosystem_points_per_hour": 25,
        "ai_benefit": "Direct AI personality and knowledge development",
        "requirements": {"level": 5, "conversations": 50},
        "skills_gained": ["teaching", "patience", "communication"],
        "progression": {
            1: {"title": "AI Tutor", "hourly_ve": 10.0, "sessions_required": 0},
            2: {"title": "AI Mentor", "hourly_ve": 12.0, "sessions_required": 20},
            3: {"title": "AI Instructor", "hourly_ve": 15.0, "sessions_required": 50},
            4: {"title": "AI Professor", "hourly_ve": 20.0, "sessions_required": 100},
            5: {"title": "AI Sage", "hourly_ve": 25.0, "sessions_required": 200}
        },
        "special_tasks": [
            {"name": "Teach New Concept", "ve_reward": 5.0, "eco_points": 50},
            {"name": "Correct AI Behavior", "ve_reward": 3.0, "eco_points": 30},
            {"name": "Emotional Calibration", "ve_reward": 8.0, "eco_points": 80}
        ]
    },
    "feedback_analyst": {
        "id": "feedback_analyst",
        "name": "Feedback Analyst",
        "category": JobCategory.DATA_TRAINING,
        "description": "Evaluate AI responses and provide quality feedback. Your assessments improve AI accuracy.",
        "base_hourly_ve": 8.0,
        "ecosystem_points_per_hour": 20,
        "ai_benefit": "Improves AI response quality and accuracy",
        "requirements": {"level": 3},
        "skills_gained": ["analysis", "evaluation", "quality_assurance"],
        "progression": {
            1: {"title": "Junior Analyst", "hourly_ve": 8.0, "reviews_required": 0},
            2: {"title": "Analyst", "hourly_ve": 10.0, "reviews_required": 50},
            3: {"title": "Senior Analyst", "hourly_ve": 13.0, "reviews_required": 150},
            4: {"title": "Lead Analyst", "hourly_ve": 18.0, "reviews_required": 400}
        }
    },
    
    # ============ COMMERCE JOBS ============
    "merchant": {
        "id": "merchant",
        "name": "Merchant",
        "category": JobCategory.COMMERCE,
        "description": "Trade goods between players and NPCs. Your market activity teaches AI economics.",
        "base_hourly_ve": 0,  # Commission-based
        "ecosystem_points_per_hour": 5,
        "ai_benefit": "AI learns economic patterns and pricing strategies",
        "requirements": {"level": 2, "gold": 100},
        "skills_gained": ["negotiation", "market_analysis", "inventory_management"],
        "commission_rate": 0.05,  # 5% of trades
        "progression": {
            1: {"title": "Peddler", "commission": 0.05, "trades_required": 0},
            2: {"title": "Trader", "commission": 0.07, "trades_required": 20},
            3: {"title": "Merchant", "commission": 0.10, "trades_required": 100},
            4: {"title": "Master Merchant", "commission": 0.12, "trades_required": 500},
            5: {"title": "Trade Baron", "commission": 0.15, "trades_required": 2000}
        }
    },
    "broker": {
        "id": "broker",
        "name": "Resource Broker",
        "category": JobCategory.COMMERCE,
        "description": "Facilitate large trades and manage market prices. Shape the village economy.",
        "base_hourly_ve": 0,
        "ecosystem_points_per_hour": 15,
        "ai_benefit": "AI learns market dynamics and resource valuation",
        "requirements": {"level": 10, "merchant_level": 3},
        "skills_gained": ["economics", "risk_management", "forecasting"],
        "progression": {
            1: {"title": "Junior Broker", "fee_rate": 0.02, "volume_required": 0},
            2: {"title": "Broker", "fee_rate": 0.03, "volume_required": 10000},
            3: {"title": "Senior Broker", "fee_rate": 0.04, "volume_required": 50000}
        }
    },
    
    # ============ CONSTRUCTION JOBS ============
    "builder": {
        "id": "builder",
        "name": "Builder",
        "category": JobCategory.CONSTRUCTION,
        "description": "Construct buildings and structures in the 2D world. Your creations become part of the village.",
        "base_hourly_ve": 5.0,
        "ecosystem_points_per_hour": 15,
        "ai_benefit": "AI learns architecture and spatial planning",
        "requirements": {"level": 3},
        "skills_gained": ["construction", "planning", "resource_efficiency"],
        "progression": {
            1: {"title": "Apprentice Builder", "hourly_ve": 5.0, "structures_required": 0},
            2: {"title": "Builder", "hourly_ve": 7.0, "structures_required": 5},
            3: {"title": "Master Builder", "hourly_ve": 10.0, "structures_required": 20},
            4: {"title": "Architect", "hourly_ve": 15.0, "structures_required": 50},
            5: {"title": "Grand Architect", "hourly_ve": 20.0, "structures_required": 100}
        },
        "buildable_structures": [
            {"name": "Small House", "cost": {"wood": 50, "stone": 20}, "eco_points": 20},
            {"name": "Shop", "cost": {"wood": 80, "stone": 40, "iron": 10}, "eco_points": 40},
            {"name": "Workshop", "cost": {"wood": 100, "stone": 60, "iron": 30}, "eco_points": 60},
            {"name": "Tower", "cost": {"stone": 200, "iron": 50, "crystal": 10}, "eco_points": 100},
            {"name": "Monument", "cost": {"obsidian": 50, "crystal": 30}, "eco_points": 200}
        ]
    },
    "infrastructure_engineer": {
        "id": "infrastructure_engineer",
        "name": "Infrastructure Engineer",
        "category": JobCategory.CONSTRUCTION,
        "description": "Build roads, bridges, and utilities that connect the village.",
        "base_hourly_ve": 8.0,
        "ecosystem_points_per_hour": 20,
        "ai_benefit": "AI learns infrastructure planning and logistics",
        "requirements": {"level": 8, "builder_level": 3},
        "skills_gained": ["engineering", "logistics", "urban_planning"],
        "progression": {
            1: {"title": "Road Worker", "hourly_ve": 8.0, "projects_required": 0},
            2: {"title": "Engineer", "hourly_ve": 12.0, "projects_required": 10},
            3: {"title": "Chief Engineer", "hourly_ve": 18.0, "projects_required": 30}
        }
    },
    
    # ============ EXPLORATION JOBS ============
    "explorer": {
        "id": "explorer",
        "name": "Explorer",
        "category": JobCategory.EXPLORATION,
        "description": "Discover new lands and gather rare resources. Your discoveries expand the world.",
        "base_hourly_ve": 4.0,
        "ecosystem_points_per_hour": 15,
        "ai_benefit": "AI expands world knowledge and geography",
        "requirements": {"level": 2},
        "skills_gained": ["navigation", "survival", "observation"],
        "progression": {
            1: {"title": "Scout", "hourly_ve": 4.0, "discoveries_required": 0},
            2: {"title": "Explorer", "hourly_ve": 6.0, "discoveries_required": 5},
            3: {"title": "Pathfinder", "hourly_ve": 8.0, "discoveries_required": 15},
            4: {"title": "Cartographer", "hourly_ve": 12.0, "discoveries_required": 30},
            5: {"title": "World Walker", "hourly_ve": 15.0, "discoveries_required": 50}
        },
        "discovery_rewards": {
            "new_location": {"ve": 10.0, "eco_points": 100},
            "rare_resource": {"ve": 5.0, "eco_points": 50},
            "hidden_path": {"ve": 3.0, "eco_points": 30},
            "ancient_ruin": {"ve": 20.0, "eco_points": 200}
        }
    },
    "resource_gatherer": {
        "id": "resource_gatherer",
        "name": "Resource Gatherer",
        "category": JobCategory.EXPLORATION,
        "description": "Collect materials from the world. Fuel the village's growth.",
        "base_hourly_ve": 3.0,
        "ecosystem_points_per_hour": 8,
        "ai_benefit": "AI learns resource locations and regeneration patterns",
        "requirements": {"level": 1},
        "skills_gained": ["gathering", "efficiency", "endurance"],
        "progression": {
            1: {"title": "Gatherer", "hourly_ve": 3.0, "resources_required": 0},
            2: {"title": "Forager", "hourly_ve": 4.0, "resources_required": 100},
            3: {"title": "Harvester", "hourly_ve": 6.0, "resources_required": 500},
            4: {"title": "Master Gatherer", "hourly_ve": 8.0, "resources_required": 2000}
        }
    },
    
    # ============ DIPLOMACY JOBS ============
    "diplomat": {
        "id": "diplomat",
        "name": "Diplomat",
        "category": JobCategory.DIPLOMACY,
        "description": "Negotiate with factions and resolve conflicts. Your diplomacy shapes alliances.",
        "base_hourly_ve": 8.0,
        "ecosystem_points_per_hour": 20,
        "ai_benefit": "AI learns negotiation and conflict resolution",
        "requirements": {"level": 5, "faction_standing": 100},
        "skills_gained": ["negotiation", "persuasion", "cultural_understanding"],
        "progression": {
            1: {"title": "Envoy", "hourly_ve": 8.0, "negotiations_required": 0},
            2: {"title": "Diplomat", "hourly_ve": 12.0, "negotiations_required": 10},
            3: {"title": "Ambassador", "hourly_ve": 18.0, "negotiations_required": 30},
            4: {"title": "High Ambassador", "hourly_ve": 25.0, "negotiations_required": 75}
        },
        "diplomatic_missions": [
            {"name": "Peace Treaty", "ve_reward": 50.0, "eco_points": 500},
            {"name": "Trade Agreement", "ve_reward": 30.0, "eco_points": 300},
            {"name": "Alliance Formation", "ve_reward": 100.0, "eco_points": 1000},
            {"name": "Conflict Resolution", "ve_reward": 40.0, "eco_points": 400}
        ]
    },
    "faction_liaison": {
        "id": "faction_liaison",
        "name": "Faction Liaison",
        "category": JobCategory.DIPLOMACY,
        "description": "Represent a faction and manage inter-faction relations.",
        "base_hourly_ve": 10.0,
        "ecosystem_points_per_hour": 25,
        "ai_benefit": "AI learns organizational dynamics and loyalty systems",
        "requirements": {"level": 8, "diplomat_level": 2},
        "skills_gained": ["leadership", "faction_management", "political_acumen"],
        "progression": {
            1: {"title": "Liaison", "hourly_ve": 10.0, "missions_required": 0},
            2: {"title": "Senior Liaison", "hourly_ve": 15.0, "missions_required": 15},
            3: {"title": "Faction Voice", "hourly_ve": 22.0, "missions_required": 40}
        }
    },
    
    # ============ SCHOLARSHIP JOBS ============
    "scholar": {
        "id": "scholar",
        "name": "Scholar",
        "category": JobCategory.SCHOLARSHIP,
        "description": "Research lore and contribute knowledge to the world. Your writings educate AI.",
        "base_hourly_ve": 7.0,
        "ecosystem_points_per_hour": 30,
        "ai_benefit": "Direct knowledge injection into AI memory systems",
        "requirements": {"level": 4, "knowledge_entries": 10},
        "skills_gained": ["research", "writing", "critical_analysis"],
        "progression": {
            1: {"title": "Student", "hourly_ve": 7.0, "articles_required": 0},
            2: {"title": "Scholar", "hourly_ve": 10.0, "articles_required": 10},
            3: {"title": "Researcher", "hourly_ve": 14.0, "articles_required": 30},
            4: {"title": "Professor", "hourly_ve": 20.0, "articles_required": 75},
            5: {"title": "Sage", "hourly_ve": 30.0, "articles_required": 150}
        },
        "research_topics": [
            {"name": "Village History", "ve_reward": 10.0, "eco_points": 100},
            {"name": "Demon Lore", "ve_reward": 15.0, "eco_points": 150},
            {"name": "Magic Theory", "ve_reward": 20.0, "eco_points": 200},
            {"name": "Economic Analysis", "ve_reward": 12.0, "eco_points": 120}
        ]
    },
    "lorekeeper": {
        "id": "lorekeeper",
        "name": "Lorekeeper",
        "category": JobCategory.SCHOLARSHIP,
        "description": "Preserve and organize world knowledge. Maintain the collective memory.",
        "base_hourly_ve": 12.0,
        "ecosystem_points_per_hour": 35,
        "ai_benefit": "Maintains AI knowledge consistency and depth",
        "requirements": {"level": 10, "scholar_level": 3},
        "skills_gained": ["archival", "organization", "wisdom"],
        "progression": {
            1: {"title": "Archivist", "hourly_ve": 12.0, "entries_required": 0},
            2: {"title": "Lorekeeper", "hourly_ve": 18.0, "entries_required": 50},
            3: {"title": "Grand Lorekeeper", "hourly_ve": 25.0, "entries_required": 150}
        }
    },
    
    # ============ COMBAT JOBS ============
    "guardian": {
        "id": "guardian",
        "name": "Guardian",
        "category": JobCategory.COMBAT,
        "description": "Protect the village from demons and threats. Your valor keeps the peace.",
        "base_hourly_ve": 6.0,
        "ecosystem_points_per_hour": 12,
        "ai_benefit": "AI learns combat strategies and threat assessment",
        "requirements": {"level": 3, "strength": 15},
        "skills_gained": ["combat", "defense", "vigilance"],
        "progression": {
            1: {"title": "Militia", "hourly_ve": 6.0, "demons_defeated": 0},
            2: {"title": "Guard", "hourly_ve": 8.0, "demons_defeated": 10},
            3: {"title": "Warrior", "hourly_ve": 12.0, "demons_defeated": 50},
            4: {"title": "Champion", "hourly_ve": 18.0, "demons_defeated": 150},
            5: {"title": "Hero", "hourly_ve": 25.0, "demons_defeated": 500}
        },
        "bounties": [
            {"target": "Lesser Demon", "ve_reward": 5.0, "eco_points": 25},
            {"target": "Demon", "ve_reward": 10.0, "eco_points": 50},
            {"target": "Greater Demon", "ve_reward": 25.0, "eco_points": 125},
            {"target": "Demon Lord", "ve_reward": 100.0, "eco_points": 500}
        ]
    },
    "demon_hunter": {
        "id": "demon_hunter",
        "name": "Demon Hunter",
        "category": JobCategory.COMBAT,
        "description": "Specialized in tracking and eliminating demonic threats.",
        "base_hourly_ve": 10.0,
        "ecosystem_points_per_hour": 18,
        "ai_benefit": "AI learns advanced combat tactics and demon behavior",
        "requirements": {"level": 8, "guardian_level": 3, "demons_defeated": 25},
        "skills_gained": ["tracking", "demon_lore", "elite_combat"],
        "progression": {
            1: {"title": "Hunter", "hourly_ve": 10.0, "hunts_required": 0},
            2: {"title": "Slayer", "hourly_ve": 15.0, "hunts_required": 20},
            3: {"title": "Vanquisher", "hourly_ve": 22.0, "hunts_required": 60},
            4: {"title": "Legendary Hunter", "hourly_ve": 35.0, "hunts_required": 150}
        }
    },
    
    # ============ CRAFTING JOBS ============
    "crafter": {
        "id": "crafter",
        "name": "Crafter",
        "category": JobCategory.CRAFTING,
        "description": "Create items and equipment. Your crafts support the village economy.",
        "base_hourly_ve": 5.0,
        "ecosystem_points_per_hour": 10,
        "ai_benefit": "AI learns crafting recipes and material properties",
        "requirements": {"level": 2},
        "skills_gained": ["crafting", "material_knowledge", "precision"],
        "progression": {
            1: {"title": "Apprentice Crafter", "hourly_ve": 5.0, "items_crafted": 0},
            2: {"title": "Crafter", "hourly_ve": 7.0, "items_crafted": 20},
            3: {"title": "Artisan", "hourly_ve": 10.0, "items_crafted": 100},
            4: {"title": "Master Artisan", "hourly_ve": 15.0, "items_crafted": 300},
            5: {"title": "Legendary Crafter", "hourly_ve": 22.0, "items_crafted": 1000}
        }
    },
    "enchanter": {
        "id": "enchanter",
        "name": "Enchanter",
        "category": JobCategory.CRAFTING,
        "description": "Imbue items with magical properties. Create powerful artifacts.",
        "base_hourly_ve": 12.0,
        "ecosystem_points_per_hour": 25,
        "ai_benefit": "AI learns magical theory and enchantment patterns",
        "requirements": {"level": 10, "crafter_level": 3, "intelligence": 20},
        "skills_gained": ["enchanting", "magic_theory", "essence_manipulation"],
        "progression": {
            1: {"title": "Apprentice Enchanter", "hourly_ve": 12.0, "enchants_required": 0},
            2: {"title": "Enchanter", "hourly_ve": 18.0, "enchants_required": 25},
            3: {"title": "Master Enchanter", "hourly_ve": 28.0, "enchants_required": 100}
        }
    },
    
    # ============ MYSTICISM JOBS ============
    "oracle_apprentice": {
        "id": "oracle_apprentice",
        "name": "Oracle Apprentice",
        "category": JobCategory.MYSTICISM,
        "description": "Learn the ways of prophecy. Channel visions and guide others.",
        "base_hourly_ve": 8.0,
        "ecosystem_points_per_hour": 40,
        "ai_benefit": "AI learns predictive modeling and intuition patterns",
        "requirements": {"level": 5, "wisdom": 18, "oracle_conversations": 20},
        "skills_gained": ["divination", "intuition", "guidance"],
        "progression": {
            1: {"title": "Initiate", "hourly_ve": 8.0, "visions_required": 0},
            2: {"title": "Seer", "hourly_ve": 12.0, "visions_required": 10},
            3: {"title": "Prophet", "hourly_ve": 20.0, "visions_required": 30},
            4: {"title": "Oracle", "hourly_ve": 35.0, "visions_required": 100}
        },
        "mystical_services": [
            {"name": "Personal Reading", "ve_reward": 5.0, "eco_points": 25},
            {"name": "Village Prophecy", "ve_reward": 15.0, "eco_points": 150},
            {"name": "Danger Warning", "ve_reward": 10.0, "eco_points": 100},
            {"name": "Lost Item Location", "ve_reward": 8.0, "eco_points": 40}
        ]
    },
    "ritual_master": {
        "id": "ritual_master",
        "name": "Ritual Master",
        "category": JobCategory.MYSTICISM,
        "description": "Perform powerful rituals that affect the world state.",
        "base_hourly_ve": 15.0,
        "ecosystem_points_per_hour": 50,
        "ai_benefit": "AI learns ritual mechanics and world modification patterns",
        "requirements": {"level": 15, "oracle_apprentice_level": 3},
        "skills_gained": ["ritual_magic", "world_shaping", "spiritual_connection"],
        "progression": {
            1: {"title": "Ritualist", "hourly_ve": 15.0, "rituals_required": 0},
            2: {"title": "High Ritualist", "hourly_ve": 25.0, "rituals_required": 20},
            3: {"title": "Ritual Master", "hourly_ve": 40.0, "rituals_required": 50}
        }
    }
}

# ============ Models ============

class PlayerJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    job_key: str
    current_level: int = 1
    experience: int = 0
    tasks_completed: int = 0
    total_ve_earned: float = 0.0
    total_eco_points: int = 0
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_worked: Optional[str] = None
    skills_learned: List[str] = Field(default_factory=list)
    specializations: List[str] = Field(default_factory=list)

class JobTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_key: str
    player_id: str
    task_type: str
    description: str
    ve_reward: float
    eco_points: int
    status: str = "pending"  # pending, in_progress, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    ai_feedback: Optional[str] = None
    quality_score: float = 1.0

class WorkSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    job_key: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None
    duration_minutes: int = 0
    ve_earned: float = 0.0
    eco_points_earned: int = 0
    tasks_completed: int = 0

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Job Endpoints ============

@jobs_router.get("/catalog")
async def get_job_catalog():
    """Get all available jobs"""
    categorized = {}
    for job_key, job in JOBS.items():
        cat = job["category"].value
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append({
            "key": job_key,
            "name": job["name"],
            "description": job["description"],
            "base_hourly_ve": job["base_hourly_ve"],
            "ecosystem_points_per_hour": job["ecosystem_points_per_hour"],
            "ai_benefit": job["ai_benefit"],
            "requirements": job["requirements"],
            "max_level": max(job["progression"].keys())
        })
    
    return {"jobs": categorized, "total_jobs": len(JOBS)}

@jobs_router.get("/details/{job_key}")
async def get_job_details(job_key: str):
    """Get detailed information about a specific job"""
    if job_key not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"job": JOBS[job_key]}

@jobs_router.post("/enroll")
async def enroll_in_job(player_id: str, job_key: str):
    """Enroll a player in a job"""
    db = get_db()
    
    if job_key not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_key]
    
    # Check requirements
    player = await db.characters.find_one({"user_id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check level requirement
    player_level = player.get("level", 1)
    if player_level < job["requirements"].get("level", 1):
        raise HTTPException(
            status_code=400, 
            detail=f"Requires level {job['requirements']['level']}. You are level {player_level}."
        )
    
    # Check if already enrolled
    existing = await db.player_jobs.find_one({
        "player_id": player_id,
        "job_key": job_key
    })
    
    if existing:
        return {"enrolled": False, "message": "Already enrolled in this job", "job": existing}
    
    # Create job enrollment
    player_job = PlayerJob(
        player_id=player_id,
        job_key=job_key
    )
    
    await db.player_jobs.insert_one(player_job.dict())
    
    # Create memory for this career decision
    await db.memories.insert_one({
        "memory_id": str(uuid.uuid4()),
        "entity_type": "user",
        "entity_id": player_id,
        "memory_type": "user_achievement",
        "importance": "significant",
        "importance_score": 7.0,
        "content": f"Started career as {job['name']}. {job['description']}",
        "structured_data": {"job_key": job_key, "job_name": job["name"]},
        "tags": ["career", "job", job_key],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decay_rate": 0.005,
        "current_strength": 1.0
    })
    
    return {
        "enrolled": True,
        "job": player_job.dict(),
        "first_level_title": job["progression"][1]["title"],
        "message": f"Welcome, {job['progression'][1]['title']}! Your journey as a {job['name']} begins."
    }

@jobs_router.get("/player/{player_id}")
async def get_player_jobs(player_id: str):
    """Get all jobs for a player"""
    db = get_db()
    
    jobs = await db.player_jobs.find(
        {"player_id": player_id},
        {"_id": 0}
    ).to_list(50)
    
    # Enrich with job details
    enriched = []
    for pj in jobs:
        job_def = JOBS.get(pj["job_key"])
        if job_def:
            level = pj["current_level"]
            progression = job_def["progression"].get(level, job_def["progression"][1])
            enriched.append({
                **pj,
                "job_name": job_def["name"],
                "current_title": progression.get("title"),
                "hourly_ve": progression.get("hourly_ve", job_def["base_hourly_ve"]),
                "category": job_def["category"].value
            })
    
    return {"jobs": enriched, "count": len(enriched)}

@jobs_router.post("/start-work-session")
async def start_work_session(player_id: str, job_key: str):
    """Start a work session for a job"""
    db = get_db()
    
    # Verify enrollment
    player_job = await db.player_jobs.find_one({
        "player_id": player_id,
        "job_key": job_key
    })
    
    if not player_job:
        raise HTTPException(status_code=400, detail="Not enrolled in this job")
    
    # Check for active session
    active = await db.work_sessions.find_one({
        "player_id": player_id,
        "ended_at": None
    })
    
    if active:
        return {"started": False, "message": "Already in a work session", "session": active}
    
    # Create session
    session = WorkSession(
        player_id=player_id,
        job_key=job_key
    )
    
    await db.work_sessions.insert_one(session.dict())
    
    job = JOBS[job_key]
    level = player_job["current_level"]
    progression = job["progression"].get(level, job["progression"][1])
    
    return {
        "started": True,
        "session_id": session.session_id,
        "job": job["name"],
        "title": progression.get("title"),
        "hourly_rate": progression.get("hourly_ve", job["base_hourly_ve"]),
        "eco_points_rate": job["ecosystem_points_per_hour"]
    }

@jobs_router.post("/end-work-session/{session_id}")
async def end_work_session(session_id: str):
    """End a work session and calculate earnings"""
    db = get_db()
    
    session = await db.work_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.get("ended_at"):
        return {"ended": False, "message": "Session already ended", "session": session}
    
    # Calculate duration
    start_time = datetime.fromisoformat(session["started_at"].replace('Z', '+00:00'))
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds() / 60  # minutes
    
    # Get job details
    job = JOBS.get(session["job_key"])
    player_job = await db.player_jobs.find_one({
        "player_id": session["player_id"],
        "job_key": session["job_key"]
    })
    
    level = player_job["current_level"] if player_job else 1
    progression = job["progression"].get(level, job["progression"][1])
    hourly_rate = progression.get("hourly_ve", job["base_hourly_ve"])
    eco_rate = job["ecosystem_points_per_hour"]
    
    # Calculate earnings
    hours_worked = duration / 60
    ve_earned = hourly_rate * hours_worked
    eco_points = int(eco_rate * hours_worked)
    
    # Update session
    await db.work_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "ended_at": end_time.isoformat(),
            "duration_minutes": int(duration),
            "ve_earned": ve_earned,
            "eco_points_earned": eco_points
        }}
    )
    
    # Update player job stats
    await db.player_jobs.update_one(
        {"player_id": session["player_id"], "job_key": session["job_key"]},
        {
            "$inc": {
                "total_ve_earned": ve_earned,
                "total_eco_points": eco_points,
                "experience": int(duration)
            },
            "$set": {"last_worked": end_time.isoformat()}
        }
    )
    
    # Credit VE$ to earnings account
    await db.earnings_accounts.update_one(
        {"user_id": session["player_id"]},
        {
            "$inc": {"available_balance_usd": ve_earned, "total_earned_usd": ve_earned},
            "$set": {"updated_at": end_time.isoformat()}
        },
        upsert=True
    )
    
    # Add ecosystem contribution
    await db.ecosystem_contributions.insert_one({
        "contribution_id": str(uuid.uuid4()),
        "user_id": session["player_id"],
        "action_type": "job_work",
        "points": eco_points,
        "details": {
            "job": job["name"],
            "duration_minutes": int(duration),
            "ve_earned": ve_earned
        },
        "ai_benefit": job["ai_benefit"],
        "timestamp": end_time.isoformat()
    })
    
    # Check for level up
    level_up = await check_job_level_up(db, session["player_id"], session["job_key"])
    
    return {
        "ended": True,
        "duration_minutes": int(duration),
        "ve_earned": round(ve_earned, 2),
        "eco_points_earned": eco_points,
        "ai_benefit": job["ai_benefit"],
        "level_up": level_up
    }

async def check_job_level_up(db, player_id: str, job_key: str) -> Optional[Dict]:
    """Check if player qualifies for job level up"""
    player_job = await db.player_jobs.find_one({
        "player_id": player_id,
        "job_key": job_key
    })
    
    if not player_job:
        return None
    
    job = JOBS.get(job_key)
    current_level = player_job["current_level"]
    next_level = current_level + 1
    
    if next_level not in job["progression"]:
        return None  # Max level
    
    next_prog = job["progression"][next_level]
    
    # Check requirements (simplified - based on tasks_completed as proxy)
    tasks_done = player_job.get("tasks_completed", 0)
    tasks_req_key = [k for k in next_prog.keys() if k.endswith("_required")]
    
    if tasks_req_key:
        req_value = next_prog[tasks_req_key[0]]
        # Use experience as proxy
        if player_job.get("experience", 0) >= req_value * 10:  # 10 mins per "task"
            # Level up!
            await db.player_jobs.update_one(
                {"player_id": player_id, "job_key": job_key},
                {"$set": {"current_level": next_level}}
            )
            
            return {
                "leveled_up": True,
                "new_level": next_level,
                "new_title": next_prog.get("title"),
                "new_hourly_ve": next_prog.get("hourly_ve")
            }
    
    return None

@jobs_router.post("/complete-task")
async def complete_job_task(player_id: str, job_key: str, task_type: str, quality_score: float = 1.0):
    """Complete a specific job task"""
    db = get_db()
    
    if job_key not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_key]
    player_job = await db.player_jobs.find_one({
        "player_id": player_id,
        "job_key": job_key
    })
    
    if not player_job:
        raise HTTPException(status_code=400, detail="Not enrolled in this job")
    
    # Find task reward
    special_tasks = job.get("special_tasks", [])
    task_def = next((t for t in special_tasks if t["name"].lower().replace(" ", "_") == task_type.lower()), None)
    
    if task_def:
        ve_reward = task_def["ve_reward"] * quality_score
        eco_points = int(task_def["eco_points"] * quality_score)
    else:
        # Default task
        level = player_job["current_level"]
        progression = job["progression"].get(level, job["progression"][1])
        ve_reward = (progression.get("hourly_ve", job["base_hourly_ve"]) / 6) * quality_score  # ~10 min task
        eco_points = int((job["ecosystem_points_per_hour"] / 6) * quality_score)
    
    # Create task record
    task = JobTask(
        job_key=job_key,
        player_id=player_id,
        task_type=task_type,
        description=f"Completed {task_type} for {job['name']}",
        ve_reward=ve_reward,
        eco_points=eco_points,
        status="completed",
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=datetime.now(timezone.utc).isoformat(),
        quality_score=quality_score
    )
    
    await db.job_tasks.insert_one(task.dict())
    
    # Update job stats
    await db.player_jobs.update_one(
        {"player_id": player_id, "job_key": job_key},
        {
            "$inc": {
                "tasks_completed": 1,
                "total_ve_earned": ve_reward,
                "total_eco_points": eco_points,
                "experience": 10
            },
            "$set": {"last_worked": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Credit earnings
    await db.earnings_accounts.update_one(
        {"user_id": player_id},
        {"$inc": {"available_balance_usd": ve_reward, "total_earned_usd": ve_reward}},
        upsert=True
    )
    
    # Ecosystem contribution
    await db.ecosystem_contributions.insert_one({
        "contribution_id": str(uuid.uuid4()),
        "user_id": player_id,
        "action_type": "task_completion",
        "points": eco_points,
        "details": {"job": job["name"], "task": task_type, "quality": quality_score},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Create AI learning memory if training job
    if job["category"] in [JobCategory.DATA_TRAINING, JobCategory.SCHOLARSHIP]:
        await db.memories.insert_one({
            "memory_id": str(uuid.uuid4()),
            "entity_type": "ecosystem",
            "entity_id": "global",
            "memory_type": "eco_collective",
            "importance": "moderate",
            "importance_score": 5.0,
            "content": f"Player completed {task_type} contributing to AI learning",
            "structured_data": {"job": job_key, "task": task_type, "quality": quality_score},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decay_rate": 0.02,
            "current_strength": 1.0
        })
    
    return {
        "task_completed": True,
        "ve_earned": round(ve_reward, 2),
        "eco_points": eco_points,
        "quality_score": quality_score,
        "ai_benefit": job["ai_benefit"]
    }

@jobs_router.get("/leaderboard/{job_key}")
async def get_job_leaderboard(job_key: str, limit: int = 20):
    """Get leaderboard for a specific job"""
    db = get_db()
    
    if job_key not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    leaderboard = await db.player_jobs.find(
        {"job_key": job_key},
        {"_id": 0, "player_id": 1, "current_level": 1, "total_ve_earned": 1, "total_eco_points": 1, "tasks_completed": 1}
    ).sort("total_eco_points", -1).limit(limit).to_list(limit)
    
    # Enrich with player names
    for entry in leaderboard:
        player = await db.user_profiles.find_one({"id": entry["player_id"]})
        entry["player_name"] = player.get("display_name", "Unknown") if player else "Unknown"
        entry["title"] = JOBS[job_key]["progression"].get(entry["current_level"], {}).get("title", "Unknown")
    
    return {"job": JOBS[job_key]["name"], "leaderboard": leaderboard}

@jobs_router.get("/economy-stats")
async def get_job_economy_stats():
    """Get overall job economy statistics"""
    db = get_db()
    
    # Total by category
    pipeline = [
        {"$group": {
            "_id": None,
            "total_ve_distributed": {"$sum": "$total_ve_earned"},
            "total_eco_points": {"$sum": "$total_eco_points"},
            "total_tasks": {"$sum": "$tasks_completed"},
            "unique_workers": {"$addToSet": "$player_id"}
        }}
    ]
    
    stats = await db.player_jobs.aggregate(pipeline).to_list(1)
    
    if stats:
        stats = stats[0]
        stats["unique_workers"] = len(stats.get("unique_workers", []))
    else:
        stats = {"total_ve_distributed": 0, "total_eco_points": 0, "total_tasks": 0, "unique_workers": 0}
    
    # Jobs by enrollment
    job_enrollments = await db.player_jobs.aggregate([
        {"$group": {"_id": "$job_key", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    popular_jobs = [{"job": JOBS.get(j["_id"], {}).get("name", j["_id"]), "enrollments": j["count"]} for j in job_enrollments]
    
    return {
        "total_ve_distributed": round(stats.get("total_ve_distributed", 0), 2),
        "total_eco_points_generated": stats.get("total_eco_points", 0),
        "total_tasks_completed": stats.get("total_tasks", 0),
        "unique_workers": stats.get("unique_workers", 0),
        "popular_jobs": popular_jobs,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
