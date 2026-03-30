# AI NPC Cloud Gaming System
# Cloud-hosted AI agents with full game emulation and remote controller transfer

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import asyncio
import json

npc_gaming_router = APIRouter(prefix="/npc-gaming", tags=["npc-gaming"])

# ============ CLOUD CONTROLLER MODELS ============

class ControllerState(str, Enum):
    IDLE = "idle"
    LEARNING = "learning"
    PLAYING = "playing"
    TRANSFERRING = "transferring"
    PAUSED = "paused"
    ERROR = "error"

class GamePlatform(str, Enum):
    BROWSER = "browser"
    EMULATOR_NES = "emulator_nes"
    EMULATOR_SNES = "emulator_snes"
    EMULATOR_GBA = "emulator_gba"
    EMULATOR_N64 = "emulator_n64"
    EMULATOR_PS1 = "emulator_ps1"
    CLOUD_STREAM = "cloud_stream"
    AI_VILLAGE = "ai_village"

class InputType(str, Enum):
    BUTTON = "button"
    DPAD = "dpad"
    ANALOG = "analog"
    TOUCH = "touch"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"

class CloudController(BaseModel):
    controller_id: str
    npc_id: str
    npc_name: str
    status: ControllerState = ControllerState.IDLE
    current_game: Optional[str] = None
    current_platform: Optional[GamePlatform] = None
    cloud_instance_id: Optional[str] = None
    learning_model_id: Optional[str] = None
    
    # Controller capabilities
    supported_inputs: List[InputType] = Field(default_factory=list)
    reaction_time_ms: int = 100  # Simulated reaction time
    accuracy_rating: float = 0.85  # 0-1 scale
    
    # Training stats
    games_played: int = 0
    total_playtime_minutes: int = 0
    training_iterations: int = 0
    skill_levels: Dict[str, float] = Field(default_factory=dict)  # {game_id: skill_level}
    
    # Remote transfer
    transfer_history: List[Dict] = Field(default_factory=list)
    can_transfer: bool = True
    
    created_at: str = ""
    updated_at: str = ""

class GameSession(BaseModel):
    session_id: str
    controller_id: str
    npc_id: str
    game_id: str
    platform: GamePlatform
    status: str = "active"
    
    # Game state
    game_state: Dict[str, Any] = Field(default_factory=dict)
    current_score: int = 0
    current_level: int = 1
    objectives_completed: List[str] = Field(default_factory=list)
    
    # Performance metrics
    actions_taken: int = 0
    successful_actions: int = 0
    deaths: int = 0
    
    started_at: str = ""
    ended_at: Optional[str] = None

class TrainingConfig(BaseModel):
    npc_id: str
    game_id: str
    platform: GamePlatform
    training_mode: str = "reinforcement"  # reinforcement, imitation, hybrid
    learning_rate: float = 0.001
    episodes: int = 1000
    reward_function: str = "score_based"
    human_demonstration_data: Optional[str] = None  # Path to demonstration data

class ControllerTransferRequest(BaseModel):
    controller_id: str
    source_game: str
    target_game: str
    target_platform: GamePlatform
    transfer_skills: bool = True  # Transfer learned skills to new game

# ============ SUPPORTED GAMES ============

