# Game constants and configurations

# ============ Permission Levels & Rankings ============
PERMISSION_LEVELS = {
    "basic": {
        "level": 1,
        "abilities": ["explore", "talk", "trade", "view_quests"],
        "description": "Standard player abilities",
        "chat_access": ["local"]
    },
    "advanced": {
        "level": 2,
        "abilities": ["craft", "teach_ai", "create_quests", "mentor"],
        "description": "Experienced player abilities",
        "chat_access": ["local", "city"]
    },
    "admin": {
        "level": 3,
        "abilities": ["modify_world", "spawn_npcs", "manage_users", "allocate_resources"],
        "description": "Administrator abilities",
        "chat_access": ["local", "city", "state"]
    },
    "sirix_1": {
        "level": 999,
        "abilities": ["all", "immutable", "supreme_override"],
        "description": "Supreme authority - cannot be overwritten",
        "chat_access": ["local", "city", "state", "country", "global"]
    }
}

# Official Rankings (for government/leadership roles)
OFFICIAL_RANKINGS = {
    "citizen": {"tier": "city", "rank": 1, "chat_access": ["local"], "title": "Citizen"},
    "merchant": {"tier": "city", "rank": 2, "chat_access": ["local", "city"], "title": "Merchant"},
    "guild_member": {"tier": "city", "rank": 3, "chat_access": ["local", "city"], "title": "Guild Member"},
    "guild_master": {"tier": "city", "rank": 4, "chat_access": ["local", "city"], "title": "Guild Master"},
    "city_council": {"tier": "city", "rank": 5, "chat_access": ["local", "city"], "title": "City Council"},
    "mayor": {"tier": "city", "rank": 6, "chat_access": ["local", "city", "state"], "title": "Mayor"},
    "state_delegate": {"tier": "state", "rank": 7, "chat_access": ["local", "city", "state"], "title": "State Delegate"},
    "state_senator": {"tier": "state", "rank": 8, "chat_access": ["local", "city", "state"], "title": "State Senator"},
    "governor": {"tier": "state", "rank": 9, "chat_access": ["local", "city", "state", "country"], "title": "Governor"},
    "ambassador": {"tier": "country", "rank": 10, "chat_access": ["local", "city", "state", "country"], "title": "Ambassador"},
    "minister": {"tier": "country", "rank": 11, "chat_access": ["local", "city", "state", "country"], "title": "Minister"},
    "high_council": {"tier": "country", "rank": 12, "chat_access": ["local", "city", "state", "country", "global"], "title": "High Council"},
    "sovereign": {"tier": "country", "rank": 13, "chat_access": ["all"], "title": "Sovereign"},
}

# Standing system (reputation-based)
STANDING_LEVELS = [
    {"name": "Outcast", "min_rep": -1000, "max_rep": -100},
    {"name": "Distrusted", "min_rep": -99, "max_rep": -1},
    {"name": "Neutral", "min_rep": 0, "max_rep": 99},
    {"name": "Respected", "min_rep": 100, "max_rep": 499},
    {"name": "Honored", "min_rep": 500, "max_rep": 999},
    {"name": "Revered", "min_rep": 1000, "max_rep": 4999},
    {"name": "Exalted", "min_rep": 5000, "max_rep": 9999},
    {"name": "Legendary", "min_rep": 10000, "max_rep": 999999},
]

# ============ Building Materials ============
MATERIALS = {
    "wood": {
        "name": "Timber",
        "description": "Basic building material from the Shadow Grove",
        "strength": 20,
        "durability": 30,
        "rarity": "common",
        "gather_locations": ["shadow_grove", "wanderers_rest"],
        "color": "#8B4513"
    },
    "stone": {
        "name": "Cobblestone",
        "description": "Sturdy stone quarried from the village foundations",
        "strength": 50,
        "durability": 60,
        "rarity": "common",
        "gather_locations": ["village_square", "watchtower"],
        "color": "#696969"
    },
    "iron": {
        "name": "Forged Iron",
        "description": "Metal refined in the Ember Forge",
        "strength": 75,
        "durability": 50,
        "rarity": "uncommon",
        "gather_locations": ["the_forge"],
        "color": "#434343"
    },
    "crystal": {
        "name": "Echo Crystal",
        "description": "Mystical crystals from the Oracle's Sanctum",
        "strength": 40,
        "durability": 80,
        "rarity": "rare",
        "gather_locations": ["oracle_sanctum", "ancient_library"],
        "color": "#00CED1"
    },
    "obsidian": {
        "name": "Void Obsidian",
        "description": "The strongest material, found in the deepest shadows",
        "strength": 95,
        "durability": 90,
        "rarity": "legendary",
        "gather_locations": ["watchtower"],
        "color": "#1a1a2e"
    }
}

