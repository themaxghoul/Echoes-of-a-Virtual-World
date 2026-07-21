"""
Shared Database Module
======================
Centralizes MongoDB connection to prevent circular imports.
All routers should import db from this module instead of server.py.
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os

# MongoDB connection (singleton)
_client = None
_db = None

def get_database():
    """Get the database instance, creating connection if needed."""
    global _client, _db
    if _db is None:
        mongo_url = os.environ.get('MONGO_URL')
        db_name = os.environ.get('DB_NAME', 'ai_village')
        if not mongo_url:
            raise RuntimeError("MONGO_URL environment variable not set")
        _client = AsyncIOMotorClient(mongo_url)
        _db = _client[db_name]
    return _db

def get_client():
    """Get the MongoDB client instance."""
    global _client
    if _client is None:
        get_database()  # Initialize connection
    return _client

# For backwards compatibility - lazy initialization
class LazyDB:
    """Lazy database proxy that initializes on first access."""
    def __getattr__(self, name):
        return getattr(get_database(), name)

db = LazyDB()

# Village locations constant (moved from server.py to break circular dependency)
VILLAGE_LOCATIONS = {
    "village_square": {
        "name": "The Hollow Square",
        "description": "The heart of the village, where paths converge under ancient lanterns.",
        "connections": ["oracle_sanctum", "the_forge", "ancient_library", "wanderers_rest"],
        "danger_level": 0,
        "terrain": "cobblestone"
    },
    "oracle_sanctum": {
        "name": "Oracle's Sanctum",
        "description": "A mystical chamber where prophecies echo through crystalline halls.",
        "connections": ["village_square", "shadow_grove"],
        "danger_level": 1,
        "terrain": "mystical_stone"
    },
    "the_forge": {
        "name": "The Ember Forge",
        "description": "Heat radiates from massive furnaces where master smiths work.",
        "connections": ["village_square", "watchtower"],
        "danger_level": 2,
        "terrain": "volcanic"
    },
    "ancient_library": {
        "name": "Ancient Library",
        "description": "Towering shelves hold knowledge from ages past.",
        "connections": ["village_square", "shadow_grove"],
        "danger_level": 1,
        "terrain": "marble"
    },
    "wanderers_rest": {
        "name": "Wanderer's Rest",
        "description": "A welcoming inn where travelers share tales by firelight.",
        "connections": ["village_square", "outer_realms"],
        "danger_level": 0,
        "terrain": "forest_clearing"
    },
    "shadow_grove": {
        "name": "Shadow Grove",
        "description": "Twisted trees cast impossible shadows in this cursed forest.",
        "connections": ["oracle_sanctum", "ancient_library", "outer_realms"],
        "danger_level": 4,
        "terrain": "dark_forest"
    },
    "watchtower": {
        "name": "The Watchtower",
        "description": "Standing vigilant against threats, this tower overlooks all.",
        "connections": ["the_forge", "outer_realms"],
        "danger_level": 3,
        "terrain": "highland"
    },
    "outer_realms": {
        "name": "Outer Realms",
        "description": "Beyond the village lies untamed wilderness and ancient ruins.",
        "connections": ["wanderers_rest", "shadow_grove", "watchtower"],
        "danger_level": 5,
        "terrain": "ethereal"
    }
}