SUPPORTED_GAMES = {
    # In-game mini-games
    "village_chess": {
        "name": "Village Chess",
        "platform": GamePlatform.AI_VILLAGE,
        "genre": "strategy",
        "complexity": "medium",
        "inputs": [InputType.TOUCH, InputType.MOUSE],
        "description": "Strategic chess against AI or other players"
    },
    "oracle_riddles": {
        "name": "Oracle's Riddles",
        "platform": GamePlatform.AI_VILLAGE,
        "genre": "puzzle",
        "complexity": "easy",
        "inputs": [InputType.TOUCH, InputType.KEYBOARD],
        "description": "Solve riddles to earn wisdom points"
    },
    "forge_rhythm": {
        "name": "Forge Rhythm",
        "platform": GamePlatform.AI_VILLAGE,
        "genre": "rhythm",
        "complexity": "medium",
        "inputs": [InputType.BUTTON, InputType.TOUCH],
        "description": "Rhythm game at the blacksmith's forge"
    },
    "demon_hunter": {
        "name": "Demon Hunter Arena",
        "platform": GamePlatform.AI_VILLAGE,
        "genre": "action",
        "complexity": "hard",
        "inputs": [InputType.DPAD, InputType.BUTTON],
        "description": "Fast-paced demon fighting mini-game"
    },
    
    # Browser games
    "browser_2048": {
        "name": "2048",
        "platform": GamePlatform.BROWSER,
        "genre": "puzzle",
        "complexity": "easy",
        "inputs": [InputType.DPAD, InputType.KEYBOARD],
        "description": "Classic 2048 number puzzle"
    },
    "browser_tetris": {
        "name": "Tetris",
        "platform": GamePlatform.BROWSER,
        "genre": "puzzle",
        "complexity": "medium",
        "inputs": [InputType.DPAD, InputType.BUTTON],
        "description": "Classic block stacking game"
    },
    "browser_snake": {
        "name": "Snake",
        "platform": GamePlatform.BROWSER,
        "genre": "arcade",
        "complexity": "easy",
        "inputs": [InputType.DPAD],
        "description": "Classic snake game"
    },
    
    # Emulated classics
    "emu_mario": {
        "name": "Platform Adventure",
        "platform": GamePlatform.EMULATOR_NES,
        "genre": "platformer",
        "complexity": "medium",
        "inputs": [InputType.DPAD, InputType.BUTTON],
        "description": "Classic side-scrolling platformer"
    },
    "emu_zelda": {
        "name": "Adventure Quest",
        "platform": GamePlatform.EMULATOR_NES,
        "genre": "adventure",
        "complexity": "hard",
        "inputs": [InputType.DPAD, InputType.BUTTON],
        "description": "Top-down adventure exploration"
    },
    "emu_pokemon": {
        "name": "Monster Collector",
        "platform": GamePlatform.EMULATOR_GBA,
        "genre": "rpg",
        "complexity": "medium",
        "inputs": [InputType.DPAD, InputType.BUTTON],
        "description": "Collect and battle creatures"
    },
    "emu_racing": {
        "name": "Kart Racing",
        "platform": GamePlatform.EMULATOR_SNES,
        "genre": "racing",
        "complexity": "medium",
        "inputs": [InputType.DPAD, InputType.BUTTON],
        "description": "Fun kart racing game"
    }
}

# ============ AI LEARNING STRATEGIES ============

LEARNING_STRATEGIES = {
    "reinforcement": {
        "name": "Reinforcement Learning",
        "description": "Learn through trial and error with rewards",
        "best_for": ["action", "arcade", "platformer"],
        "training_time": "medium",
        "accuracy_potential": 0.9
    },
    "imitation": {
        "name": "Imitation Learning",
        "description": "Learn by watching human demonstrations",
        "best_for": ["strategy", "puzzle", "rpg"],
        "training_time": "fast",
        "accuracy_potential": 0.85
    },
    "hybrid": {
        "name": "Hybrid Learning",
        "description": "Combine imitation and reinforcement",
        "best_for": ["all"],
        "training_time": "long",
        "accuracy_potential": 0.95
    },
    "evolutionary": {
        "name": "Evolutionary Algorithm",
        "description": "Evolve strategies through generations",
        "best_for": ["racing", "fighting", "sports"],
        "training_time": "long",
        "accuracy_potential": 0.92
    }
}

# ============ DATABASE HELPER ============

def get_db():
    from server import db
    return db

# ============ CLOUD CONTROLLER ENDPOINTS ============