# ============ Day/Night Cycle System ============
DAY_PHASES = {
    "dawn": {"start_hour": 5, "end_hour": 7, "description": "The first light pierces the darkness", "danger_level": 0.2},
    "morning": {"start_hour": 7, "end_hour": 12, "description": "The village stirs to life", "danger_level": 0.1},
    "afternoon": {"start_hour": 12, "end_hour": 17, "description": "The sun hangs high, commerce thrives", "danger_level": 0.1},
    "dusk": {"start_hour": 17, "end_hour": 20, "description": "Shadows lengthen, wise folk head indoors", "danger_level": 0.3},
    "night": {"start_hour": 20, "end_hour": 24, "description": "Darkness reigns, demons stir", "danger_level": 0.7},
    "witching_hour": {"start_hour": 0, "end_hour": 3, "description": "The veil between worlds thins", "danger_level": 1.0},
    "pre_dawn": {"start_hour": 3, "end_hour": 5, "description": "The deepest dark before dawn", "danger_level": 0.5}
}

# Guild System
GUILD_RANKS = {
    "initiate": {"level": 1, "permissions": ["view_guild", "guild_chat"], "title": "Initiate"},
    "member": {"level": 2, "permissions": ["view_guild", "guild_chat", "use_guild_storage"], "title": "Member"},
    "veteran": {"level": 3, "permissions": ["view_guild", "guild_chat", "use_guild_storage", "invite_members"], "title": "Veteran"},
    "officer": {"level": 4, "permissions": ["view_guild", "guild_chat", "use_guild_storage", "invite_members", "kick_members", "manage_storage"], "title": "Officer"},
    "leader": {"level": 5, "permissions": ["all"], "title": "Guild Leader"}
}

GUILD_TYPES = {
    "trade": {"focus": "commerce", "bonuses": {"gold_gain": 1.2, "trade_discount": 0.9}},
    "combat": {"focus": "fighting", "bonuses": {"damage": 1.15, "defense": 1.1}},
    "crafting": {"focus": "creation", "bonuses": {"craft_speed": 1.25, "material_efficiency": 0.85}},
    "exploration": {"focus": "discovery", "bonuses": {"travel_speed": 1.3, "discovery_chance": 1.2}},
    "mystical": {"focus": "magic", "bonuses": {"essence_gain": 1.25, "spell_power": 1.15}}
}

# ============ AI Emotional Memory System ============
AI_MOODS = {
    "joyful": {"modifier": 1.3, "trade_bonus": 0.9, "will_help": True, "dialogue_tone": "warm and welcoming"},
    "content": {"modifier": 1.1, "trade_bonus": 0.95, "will_help": True, "dialogue_tone": "pleasant"},
    "neutral": {"modifier": 1.0, "trade_bonus": 1.0, "will_help": True, "dialogue_tone": "professional"},
    "annoyed": {"modifier": 0.9, "trade_bonus": 1.1, "will_help": True, "dialogue_tone": "curt and impatient"},
    "angry": {"modifier": 0.7, "trade_bonus": 1.3, "will_help": False, "dialogue_tone": "hostile"},
    "furious": {"modifier": 0.5, "trade_bonus": 1.5, "will_help": False, "dialogue_tone": "refusing service"},
    "fearful": {"modifier": 0.8, "trade_bonus": 1.0, "will_help": False, "dialogue_tone": "nervous and evasive"},
    "grieving": {"modifier": 0.6, "trade_bonus": 1.0, "will_help": False, "dialogue_tone": "sorrowful"},
    "inspired": {"modifier": 1.4, "trade_bonus": 0.85, "will_help": True, "dialogue_tone": "enthusiastic"}
}

MOOD_EVENTS = {
    "positive_trade": {"mood_change": 5, "description": "Completed a fair trade"},
    "generous_tip": {"mood_change": 15, "description": "Received generosity"},
    "friendly_chat": {"mood_change": 10, "description": "Had a pleasant conversation"},
    "helped_quest": {"mood_change": 20, "description": "Received help with a task"},
    "gift_received": {"mood_change": 25, "description": "Received a gift"},
    "insult": {"mood_change": -20, "description": "Was insulted"},
    "theft_attempt": {"mood_change": -40, "description": "Someone tried to steal"},
    "property_damage": {"mood_change": -50, "description": "Property was damaged"},
    "violence": {"mood_change": -60, "description": "Was attacked or threatened"},
    "betrayal": {"mood_change": -80, "description": "Was betrayed"},
    "witnessed_demon": {"mood_change": -30, "description": "Witnessed demon attack"},
    "saved_from_demon": {"mood_change": 40, "description": "Was saved from demons"}
}

# ============ Combat & Stats System ============
BASE_STATS = {
    "health": 100,
    "max_health": 100,
    "stamina": 100,
    "max_stamina": 100,
    "mana": 50,
    "max_mana": 50,
    "strength": 10,
    "endurance": 10,
    "agility": 10,
    "vitality": 10,
    "intelligence": 10,
    "wisdom": 10,
    "armor_weight": 0,
    "damage_bonus": 0,
    "defense_bonus": 0,
    "spell_power": 0
}

COMBAT_ACTIONS = {
    "attack": {
        "name": "Attack",
        "stamina_cost": 10,
        "base_damage": 15,
        "cooldown": 1.0,
        "description": "Strike your enemy"
    },
    "heavy_attack": {
        "name": "Heavy Attack",
        "stamina_cost": 25,
        "base_damage": 35,
        "cooldown": 2.5,
        "description": "A powerful but slow strike"
    },
    "block": {
        "name": "Block",
        "stamina_cost": 5,
        "damage_reduction": 0.7,
        "description": "Raise your guard to reduce incoming damage"
    },
    "dodge": {
        "name": "Dodge",
        "stamina_cost": 15,
        "invulnerability_frames": 0.5,
        "cooldown": 1.5,
        "description": "Roll to evade attacks"
    },
    "sprint": {
        "name": "Sprint",
        "stamina_cost_base": 0.5,
        "speed_multiplier": 2.0,
        "description": "Run faster at the cost of stamina"
    }
}

ARMOR_TYPES = {
    "none": {"name": "Unarmored", "weight": 0, "defense": 0},
    "cloth": {"name": "Cloth Armor", "weight": 2, "defense": 5},
    "leather": {"name": "Leather Armor", "weight": 5, "defense": 15},
    "chain": {"name": "Chainmail", "weight": 12, "defense": 30},
    "plate": {"name": "Plate Armor", "weight": 25, "defense": 50},
    "legendary": {"name": "Void Armor", "weight": 15, "defense": 75}
}

WEAPON_TYPES = {
    "fists": {"name": "Bare Fists", "damage": 5, "speed": 1.5},
    "dagger": {"name": "Dagger", "damage": 12, "speed": 1.8},
    "sword": {"name": "Iron Sword", "damage": 20, "speed": 1.2},
    "greatsword": {"name": "Greatsword", "damage": 40, "speed": 0.7},
    "mace": {"name": "Mace", "damage": 25, "speed": 1.0},
    "spear": {"name": "Spear", "damage": 22, "speed": 1.1},
    "staff": {"name": "Magic Staff", "damage": 15, "speed": 1.3, "magic_bonus": 20}
}

# Geographic restrictions
RESTRICTED_REGIONS = ["CU", "IR", "KP", "SY", "RU", "BY"]

SUPPORTED_REGIONS = [
    "US", "CA", "GB", "DE", "FR", "AU", "JP", "KR", "SG", "NL", "SE", "NO", "DK", "FI",
    "IE", "NZ", "CH", "AT", "BE", "IT", "ES", "PT", "PL", "CZ", "HU", "RO", "BG", "HR",
    "SK", "SI", "LT", "LV", "EE", "MT", "CY", "LU", "MX", "BR", "AR", "CL", "CO", "PE",
    "IN", "PH", "TH", "MY", "ID", "VN", "ZA", "NG", "KE", "GH", "EG", "MA", "TN"
]