@npc_gaming_router.post("/controller/create")
async def create_cloud_controller(npc_id: str, npc_name: str):
    """Create a cloud controller for an NPC"""
    db = get_db()
    
    # Check if NPC exists
    npc = await db.ai_villagers.find_one({"villager_id": npc_id})
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    # Check if controller already exists
    existing = await db.cloud_controllers.find_one({"npc_id": npc_id})
    if existing:
        return {"controller_id": existing["controller_id"], "already_exists": True}
    
    controller = CloudController(
        controller_id=f"ctrl_{str(uuid.uuid4())[:8]}",
        npc_id=npc_id,
        npc_name=npc_name or npc.get("name", "Unknown NPC"),
        supported_inputs=[InputType.BUTTON, InputType.DPAD, InputType.TOUCH, InputType.KEYBOARD],
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.cloud_controllers.insert_one(controller.dict())
    
    return {
        "controller_id": controller.controller_id,
        "npc_id": npc_id,
        "npc_name": controller.npc_name,
        "status": controller.status,
        "created": True
    }

@npc_gaming_router.get("/controller/{controller_id}")
async def get_controller(controller_id: str):
    """Get cloud controller details"""
    db = get_db()
    
    controller = await db.cloud_controllers.find_one({"controller_id": controller_id}, {"_id": 0})
    if not controller:
        raise HTTPException(status_code=404, detail="Controller not found")
    
    return controller

@npc_gaming_router.get("/controllers/npc/{npc_id}")
async def get_npc_controller(npc_id: str):
    """Get controller for specific NPC"""
    db = get_db()
    
    controller = await db.cloud_controllers.find_one({"npc_id": npc_id}, {"_id": 0})
    if not controller:
        # Auto-create controller
        npc = await db.ai_villagers.find_one({"villager_id": npc_id})
        if npc:
            await create_cloud_controller(npc_id, npc.get("name"))
            controller = await db.cloud_controllers.find_one({"npc_id": npc_id}, {"_id": 0})
    
    return controller

@npc_gaming_router.get("/controllers/list")
async def list_controllers(status: Optional[str] = None, limit: int = 50):
    """List all cloud controllers"""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    controllers = await db.cloud_controllers.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    return {"controllers": controllers, "count": len(controllers)}

# ============ GAME SESSION MANAGEMENT ============

@npc_gaming_router.post("/session/start")
async def start_game_session(controller_id: str, game_id: str):
    """Start a game session for an NPC controller"""
    db = get_db()
    
    controller = await db.cloud_controllers.find_one({"controller_id": controller_id})
    if not controller:
        raise HTTPException(status_code=404, detail="Controller not found")
    
    if controller["status"] not in [ControllerState.IDLE, ControllerState.PAUSED]:
        raise HTTPException(status_code=400, detail=f"Controller is {controller['status']}, cannot start new session")
    
    game = SUPPORTED_GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not supported")
    
    session = GameSession(
        session_id=f"sess_{str(uuid.uuid4())[:8]}",
        controller_id=controller_id,
        npc_id=controller["npc_id"],
        game_id=game_id,
        platform=game["platform"],
        started_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.game_sessions.insert_one(session.dict())
    
    # Update controller status
    await db.cloud_controllers.update_one(
        {"controller_id": controller_id},
        {"$set": {
            "status": ControllerState.PLAYING,
            "current_game": game_id,
            "current_platform": game["platform"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "session_id": session.session_id,
        "game": game,
        "controller_id": controller_id,
        "npc_name": controller["npc_name"],
        "status": "started"
    }

@npc_gaming_router.post("/session/{session_id}/action")
async def submit_action(session_id: str, action: Dict[str, Any]):
    """Submit an action in a game session (for AI decision making)"""
    db = get_db()
    
    session = await db.game_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session not active")
    
    # Record action
    action_record = {
        "action_id": str(uuid.uuid4()),
        "session_id": session_id,
        "action_type": action.get("type"),
        "action_data": action.get("data"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.game_actions.insert_one(action_record)
    
    # Update session stats
    await db.game_sessions.update_one(
        {"session_id": session_id},
        {"$inc": {"actions_taken": 1}}
    )
    
    # Simulate game response (in production, this would interact with actual game)
    game_response = simulate_game_response(session["game_id"], action)
    
    return {
        "action_accepted": True,
        "game_response": game_response,
        "session_stats": {
            "actions_taken": session["actions_taken"] + 1,
            "current_score": session["current_score"] + game_response.get("score_change", 0)
        }
    }

def simulate_game_response(game_id: str, action: Dict) -> Dict:
    """Simulate game response to an action"""
    import random
    
    game = SUPPORTED_GAMES.get(game_id, {})
    genre = game.get("genre", "unknown")
    
    # Simulate different responses based on genre
    if genre == "puzzle":
        success = random.random() > 0.3
        return {
            "success": success,
            "score_change": 10 if success else 0,
            "puzzle_progress": random.uniform(0.05, 0.15) if success else 0,
            "feedback": "Correct move!" if success else "Try again"
        }
    elif genre == "action":
        damage_dealt = random.randint(5, 25)
        damage_taken = random.randint(0, 10)
        return {
            "success": True,
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "score_change": damage_dealt,
            "enemy_defeated": random.random() > 0.8
        }
    elif genre == "platformer":
        return {
            "success": random.random() > 0.2,
            "position_change": {"x": random.randint(-5, 10), "y": random.randint(-2, 5)},
            "coins_collected": random.randint(0, 3),
            "score_change": random.randint(0, 100)
        }
    else:
        return {
            "success": True,
            "score_change": random.randint(0, 50),
            "feedback": "Action processed"
        }

@npc_gaming_router.post("/session/{session_id}/end")
async def end_game_session(session_id: str):
    """End a game session"""
    db = get_db()
    
    session = await db.game_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Calculate final stats
    end_time = datetime.now(timezone.utc)
    start_time = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
    duration_minutes = (end_time - start_time).total_seconds() / 60
    
    # Update session
    await db.game_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": "completed",
            "ended_at": end_time.isoformat(),
            "duration_minutes": duration_minutes
        }}
    )
    
    # Update controller
    await db.cloud_controllers.update_one(
        {"controller_id": session["controller_id"]},
        {
            "$set": {
                "status": ControllerState.IDLE,
                "current_game": None,
                "updated_at": end_time.isoformat()
            },
            "$inc": {
                "games_played": 1,
                "total_playtime_minutes": int(duration_minutes)
            }
        }
    )
    
    # Update skill level for this game
    skill_improvement = min(0.1, duration_minutes * 0.001)  # Small improvement per minute
    await db.cloud_controllers.update_one(
        {"controller_id": session["controller_id"]},
        {"$inc": {f"skill_levels.{session['game_id']}": skill_improvement}}
    )
    
    return {
        "session_id": session_id,
        "status": "completed",
        "final_score": session["current_score"],
        "duration_minutes": round(duration_minutes, 2),
        "actions_taken": session["actions_taken"],
        "skill_improvement": round(skill_improvement, 4)
    }

# ============ TRAINING SYSTEM ============

@npc_gaming_router.post("/training/start")
async def start_training(config: TrainingConfig):
    """Start training an NPC on a specific game"""
    db = get_db()
    
    controller = await db.cloud_controllers.find_one({"npc_id": config.npc_id})
    if not controller:
        raise HTTPException(status_code=404, detail="Controller not found for NPC")
    
    if controller["status"] != ControllerState.IDLE:
        raise HTTPException(status_code=400, detail="Controller busy")
    
    game = SUPPORTED_GAMES.get(config.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not supported")
    
    # Create training session
    training_session = {
        "training_id": f"train_{str(uuid.uuid4())[:8]}",
        "controller_id": controller["controller_id"],
        "npc_id": config.npc_id,
        "game_id": config.game_id,
        "platform": config.platform,
        "training_mode": config.training_mode,
        "learning_rate": config.learning_rate,
        "total_episodes": config.episodes,
        "completed_episodes": 0,
        "current_performance": 0.0,
        "best_performance": 0.0,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.training_sessions.insert_one(training_session)
    
    # Update controller
    await db.cloud_controllers.update_one(
        {"controller_id": controller["controller_id"]},
        {"$set": {
            "status": ControllerState.LEARNING,
            "current_game": config.game_id,
            "learning_model_id": training_session["training_id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # In production, this would spawn actual training process
    # For now, we simulate training progress
    asyncio.create_task(simulate_training(training_session["training_id"]))
    
    return {
        "training_id": training_session["training_id"],
        "npc_id": config.npc_id,
        "game": game["name"],
        "training_mode": config.training_mode,
        "episodes": config.episodes,
        "status": "started",
        "strategy_info": LEARNING_STRATEGIES.get(config.training_mode, {})
    }

async def simulate_training(training_id: str):
    """Simulate training progress (in production, this would be actual ML training)"""
    db = get_db()
    
    for episode in range(1, 101):  # Simulate 100 episodes
        await asyncio.sleep(0.5)  # Simulate training time
        
        # Update progress
        performance = min(1.0, episode * 0.01 + 0.3)  # Gradually improve
        
        await db.training_sessions.update_one(
            {"training_id": training_id},
            {"$set": {
                "completed_episodes": episode,
                "current_performance": performance,
                "best_performance": max(performance, 0)
            }}
        )
        
        if episode >= 100:
            # Training complete
            await db.training_sessions.update_one(
                {"training_id": training_id},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # Update controller
            session = await db.training_sessions.find_one({"training_id": training_id})
            if session:
                await db.cloud_controllers.update_one(
                    {"controller_id": session["controller_id"]},
                    {
                        "$set": {
                            "status": ControllerState.IDLE,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        },
                        "$inc": {"training_iterations": 100}
                    }
                )

@npc_gaming_router.get("/training/{training_id}")
async def get_training_status(training_id: str):
    """Get training session status"""
    db = get_db()
    
    session = await db.training_sessions.find_one({"training_id": training_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    return session

# ============ CONTROLLER TRANSFER SYSTEM ============

@npc_gaming_router.post("/transfer")
async def transfer_controller(request: ControllerTransferRequest):
    """Transfer an NPC's controller to a different game"""
    db = get_db()
    
    controller = await db.cloud_controllers.find_one({"controller_id": request.controller_id})
    if not controller:
        raise HTTPException(status_code=404, detail="Controller not found")
    
    if not controller.get("can_transfer", True):
        raise HTTPException(status_code=403, detail="Controller cannot be transferred")
    
    if controller["status"] == ControllerState.PLAYING:
        raise HTTPException(status_code=400, detail="Cannot transfer while playing. End current session first.")
    
    target_game = SUPPORTED_GAMES.get(request.target_game)
    if not target_game:
        raise HTTPException(status_code=404, detail="Target game not supported")
    
    # Record transfer
    transfer_record = {
        "transfer_id": str(uuid.uuid4()),
        "controller_id": request.controller_id,
        "source_game": request.source_game,
        "target_game": request.target_game,
        "target_platform": request.target_platform,
        "skills_transferred": request.transfer_skills,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Calculate skill transfer (skills partially transfer to similar games)
    transferred_skills = {}
    if request.transfer_skills:
        source_skill = controller.get("skill_levels", {}).get(request.source_game, 0)
        
        # Calculate transfer efficiency based on game similarity
        source_game = SUPPORTED_GAMES.get(request.source_game, {})
        transfer_efficiency = 0.5  # Base 50% skill transfer
        
        if source_game.get("genre") == target_game.get("genre"):
            transfer_efficiency = 0.8  # 80% for same genre
        if source_game.get("platform") == target_game.get("platform"):
            transfer_efficiency += 0.1  # +10% for same platform
        
        transferred_skill = source_skill * transfer_efficiency
        transferred_skills[request.target_game] = transferred_skill
    
    # Update controller
    await db.cloud_controllers.update_one(
        {"controller_id": request.controller_id},
        {
            "$set": {
                "status": ControllerState.TRANSFERRING,
                "current_game": request.target_game,
                "current_platform": request.target_platform,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {"transfer_history": transfer_record},
            "$inc": {f"skill_levels.{request.target_game}": transferred_skills.get(request.target_game, 0)}
        }
    )
    
    # Simulate transfer time
    await asyncio.sleep(1)
    
    # Complete transfer
    await db.cloud_controllers.update_one(
        {"controller_id": request.controller_id},
        {"$set": {"status": ControllerState.IDLE}}
    )
    
    return {
        "transfer_id": transfer_record["transfer_id"],
        "controller_id": request.controller_id,
        "source_game": request.source_game,
        "target_game": request.target_game,
        "target_platform": request.target_platform,
        "skills_transferred": transferred_skills,
        "status": "completed"
    }

# ============ GAME CATALOG ============

@npc_gaming_router.get("/games")
async def list_games(platform: Optional[str] = None, genre: Optional[str] = None):
    """List all supported games"""
    games = []
    
    for game_id, game_data in SUPPORTED_GAMES.items():
        if platform and game_data["platform"] != platform:
            continue
        if genre and game_data["genre"] != genre:
            continue
        
        games.append({
            "game_id": game_id,
            **game_data
        })
    
    return {
        "games": games,
        "platforms": [p.value for p in GamePlatform],
        "genres": list(set(g["genre"] for g in SUPPORTED_GAMES.values()))
    }

@npc_gaming_router.get("/games/{game_id}")
async def get_game_details(game_id: str):
    """Get details for a specific game"""
    game = SUPPORTED_GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return {
        "game_id": game_id,
        **game,
        "learning_strategies": LEARNING_STRATEGIES
    }

@npc_gaming_router.get("/strategies")
async def list_learning_strategies():
    """List all AI learning strategies"""
    return {"strategies": LEARNING_STRATEGIES}
