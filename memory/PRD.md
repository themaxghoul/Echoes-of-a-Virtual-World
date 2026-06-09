# AI Village: The Echoes - Production Ready PRD
## Pre-Release for itch.io

## Overview
A virtual world storytelling experience where AI companions learn and evolve through player interactions. Features real-world monetization (ApexForge Collective), dynamic world events, **full AI autonomy**, persistent memory, and **multiplayer 3D environment** with consistent world seed.

## Deployment: READY FOR ITCH.IO PRE-RELEASE

### Sirix-1 Admin Account
- Username: `sirix_1`
- Password: `HCLynnTV04` (SECURED - do not share publicly)
- Permissions: Transcendent (infinite stats, all access)
- **Has exclusive private realm** only accessible by sirix_1

---

## Game Modes (3 Options)

### 1. Story Mode (2D Chat Adventure)
- Text-based adventure with AI narrator
- **ALL MAPS OPEN** - No progression locks
- 2D Building System with grid-based placement
- Skills gain XP through actions

### 2. First Person 3D (Web)
- Immersive 3D experience in browser
- Top-down stylized world map

### 3. Unity 3D
- High-fidelity Unity client with cross-platform sync
- 3D Character models from descriptor system

---

## P1 FEATURES COMPLETE (April 2026)

### 1. Character Customization with 3D Model Descriptors
**4 Customization Tabs:**
- Basic: Name, Age (16-100), Background Story, Quick Backgrounds, Personality Traits (16 options)
- Appearance: Face Type (5), Skin Tone (8), Hair Style (8), Hair Color (8), Eye Color (8), Features (scars/tattoos/beard)
- Body: Body Type (5), Height (140-220cm)
- Style: Clothing Style (8)

**3D Model Descriptor Export:**
```json
{
  "bodyType": "athletic",
  "faceType": "angular",
  "skinTone": "medium",
  "hairStyle": "medium",
  "hairColor": "brown",
  "eyeColor": "blue",
  "clothingStyle": "adventurer",
  "height": 175,
  "age": 28,
  "scars": true,
  "tattoos": false,
  "beard": false,
  "accessories": []
}
```
Unity/engines interpret this to generate 3D models.

### 2. Task Marketplace (Human & Robot Integration)
**10 Task Categories:**
| Category | Description | Base Pay | Skills Rewarded |
|----------|-------------|----------|-----------------|
| Data Labeling | Label images/text/audio | $0.01-0.10 | Investigation, Lore |
| Transcription | Audio/video to text | $0.05-0.25 | Languages, Lore |
| Content Moderation | Review/flag content | $0.02-0.15 | Investigation, Diplomacy |
| AI Training | Improve AI responses | $0.05-0.50 | Arcana, Lore |
| Quality Assurance | Test features/bugs | $0.10-0.75 | Investigation, Tactics |
| Creative Writing | Stories/dialogues | $0.25-2.00 | Lore, Charm, Languages |
| Art & Design | Visual assets/concepts | $0.50-5.00 | Enchanting, Divination |
| Translation | Multi-language content | $0.10-1.00 | Languages, Diplomacy |
| Research | Compile information | $0.15-1.50 | Investigation, Lore, Arcana |
| World Building | Design locations/NPCs | $0.50-3.00 | Engineering, Lore, Leadership |

**6 Difficulty Levels:**
- Trivial (0.5x), Easy (0.75x), Medium (1.0x), Hard (1.5x), Expert (2.0x), Legendary (3.0x)

### 3. 2D Building System (Grid-Based)
**5 Building Categories:**

| Category | Buildings | Cost Range |
|----------|-----------|------------|
| Basic Structures | Wooden House, Stone House, Cottage, Tower, Wall, Gate, Bridge | 25-300 VE$ |
| Functional | Forge, Farm, Mine, Temple, Marketplace, Library, Barracks, Tavern, Workshop | 150-500 VE$ |
| Decorative | Trees, Flower Bed, Fountain, Statue, Bench, Lamp Post, Well, Signpost | 5-150 VE$ |
| Paths | Dirt Path, Stone Path, Cobblestone Road, Wooden Boardwalk | 2-8 VE$ |
| Special | Portal, Obelisk, Altar, Waypoint, Monument | 200-1000 VE$ |

**Grid System:**
- 100x100 grid per region
- 32px cell size for rendering
- Collision detection
- Building XP awards Engineering skill

### 4. Top-Down World Map
**8 Regions with Consistent Seed:**
| Region | Position | Terrain | Connections |
|--------|----------|---------|-------------|
| The Hollow Square | (50,50) | Cobblestone | Oracle, Forge, Library, Rest |
| Oracle's Sanctum | (30,30) | Mystical Stone | Square, Grove |
| The Ember Forge | (70,40) | Volcanic | Square, Watchtower |
| Ancient Library | (40,70) | Marble | Square, Outer Realms |
| Wanderer's Rest | (60,65) | Forest Clearing | Square, Grove |
| Shadow Grove | (20,60) | Dark Forest | Oracle, Rest, Outer |
| The Watchtower | (85,25) | Highland | Forge, Outer |
| Outer Realms | (15,85) | Ethereal | Library, Grove, Tower |

**15 Terrain Types:**
Grass, Forest, Dark Forest, Water, Shallow Water, Mountain, Highland, Cobblestone, Marble, Volcanic, Mystical Stone, Forest Clearing, Ethereal, Sand, Snow

**Multiplayer Features:**
- Single persistent world (consistent seed)
- Only altered by player/AI interaction
- Entity position tracking
- World modifications history

### 5. Continue Journey Auth Fix
- Verifies character belongs to logged-in user
- Clears invalid character data
- Session isolation between accounts

---

## Previous P0 Systems

### Skills System (30 Skills, 6 Categories)
Combat, Magic, Crafting, Gathering, Social, Knowledge

### Titles System (31 Titles)
Stat boosts from equipped titles

### Entity Earnings (VE$ for All)
Players AND AI earn real currency through activities

### AI Autonomy
- 8 personality traits
- Free will (0-1 scale)
- AI-to-AI conversations
- 20+ autonomous actions

### World Instances
- Private (Sirix-1 exclusive)
- Shared (multiplayer)
- Story (original characters)

---

## Backend Routers (19 Total)
| Router | Prefix | Description |
|--------|--------|-------------|
| server.py | /api | Core routes |
| skills_router.py | /api/skill-system | Skills & Titles |
| ai_autonomy_router.py | /api/ai-autonomy | AI-to-AI, Free Will |
| world_instances_router.py | /api/worlds | Private/Story worlds |
| entity_earnings_router.py | /api/entity-earnings | VE$ earnings |
| conversation_history_router.py | /api/conversations | Chat logs |
| jobs_router.py | /api/jobs | Career system |
| unity_router.py | /api/unity | Unity offload |
| memory_router.py | /api/memory | Persistent memory |
| task_marketplace_router.py | /api/task-marketplace | Human/Robot tasks |
| building_system_router.py | /api/building | 2D building |
| world_map_router.py | /api/world-map | Top-down map |
| ...others | | |

---

## Completed Features
- [x] P0: Skills system (30 skills, 6 categories)
- [x] P0: Titles system (31 titles with stat boosts)
- [x] P0: Entity earnings (VE$ for players AND AI)
- [x] P0: AI autonomy (free will, AI-to-AI conversations)
- [x] P0: World instances (private, shared, story)
- [x] P0: Sirix-1 exclusive private realm
- [x] P1: Character Customization with 3D Model Descriptors
- [x] P1: Task Marketplace (10 categories, human/robot)
- [x] P1: 2D Building System (5 categories, 100x100 grid)
- [x] P1: Top-Down World Map (8 regions, 15 terrains)
- [x] P1: Continue Journey auth fix (session isolation)
- [x] P0: Real-Time Tasks Dashboard (/tasks) - 13 task types with instant VE$ payouts
- [x] P0: AI Compute Marketplace (/compute) - Cloud compute & self-computing farms
- [x] P1: Deployment Guide completed (/app/DEPLOYMENT_GUIDE.md)
- [x] P2: Building Grid UI (/build) - 100x100 grid-based building placement
- [x] P2: World Map UI (/world-map) - Interactive 8-region map with terrain
- [x] P2: Unity WebGL Integration (/webgl) - Browser-based Unity loader framework
- [x] P2: Enhanced Micro-Task Providers - Realistic simulated task data pools
- [x] P0: Multiplayer Chat System - WebSocket real-time chat with 4 channels
- [x] P0: Skill Trees - 5 trees, 32 skills, active/passive abilities
- [x] P0: Title Passives - 10 titles with passive bonuses
- [x] Bug Fix: Registration with display_name field

---

## NEW: Real-Time Tasks System (April 22, 2026)

### 13 Task Types with Instant Payouts:
| Task Type | Payout/Task | Est. Hourly | Skills |
|-----------|-------------|-------------|--------|
| Image Tagging | VE$0.02 | ~VE$7.20 | Investigation |
| Image Comparison | VE$0.015 | ~VE$6.75 | Investigation |
| Content Rating | VE$0.01 | ~VE$7.20 | Diplomacy |
| Sentiment Labeling | VE$0.01 | ~VE$6.00 | Lore |
| Text Categorization | VE$0.025 | ~VE$7.50 | Lore, Investigation |
| Spam Detection | VE$0.008 | ~VE$7.20 | Investigation |
| Audio Transcription | VE$0.10 | ~VE$8.00 | Languages, Lore |
| Response Ranking | VE$0.05 | ~VE$9.00 | Arcana |
| Prompt Writing | VE$0.08 | ~VE$9.60 | Lore, Charm |
| CAPTCHA Solving | VE$0.005 | ~VE$3.60 | Investigation |
| Data Entry | VE$0.04 | ~VE$5.76 | Lore |
| NPC Dialogue Rating | VE$0.03 | ~VE$7.20 | Charm, Diplomacy |
| World Description | VE$0.15 | ~VE$9.00 | Lore, Languages |

**Features:**
- Start task sessions with batch task loading
- Complete tasks for instant VE$ payouts + skill XP
- Session stats tracking (tasks completed, earnings, time)
- Hourly leaderboard showing top earners
- Platform stats (active workers, tasks/hour)

---

## NEW: AI Compute Marketplace (April 22, 2026)

### Cloud Compute Tiers:
| Tier | Specs | Hourly Cost |
|------|-------|-------------|
| Basic Cloud | 2 vCPU, 4GB RAM, 50GB | VE$0.05/hr |
| Standard | 4 vCPU, 16GB RAM, 100GB | VE$0.15/hr |
| Performance | 8 vCPU, 32GB RAM, 250GB | VE$0.40/hr |
| Basic GPU | 4 vCPU, 16GB RAM, T4 GPU | VE$0.50/hr |
| Advanced GPU | 8 vCPU, 64GB RAM, A100 | VE$2.00/hr |
| GPU Cluster | 32 vCPU, 256GB RAM, 8x A100 | VE$12.00/hr |

### Self-Computing Hardware (Passive Income):
| Hardware | One-Time Cost | Monthly Yield | ROI |
|----------|---------------|---------------|-----|
| Raspberry Pi 5 | VE$100 | VE$5/mo | 300% |
| Mini PC Node | VE$300 | VE$15/mo | 300% |
| AI Workstation | VE$3,000 | VE$150/mo | 240% |
| Server Node | VE$8,000 | VE$400/mo | 300% |
| Compute Rack | VE$50,000 | VE$3,000/mo | 360% |

**Features:**
- VE$/USD exchange rate tracking (currently ~$0.991)
- Cloud compute allocation for AI/player
- Hardware purchase with passive yield collection
- Health degradation over lifespan
- Business Owner System Logs (activity monitoring)
- AI/Player mode toggle
- Top AI Investors leaderboard
- Market stats overview

---

## Backend Routers (21 Total)
| Router | Prefix | Description |
|--------|--------|-------------|
| server.py | /api | Core routes |
| skills_router.py | /api/skill-system | Skills & Titles |
| ai_autonomy_router.py | /api/ai-autonomy | AI-to-AI, Free Will |
| world_instances_router.py | /api/worlds | Private/Story worlds |
| entity_earnings_router.py | /api/entity-earnings | VE$ earnings |
| conversation_history_router.py | /api/conversations | Chat logs |
| jobs_router.py | /api/jobs | Career system |
| unity_router.py | /api/unity | Unity offload |
| memory_router.py | /api/memory | Persistent memory |
| task_marketplace_router.py | /api/task-marketplace | Human/Robot tasks |
| building_system_router.py | /api/building | 2D building |
| world_map_router.py | /api/world-map | Top-down map |
| realtime_tasks_router.py | /api/rt-tasks | Real-time micro-tasks |
| currency_compute_router.py | /api/economy | VE$ & compute marketplace |
| multiplayer_chat_router.py | /api/chat | **NEW** WebSocket chat, parties |
| skill_tree_router.py | /api/skill-trees | **NEW** Skills & title passives |

---

## Remaining Tasks
- [ ] VR voice input/output
- [ ] Real external micro-task provider connections (currently simulated)
- [x] ~~Stripe Purchases (enabled - April 26, 2026)~~
- [x] ~~Conversational AI prompts (April 26, 2026)~~
- [x] ~~Civilization structures store (April 26, 2026)~~

---

## NEW: Multiplayer Chat System (April 22, 2026)

### 4 Chat Channels:
| Channel | Scope | Features |
|---------|-------|----------|
| Global | All players | Broadcasts to everyone online |
| Region | Same region | Players in same area |
| Party | Party members | Up to 6 members per party |
| Whisper | Direct message | 1-on-1 private chat |

### Features:
- **WebSocket Real-time**: /api/chat/ws/{user_id}
- **Player Presence**: Online status, current region
- **Typing Indicators**: Shows who's typing
- **Party System**: Create, invite, join, leave parties
- **Block System**: Block/unblock users
- **Pop-out Windows**: Chat can be detached
- **Minimizable**: Collapsible chat panel

### API Endpoints:
- GET /api/chat/online - List online users
- GET /api/chat/history/{channel} - Chat history
- POST /api/chat/party/create - Create party
- POST /api/chat/party/{id}/join - Join party
- POST /api/chat/block - Block user

---

## NEW: Skill Trees System (April 22, 2026)

### 5 Skill Trees (32 Total Skills):
| Tree | Skills | Ultimate |
|------|--------|----------|
| Combat Mastery | Power Strike, Defensive Stance, Whirlwind, Battle Cry, Executioner, Iron Will | Berserker Rage |
| Arcane Arts | Arcane Bolt, Mana Shield, Chain Lightning, Teleport, Meteor Strike, Arcane Mastery | Time Stop |
| Master Craftsman | Basic Smithing, Salvage, Efficient Crafting, Quality Boost | Legendary Enchanter |
| Silver Tongue | Persuasion, Gather Intel, Haggle, Inspire | Master Diplomat |
| Wilderness Expert | Foraging, Tracking, Camouflage, Trap Setting | One With Nature |

### 10 Titles with Passive Bonuses:
| Title | Key Passives |
|-------|--------------|
| Newcomer | +10% XP (first 10 levels) |
| Explorer | +5% movement, +20% exploration XP |
| Hero | +10% party damage, +15% reputation |
| Champion | +15% damage, +10% defense, 50% death save |
| Legend | +20% all stats, party XP bonus |
| Wealthy | +25% gold, exclusive shop access |
| Master Crafter | +30% craft speed, 20% material save |
| Shadow Walker | +30% stealth, silent movement |
| Dragon Slayer | +50% boss damage, fear immunity |
| Transcendent | +50% all stats, +100% XP, -90% death penalty |

---

## NEW: Building Grid UI (April 22, 2026)

### Features:
- **100x100 Grid Canvas**: Interactive grid with zoom (25%-200%), pan, and grid toggle
- **5 Building Categories**: Basic Structures, Functional Buildings, Decorative, Paths, Special
- **Building Placement**: Click-to-place with rotation support, collision detection
- **Building Management**: Select, move, demolish with 50% refund
- **Ownership**: Only owners can move/demolish their buildings
- **Engineering XP**: +10 XP per building placed

### Building Categories:
| Category | Items | Cost Range |
|----------|-------|------------|
| Basic Structures | Wooden/Stone House, Cottage, Tower, Wall, Gate, Bridge | VE$25-300 |
| Functional Buildings | Forge, Farm, Mine, Temple, Marketplace, Library, Barracks, Tavern, Workshop | VE$150-500 |
| Decorative | Trees, Flower Bed, Fountain, Statue, Bench, Lamp Post, Well, Signpost | VE$5-150 |
| Paths | Dirt Path, Stone Path, Cobblestone Road, Wooden Boardwalk | VE$2-8 |
| Special | Portal, Obelisk, Altar, Waypoint, Monument | VE$200-1000 |

### UI Components:
- Left sidebar: Building catalog with category tabs
- Center: 100x100 grid canvas
- Right sidebar: Selected building info panel
- Toolbar: Zoom, grid toggle, rotation, coordinates display

---

## NEW: World Map UI (April 22, 2026)

### Features:
- **8 Regions**: Village Square, Oracle Sanctum, The Forge, Ancient Library, Wanderer's Rest, Shadow Grove, Watchtower, Outer Realms
- **Procedural Terrain**: 15 terrain types (grass, forest, dark_forest, water, mountain, volcanic, mystical_stone, ethereal, etc.)
- **Road Network**: 10 roads connecting regions
- **Entity Tracking**: Real-time player/NPC/creature positions
- **Region Selection**: Click regions to view details (connected regions, NPCs, buildings)
- **Travel System**: Navigate to selected regions

### Region Details:
| Region | Terrain | Color | Description |
|--------|---------|-------|-------------|
| The Hollow Square | Cobblestone | #8B7355 | Central meeting place |
| Oracle's Sanctum | Mystical Stone | #9333EA | Ancient prophecies |
| The Ember Forge | Volcanic | #DC2626 | Master craftsmen |
| Ancient Library | Marble | #3B82F6 | Knowledge repository |
| Wanderer's Rest | Forest Clearing | #22C55E | Traveler haven |
| Shadow Grove | Dark Forest | #1E3A2F | Mysterious forest |
| The Watchtower | Highland | #71717A | Defense outpost |
| Outer Realms | Ethereal | #EC4899 | Beyond the veil |

---

## NEW: Unity WebGL Integration (April 22, 2026)

### Features:
- **Custom Build Loading**: Input URL to Unity WebGL build folder
- **Session Management**: Creates backend session with token sync
- **State Sync**: Character ID and session token sent to Unity
- **Performance Monitoring**: FPS, memory, ping tracking
- **Controls**: Pause/resume, mute, fullscreen toggles
- **Platform Support**: Desktop, Tablet, Mobile (limited)

### Integration Points:
- `POST /api/unity/session`: Create game session
- `POST /api/unity/session/{id}/connect`: Connect client
- `SendMessage('GameManager', 'SetSessionToken', token)`
- `SendMessage('GameManager', 'SetCharacterId', characterId)`

---

## NEW: Enhanced Micro-Task Providers (April 22, 2026)

### Simulated Data Pools (Mimics Toloka/MTurk):
- **Sentiment Samples**: 24 texts (positive, negative, neutral) with ground truth
- **Content Samples**: 15 samples (safe, questionable, unsafe) for moderation training
- **NPC Dialogue Samples**: 8 game-specific dialogue snippets with context
- **AI Response Samples**: 4 prompt/response sets for RLHF training
- **Spam Samples**: 10 spam vs legitimate messages
- **Text Categories**: 6 news categories (technology, sports, politics, entertainment, science, business)
- **World Description Prompts**: 5 creative writing scenarios for game content

### Task Data Includes:
- `provider_hint`: Source/purpose identifier
- `_ground_truth`: Hidden correct answer for quality tracking
- `criteria`: Rating dimensions
- `context`: Situational information

---

## NEW: Profile Customization System (April 22, 2026)

### Features:
- **Display Name**: 2-30 character custom name
- **Status Message**: Up to 100 characters
- **Bio**: Up to 500 characters personal description
- **Profile Picture**: URL-based profile image

### Character Model Presets (12 options):
- Human Male/Female, Elf Male/Female, Dwarf Male/Female
- Orc, Demon, Angel, Robot, Ghost, Beast

### Model Colors (4 customizable):
- Skin Color, Hair Color, Eye Color, Accent Color

### Chat Colors (12 options):
- Default, Gold, Crimson, Emerald, Sapphire, Amethyst
- Rose, Sunset, Ocean, Forest, Royal, Shadow

### Privacy Settings:
- Show Online Status toggle
- Allow Whispers toggle

### UI Tabs:
1. **Profile**: Basic info (name, status, bio, picture)
2. **Appearance**: Model preset & color customization
3. **Chat**: Chat color selection with live preview
4. **Privacy**: Online status & whisper settings

### API Endpoints:
- `GET /api/profile/customization-options`: Available options
- `GET /api/profile/customization/{user_id}`: Current settings
- `PUT /api/profile/customization/{user_id}`: Update settings

---

## NEW: Real Earnings Tracking & Withdrawal Preferences (April 23, 2026)

### Real Earnings History API:
- `GET /api/earnings/history/{user_id}`: Returns actual today_earned, week_earned from transactions
- Daily breakdown with per-day earnings and task counts
- Tracks RT task session earnings separately
- No more simulated/placeholder stats

### Withdrawal Preferences:
- `GET /api/earnings/preferences/{user_id}`: Get saved preferences
- `PUT /api/earnings/preferences/{user_id}`: Save preferences permanently
- Supports: `default_method` (crypto/game_balance), `default_wallet`, `wallet_percentage`, `auto_withdraw_threshold`
- Modal shows "Set as Default" buttons for permanent preference saving

### Session Earnings Sync:
- `POST /api/rt-tasks/session/{session_id}/end` now auto-syncs earnings to main account
- Creates transaction record in earnings_transactions

---

## NEW: Skill Trees System (April 23, 2026)

### 5 Skill Trees:
1. **Combat Mastery**: Power Strike, Defensive Stance, Whirlwind, Battle Cry, Executioner, Iron Will, Berserker Rage
2. **Arcane Arts**: Mana Bolt, Shield, Teleport, Arcane Blast, Mind Control, Soul Drain, Reality Warp
3. **Master Craftsman**: Basic Tools, Repair, Forge Mastery, Enchanting, Alchemy, Masterwork, Legendary Craft
4. **Silver Tongue**: Bargain, Persuade, Intimidate, Inspire, Deception, Leadership, Orator
5. **Wilderness Expert**: Forage, Track, Tame Beast, Camouflage, Survival, Beast Master, One with Nature

### Features:
- 4 tiers per tree with requirements (must unlock prereqs first)
- Active skills (cooldown, cost) and Passive skills (permanent bonuses)
- Skill Points awarded for achievements/levels
- Title Passives: Earn titles to unlock additional bonuses
- UI shows progress (0/7 unlocked), locked/unlocked states, detailed skill modals

### API Endpoints:
- `GET /api/skill-trees/trees`: All skill trees with tiers
- `GET /api/skill-trees/player/{player_id}`: Player skills and points
- `POST /api/skill-trees/unlock`: Unlock a skill
- `GET /api/skill-trees/active-effects`: Combined passive bonuses
- `POST /api/skill-trees/award-points`: Award skill points

---

## NEW: Real Task Provider Integration (April 23, 2026)

### Supported Providers (5 Total):
1. **Toloka (Yandex)** - Image classification, content moderation, text classification
2. **Amazon MTurk** - HITs, surveys, transcription, data labeling
3. **Scale AI** - Image/text annotation, comparison, transcription
4. **Hive AI** - Text/visual moderation, AI detection, spam/PII detection
5. **Appen** - Image/text/audio/video annotation, data collection

### Architecture:
- `task_providers/` package with provider-specific implementations
- `TaskProviderManager` orchestrates all providers
- Unified `ProviderTask` and `TaskSubmission` models
- Async HTTP clients with retry logic and rate limiting

### Required Environment Variables:
```
TOLOKA_API_KEY=your_toloka_oauth_token
MTURK_API_KEY=access_key:secret_key
SCALE_AI_API_KEY=your_scale_api_key
HIVE_API_KEY=your_hive_api_key
APPEN_API_KEY=your_appen_api_key
```

### API Endpoints:
- `GET /api/rt-tasks/providers/status`: Provider configuration status
- `POST /api/rt-tasks/providers/initialize`: Initialize configured providers
- `POST /api/rt-tasks/providers/add`: Add provider with API key
- `GET /api/rt-tasks/providers/health`: Health check all providers
- `GET /api/rt-tasks/providers/balances`: Get account balances
- `GET /api/rt-tasks/providers/task-types`: Get all task types
- `GET /api/rt-tasks/providers/tasks`: Fetch real tasks from providers
- `POST /api/rt-tasks/providers/submit`: Submit task to provider

### Notes:
- System falls back to simulated tasks when no providers configured
- Each provider uses sandbox/production environments
- Task IDs prefixed with provider name (e.g., `toloka_xxx`, `mturk_xxx`)

---

## UPDATE: Coming Soon Modes & Version Fix (April 24, 2026)

- **First Person 3D** and **Unity 3D** modes now show "Coming Soon" overlay
- Version number standardized to **v0.1.0** across all UI elements
- Story Mode remains active and accessible

---

## NEW: 2D Isometric Building System (April 24, 2026)

### Plot Size Tiers:
| Size | Dimensions | Cost | Max Buildings |
|------|------------|------|---------------|
| Small | 4x4 tiles | VE$500 | 1 |
| Medium | 6x6 tiles | VE$1,500 | 3 |
| Large | 8x8 tiles | VE$4,000 | 6 |

### Building Categories (30 prefabs total, 4-6 per category):

**Residential** (6 prefabs):
- Cottage, Townhouse, Manor, Apartment Complex, Villa, Palace

**Commercial** (6 prefabs):
- Market Stall, General Store, Tavern, Bank, Grand Bazaar, Auction House

**Industrial** (6 prefabs):
- Smithy, Carpentry, Alchemy Lab, Foundry, Enchanting Tower, Manufacturing Plant

**Agricultural** (6 prefabs):
- Vegetable Garden, Orchard, Grain Farm, Livestock Pen, Vineyard, Mega Farm

**Civic** (6 prefabs):
- Well, Shrine, Guard Post, Town Hall, Temple, Colosseum

### Features:
- Isometric 2.5D view with pan/zoom controls
- Prefab sprite variants (4-6 per building)
- Plot upgrades (small → medium → large)
- Daily income from buildings
- Building removal with 50% refund

### API Endpoints:
- `GET /api/isometric-building/prefabs`: All building prefabs
- `GET /api/isometric-building/plot-sizes`: Plot tier info
- `POST /api/isometric-building/plot/purchase`: Buy a plot
- `POST /api/isometric-building/building/place`: Place building
- `DELETE /api/isometric-building/building/{plot}/{building}`: Remove building
- `POST /api/isometric-building/plot/upgrade`: Upgrade plot size

---

## NEW: Adventurer Rank & AI Title System (April 24, 2026)

### Rank Progression:
F → E → D → C → B → A → S → SS → SSS → ★1 → ★2 → ★∞

### Rebirth System:
- Rebirth through **achievement**, not death
- First rebirth requires SSS rank (1,000,000 exp)
- Subsequent rebirths require accumulated achievements
- Star ranks (★) can go infinitely: ★1, ★2, ★3, ...

### Title System:
- **AI-driven**: Titles earned based on actions, not named by players
- **6 Categories**: Combat, Exploration, Wealth, Social, Crafting, Special
- **Rarities**: Common → Rare → Epic → Legendary → Mythic → Transcendent → Unique
- **Max buff**: 1000% (10x multiplier) per stat

### Example Titles:
- Monster Slayer: +10% Attack, +5% Crit (Common)
- Dragon Hunter: +25% Attack, +20% Fire Resist (Rare)
- Godslayer: +100% All Stats (Legendary)
- War God: +500% Attack, +300% Crit Damage (Transcendent)
- Extinction Class: +1000% All Stats (Unique - MAX)

### API Endpoints:
- `GET /api/ranks/player/{user_id}`: Player rank, titles, buffs
- `POST /api/ranks/rebirth`: Perform achievement-based rebirth
- `POST /api/ranks/title/claim`: Claim earned title
- `GET /api/ranks/leaderboard`: Top ranked players

---

## NEW: AI Partner & Automated Income System (April 24, 2026)

### Philosophy
AI as partners that offload tasks and generate passive income. Players maintain relationships with AI companions who work for them while away.

### AI Programs (10 Types):
| Program | Compute | Base Gold/hr | Base VE$/hr | Max Multiplier |
|---------|---------|--------------|-------------|----------------|
| Market Analyst | 50 | 10 | 0.02 | 5x |
| Resource Harvester | 30 | 15 | 0.01 | 4x |
| Craft Optimizer | 40 | 12 | 0.015 | 4.5x |
| Quest Runner | 60 | 20 | 0.025 | 6x |
| NPC Merchant | 35 | 18 | 0.02 | 5x |
| Farm Manager | 25 | 8 | 0.01 | 3.5x |
| Dungeon Crawler | 80 | 35 | 0.04 | 8x |
| Research Assistant | 70 | 5 | 0.03 | 5x |
| Security Monitor | 45 | 0 | 0.005 | 4x |
| Energy Converter | 200 | 0 | 0.10 | 10x |

### Trust System:
- **Stranger** (0-20): 0.6x earnings
- **Acquaintance** (20-40): 0.8x earnings
- **Associate** (40-60): 1.0x earnings
- **Partner** (60-75): 1.2x earnings
- **Trusted Ally** (75-90): 1.35x earnings
- **Soulbound** (90-100): 1.5x earnings

### Currencies:
- **Gold**: In-game currency for purchases, quests, NPC trading
- **VE$**: Real value currency, withdrawable

---

## NEW: Quest System (April 24, 2026)

### Quest Categories:
- Story, Faction, Daily, Exploration, Combat, Crafting, Social

### Factions (6):
- Merchants Guild, Adventurers League, Mages Circle
- Craftsmen Union, Nature Wardens, Shadow Network

### Reputation Tiers:
Hostile → Unfriendly → Neutral → Friendly → Honored → Revered → Exalted

### Sample Quests:
- Daily Gathering: 50 Gold, 25 XP
- Monster Hunt: 75 Gold, 40 XP, +15 Adventurers League rep
- Bounty Hunt: 300 Gold, 100 XP, +75 rep

---

## NEW: Player Directions & Introduction (April 24, 2026)

### 8 Player Paths:
1. **Merchant Prince** - Trade and economics
2. **Warrior Champion** - Combat and glory
3. **Arcane Scholar** - Magic and research
4. **Master Artisan** - Crafting and building
5. **Nature Guardian** - Farming and wildlife
6. **Shadow Operative** - Stealth and secrets
7. **Tech Pioneer** - AI and automation
8. **Free Spirit** - Complete freedom

### Introduction System:
- 7-step introduction explaining the Virtual Verse
- Skippable after path selection
- Covers: Welcome, Path Selection, AI Partner, Economy, Building, Purpose, Begin

---

## The Virtual Verse - Single Seed World (April 24, 2026)

### Concept:
A unified, persistent world shared by all players. Every action shapes reality.

### Scale Progression:
| Scale | Size | Compute Required |
|-------|------|------------------|
| Genesis | 0.1x | 0 |
| Expansion | 0.5x | 10,000 |
| Continents | 1x | 100,000 |
| Megaverse | 2x | 1,000,000 |
| Infinite Realm | 4x | 10,000,000 |

### Energy Conversion (End-game):
At 4x Earth scale (10M compute), computational power converts to real-world energy efficiency:
- 1M compute = sustainable energy for 1000 households
- Goal: Transform computational power into real-world positive impact

---
Last Updated: April 24, 2026

## P0-P2 FEATURES COMPLETE (April 24, 2026 - Session 2)

### P0: Hybrid Task Marketplace with Stripe Connect
**Payment Types:**
- VE$ Only: Pay tasks with in-game currency
- Stripe (Real Money): Pay with credit card via Stripe Connect
- Hybrid: Both VE$ AND Stripe payments combined

**Features:**
- Create tasks with category, difficulty, and instructions
- 10% platform fee (deducted from worker payout)
- VE$ escrow system for task creators
- Workers can browse, accept, submit, and get paid
- Task approval/rejection by creators
- Skills XP awarded on completion

**Endpoints:**
- `POST /api/task-marketplace/hybrid/create` - Create hybrid task
- `GET /api/task-marketplace/hybrid/tasks` - List open tasks
- `POST /api/task-marketplace/hybrid/fund-stripe` - Stripe checkout session
- `POST /api/task-marketplace/hybrid/accept` - Accept task
- `POST /api/task-marketplace/hybrid/submit` - Submit work
- `POST /api/task-marketplace/hybrid/review` - Approve/reject submission

### P1: AI Partners UI
**10 AI Programs for Passive Income:**
| Program | Compute | Gold/hr | VE$/hr | Risk |
|---------|---------|---------|--------|------|
| Market Analyst | 50 | 10 | 0.02 | Medium |
| Resource Harvester | 30 | 15 | 0.01 | Low |
| Craft Optimizer | 40 | 12 | 0.015 | Low |
| Quest Runner | 60 | 20 | 0.025 | Medium |
| NPC Merchant | 35 | 8 | 0.018 | Very Low |
| Farm Manager | 25 | 6 | 0.008 | None |
| Dungeon Explorer | 80 | 30 | 0.05 | High |
| Alchemist AI | 55 | 18 | 0.022 | Medium |
| Defense Coordinator | 45 | 0 | 0 | Low |
| Energy Harvester | 100 | 25 | 0.03 | Low |

**Trust Levels:**
- Stranger (0-19%): 0.6x earnings
- Acquaintance (20-39%): 0.8x earnings
- Associate (40-59%): 1.0x earnings
- Partner (60-74%): 1.2x earnings
- Trusted Ally (75-89%): 1.35x earnings
- Soulbound (90-100%): 1.5x earnings

### P1: Quest Log UI
**7 Quest Categories:**
- Story, Faction, Daily, Exploration, Combat, Crafting, Social

**6 Factions:**
- Merchants Guild, Adventurers League, Arcane Council, Artisans Union, Nature Wardens, Shadow Network

**Features:**
- Accept quests for Gold + XP rewards
- Track quest objectives and completion
- Earn faction reputation
- Quest templates with varying difficulty

### P1: Onboarding/Introduction Flow
**8 Player Paths:**
| Path | Starting Gold | Key Bonuses |
|------|--------------|-------------|
| Merchant Prince | 500 | Market access |
| Warrior Champion | 200 | Combat gear |
| Arcane Scholar | 150 | 200 Compute |
| Master Artisan | 300 | Crafting bonuses |
| Nature Guardian | 200 | Exploration bonuses |
| Shadow Operative | 400 | Stealth bonuses |
| Tech Pioneer | 100 | 300 Compute |
| Free Spirit | 250 | Balanced bonuses |

**7-Step Introduction:**
1. Welcome to Virtual Verse
2. Choose Your Path (with bonuses)
3. AI Partnership explanation
4. Economy (Gold + VE$) overview
5. Building System introduction
6. World Scale & Purpose
7. Begin the Journey

### P2: Leaderboard UI
**3 Leaderboard Categories:**
1. Adventurer Rank - XP and rank progression
2. Top Earners - VE$ earnings hourly
3. Compute Power - Hardware + allocations

**Features:**
- Top 3 podium display
- User rank highlighting
- Real-time refresh

### P2: Mode Selection Updates
**New Quick Access Buttons:**
- Marketplace (`/marketplace`)
- AI Partners (`/ai-partners`)
- Quest Log (`/quest-log`)
- Leaderboard (`/leaderboard`)

---

## FRONTEND ROUTES
```
/auth - Authentication
/create-character - Character creation
/select-mode - Mode selection hub
/village - Story Mode (2D chat adventure)
/isometric-builder - 2D Building System
/marketplace - Hybrid Task Marketplace
/ai-partners - AI Partners (passive income)
/quest-log - Quest Log
/onboarding - New player introduction
/leaderboard - Rankings
/profile-settings - Profile customization
/skill-trees - Skill management
/earnings - Earnings hub
/trading - Trading interface
/jobs - Career hub
```

---

## TESTED & VERIFIED (April 24, 2026)
- All 25 backend API tests passed (100%)
- All 5 new frontend pages loading correctly
- Navigation buttons working on ModeSelection
- Test credentials: sirix_1 / HCLynnTV04

---

## Pre-Deployment Updates (April 25, 2026)

### Title Achievement Auto-Award System
**Trigger-based title awards:**
- Combat: monster_slayer, dragon_hunter, berserker, godslayer, one_man_army, extinction_class
- Exploration: wanderer, cartographer, dungeon_delver, world_walker, seeker_of_secrets
- Economy: gold_digger, millionaire, economic_titan, trader, merchant_king, crypto_pioneer
- Social: friendly_face, beloved, quest_master, diplomat, soulbound_partner
- Crafting: artisan, master_craftsman, legendary_smith, architect

**New Endpoints:**
- `POST /api/ranks/achievement/trigger` - Auto-check and award titles
- `GET /api/ranks/buffs/{user_id}` - Calculate total buffs (capped at 1000%)
- `POST /api/ranks/xp/award` - Award XP with rank-up check

### Loading Screen
- "Created by ApexForge Collective" branding
- Animated loading sequence
- Progress indicators

### Purchase System (BLOCKED)
- All purchases disabled until Stripe integration complete
- `GET /api/purchase/stripe-status` - Check if purchases enabled
- PurchaseContext provides `attemptPurchase()` that shows "Coming Soon" toast
- `STRIPE_INTEGRATION_COMPLETE = False` flag in both frontend and backend

### Files Changed
- `/app/backend/rank_title_router.py` - Auto-award title system
- `/app/backend/server.py` - Purchase status endpoints
- `/app/frontend/src/components/LoadingScreen.jsx` - ApexForge branding
- `/app/frontend/src/context/PurchaseContext.jsx` - Purchase blocking
- `/app/frontend/src/App.js` - Loading screen + PurchaseProvider

---

## QUEUED UPDATES (Future Implementation)

### Bounty Board UI Redesign (P1)
**Visual Theme:**
- Emerald oak wall background texture
- Ragged/worn paper aesthetic for task postings
- Click-to-expand detailed view matching game's fantasy theme
- Wax seals, torn edges, handwritten-style fonts

**Exclusive In-Game Tasks (Non-Automatable):**
These tasks require genuine player engagement and cannot be completed by AI partners:

| Task Type | Description | VE$ Potential |
|-----------|-------------|---------------|
| Rescue Missions | Save NPCs from dangerous situations, escort to safety | High |
| Scouting Uncharted Territory | Explore unmapped regions, report findings | Medium-High |
| Dangerous Territory Recon | Investigate hostile areas, gather intel | High |
| Hosting Diversified Meetings | Organize multi-faction diplomatic events | Medium |
| Artifact Recovery | Retrieve rare items from dungeons | High |
| Monster Bounties | Hunt specific creatures terrorizing regions | Variable |
| Trade Route Establishment | Personally negotiate new commerce paths | Medium |
| First Discovery Experiments | Test untested elements/materials/spells | Very High |

**First Discovery System:**
New spells, materials, or elemental combinations cannot be "slot-machined" into existence. Rules:
- Any **untested** experiment requires an **animate entity present**
- Valid participants: Experiment Manager, Assistant, or Machine Operator
- Once discovered/tested once, the process MAY be automated for reproduction
- First discoverer gets permanent credit + bonus VE$ + potential royalties

**Participant Roles:**
| Role | Responsibility | Automation After Discovery |
|------|----------------|---------------------------|
| Experiment Manager | Oversees the entire process, makes decisions | Cannot be automated |
| Assistant | Supports manager, handles materials | Can be AI after first success |
| Machine Operator | Controls equipment during experiment | Can be AI after first success |

**Why This Matters:**
- Prevents "AFK farming" of new discoveries
- Rewards genuine exploration and risk-taking
- Creates economic value for pioneers
- Balances automation with meaningful gameplay

**Purpose:**
- Incentivize dedicated player engagement for VE$ earnings
- Create meaningful gameplay that AI cannot replicate
- Balance passive income (AI Partners) with active earning opportunities
- Build player investment in the world through exclusive experiences

**Implementation Notes:**
- Task board component: `/app/frontend/src/pages/TaskMarketplace.jsx` (refactor)
- Add `exclusive: true` flag to task schema
- Create `BountyBoard.jsx` component with wood/paper theme
- Add ambient sounds (paper rustling, creaking wood)
- Implement task detail expansion animation

---

## IMPLEMENTED (April 25, 2026 - Session 2 Continued)

### Universal Possession Ledger
**File:** `/app/backend/possession_ledger_router.py`

**Purpose:** Authoritative record of ALL possessions - bypasses ALL concealment methods.

**Endpoints:**
- `POST /api/ledger/record` - Record a possession
- `POST /api/ledger/transfer` - Record item transfer between entities
- `GET /api/ledger/entity/{entity_id}` - Get all possessions for an entity
- `GET /api/ledger/item/{item_id}/history` - Complete ownership history
- `GET /api/ledger/search` - Search possessions by criteria
- `GET /api/ledger/concealed` - View ALL concealed items (bypasses hiding)
- `GET /api/ledger/audit-trail` - Full audit log
- `GET /api/ledger/stats` - Ledger statistics
- `DELETE /api/ledger/remove/{ledger_id}` - Remove/destroy possession

**Bypassed Concealment Methods:**
- invisibility, pocket_dimension, shadow_storage, soul_binding
- dimensional_pocket, thieves_cant_hiding, assassin_stash
- magical_concealment, illusion_cover, void_storage
- time_locked, parallel_dimension, dream_realm_storage, spirit_realm_cache

### Grand Loading Screen
**File:** `/app/frontend/src/components/LoadingScreen.jsx`

**Cinematic Sequence (~3.5s):**
1. **0-1.5s:** Title scales up grandly "AI VILLAGE" + "THE ECHOES"
2. **1.5s:** "Created by" flies in fast from right
3. **1.8-3.8s:** Pauses for 2 seconds (readable)
4. **3.8s:** Fast zoom out to left
5. **4.2s:** Fade out complete

**Visual Features:**
- Wide proud title with letter-spacing
- Floating ambient particles
- Gradient glows and decorative lines
- Bouncing loading dots

### Bounty Board UI (Implemented)
**Files:**
- `/app/frontend/src/pages/BountyBoard.jsx`
- `/app/backend/bounty_board_router.py`

**Visual Theme:**
- Emerald oak wall background with wood grain texture
- Ragged parchment paper postings with torn edges
- Wax seals for bounty type icons
- Pin/nail effects holding papers to wall
- Click-to-expand detailed scroll view

**7 Exclusive Bounty Types (Non-Automatable):**
| Type | VE Multiplier | Description |
|------|---------------|-------------|
| Rescue Mission | 1.5x | Save NPCs from danger |
| Scout Uncharted | 1.3x | Explore unmapped regions |
| Dangerous Recon | 1.8x | Infiltrate hostile areas |
| Diplomatic Meeting | 1.2x | Host multi-faction events |
| Artifact Recovery | 1.6x | Retrieve dungeon items |
| Monster Bounty | 1.4x | Hunt specific creatures |
| First Discovery | 2.0x | Test untested elements/spells + Pioneer bonus + Royalties |

**Key Features:**
- Presence verification required (cannot be automated)
- Time limits with deadlines
- Difficulty-based rewards (trivial → legendary)
- First Discovery system with royalty tracking
- Skills requirements per bounty type

**Endpoints:**
- `GET /api/bounty-board/types` - All bounty types
- `GET /api/bounty-board/available` - Open bounties
- `POST /api/bounty-board/create` - Create bounty
- `POST /api/bounty-board/accept` - Accept bounty
- `POST /api/bounty-board/verify-presence` - Anti-automation check
- `POST /api/bounty-board/complete` - Submit completion
- `GET /api/bounty-board/my-bounties/{user_id}` - User's bounties
- `POST /api/bounty-board/seed-bounties` - Seed test data

---

## IMPLEMENTED (April 26, 2026)

### NPC Memory Delocalization System
**File:** `/app/backend/npc_memory_router.py`

**Concept:** Memory states are NOT centralized. Each NPC maintains individual memory that only updates when they personally encounter information through witnessing events or receiving evidence.

**6 Memory Event Types:**
| Type | Reliability | Decay Rate | Description |
|------|-------------|------------|-------------|
| witnessed_action | 100% | 0.001 | NPC was physically present |
| heard_rumor | 70% | 0.01 | Heard from another NPC |
| received_evidence | 90% | 0.002 | Received physical evidence |
| fabricated_info | 0% | 0.005 | Planted/false information |
| confession | 95% | 0.003 | Direct confession received |
| deduced | 60% | 0.008 | Logically inferred |

**5 Evidence Types:**
| Type | Transfer Reliability Loss | Can Destroy |
|------|--------------------------|-------------|
| physical_item | 5% | Yes |
| written_document | 2% | Yes (copyable) |
| magical_imprint | 10% | No (fades naturally) |
| witness_testimony | 15% | No |
| divine_revelation | 0% | No (requires oracle) |

**Propagation Rules:**
- 30% chance NPC shares memory in conversation
- 10% reliability loss per gossip transfer
- Max 5 propagation hops before memory degrades
- Merchants 20% more likely to gossip
- Innkeepers 40% more likely to gossip

**Implications:**
- Secrets remain hidden unless witnesses talk
- Players can manipulate information flow
- False information can spread organically
- NPC knowledge is verifiable and traceable

**Endpoints:**
- `GET /api/npc-memory/event-types` - All event/evidence types
- `POST /api/npc-memory/event/record` - Record world event, create witness memories
- `POST /api/npc-memory/transfer` - Transfer memory between NPCs
- `GET /api/npc-memory/npc/{npc_id}/memories` - Get NPC's memories
- `GET /api/npc-memory/npc/{npc_id}/knows-about/{entity_id}` - What NPC knows about entity
- `POST /api/npc-memory/evidence/create` - Create evidence item
- `POST /api/npc-memory/evidence/{evidence_id}/transfer` - Transfer evidence
- `DELETE /api/npc-memory/evidence/{evidence_id}/destroy` - Destroy evidence
- `POST /api/npc-memory/gossip/simulate` - Simulate gossip round at location
- `GET /api/npc-memory/stats` - Memory system statistics

---

### Extended Materials & Components System
**File:** `/app/backend/materials_router.py`

**27 Materials in 6 Categories:**

| Category | Count | Examples |
|----------|-------|----------|
| Basic | 4 | Timber, Cobblestone, Clay, Sand |
| Metal | 5 | Iron Ore, Forged Iron, Steel, Mithril, Adamantine |
| Crystal | 5 | Echo Crystal, Void Obsidian, Sunstone, Moonpearl, Bloodstone |
| Organic | 4 | Ancient Bark, Ether Silk, Dragon Scale, Phoenix Feather |
| Essence | 4 | Mana Essence, Shadow Essence, Holy Essence, Chaos Essence |
| Alchemical | 5 | Charcoal, Carbon Dust, Philosopher's Salt, Quicksilver, Demon Ichor |

**6 Rarity Tiers:**
Common → Uncommon → Rare → Epic → Legendary → Mythic

**16 Craftable Components in 4 Categories:**

| Category | Count | Examples |
|----------|-------|----------|
| Structural | 6 | Wooden Beam, Stone Block, Brick, Glass Pane, Iron Nail, Steel Beam |
| Magical | 4 | Rune Stone, Ward Crystal, Mana Conduit, Shadow Anchor |
| Decorative | 3 | Ornate Tile, Stained Glass, Gold Trim |
| Mechanical | 3 | Gear, Spring, Clockwork Core |

**Features:**
- Crafting trees with material dependencies
- Gathering by location
- Processing chains (ore → refined metal)
- Magical properties for special materials
- Skill requirements for crafting

**Endpoints:**
- `GET /api/materials/list` - All 27 materials
- `GET /api/materials/components` - All 16 components
- `GET /api/materials/{material_id}` - Specific material details
- `GET /api/materials/component/{component_id}` - Specific component details
- `GET /api/materials/by-location/{location_id}` - Gatherable materials
- `GET /api/materials/by-rarity/{rarity}` - Materials by rarity tier
- `GET /api/materials/crafting-tree/{material_id}` - Full crafting tree
- `POST /api/materials/gather` - Gather material at location
- `POST /api/materials/craft` - Craft component from materials
- `GET /api/materials/inventory/{user_id}` - User's inventory

---

### AI Digest Summary System
**File:** `/app/backend/ai_digest_router.py`

**Purpose:** Machine-readable digest of game state for LLM context injection, NPC behavior modeling, and cross-system synchronization.

**Endpoints:**
- `GET /api/digest/compact` - Minimal digest for limited token budgets
- `GET /api/digest/full` - Comprehensive game state (20+ sections)
- `GET /api/digest/world-state` - Current world state for AI simulation
- `GET /api/digest/for-npc/{npc_id}` - NPC-specific context digest

**Compact Digest Contents:**
```json
{
  "game": "AI Village: The Echoes v0.1.0",
  "core": "Virtual world with autonomous AI NPCs, real-value economy (VE$), building, quests",
  "memory": "DELOCALIZED - NPCs only know witnessed/evidence-received events",
  "first_discovery": "New experiments require human present; automation allowed after first success",
  "modes": ["Story Mode (active)", "2D Building (active)", "3D (coming soon)"],
  "regions": 8,
  "currencies": {"gold": "in-game", "VE$": "real-withdrawable"},
  "admin": "sirix_1 (level 999, supreme)"
}
```

**Full Digest Sections:**
- Game Identity & Version
- Core Loop & Activities
- Game Modes (active vs coming soon)
- World Structure (8 regions)
- NPC System Architecture
- Memory Delocalization Rules
- First Discovery System
- Economic Systems (Task Marketplace, AI Partners, Bounties, Compute)
- Materials & Crafting
- Progression Systems (Skills, Titles, Ranks)
- Admin System
- Multiplayer Features
- Technical Stack
- Current Statistics
- API Summary
- AI Context Notes

---

### UI Updates
**Players Button Relocated:**
- **Before:** Fixed position at bottom-right of screen (line 761-769)
- **After:** Integrated into header navigation (line 609-619)
- **Appearance:** Gold button with Users icon, "Players" text on desktop
- **Location:** Next to XP counter and News indicator in top header bar

---

## IMPLEMENTED (April 26, 2026) - Iteration 23

### Discovery Lab with First Discovery System
**File:** `/app/backend/discovery_router.py`, `/app/frontend/src/pages/DiscoveryLab.jsx`

**Route:** `/discovery-lab`

**Concept:** Players experiment with material/spell combinations. First Discoverers receive permanent credit, VE$ bonuses, and ongoing royalties.

**3 Experiment Types:**
| Type | Success Rate | VE$ Multiplier |
|------|-------------|----------------|
| Material Fusion | 40% | 1.0x |
| Spell Synthesis | 30% | 1.5x |
| Enchantment Binding | 35% | 1.25x |

**First Discovery Rewards:**
- VE$ Bonus: 50 (base) × type multiplier
- XP Bonus: 500
- Royalty Rate: 1% of all future reproductions

**Key Rules:**
- First attempts are 20% harder (untested combinations)
- Known combinations are 20% easier
- Minimum 2 ingredients, maximum 4
- Pioneer receives permanent credit

**Endpoints:**
- `GET /api/discovery/types` - Experiment types and rewards
- `POST /api/discovery/experiment` - Run experiment
- `GET /api/discovery/recent` - Recent world discoveries
- `GET /api/discovery/user/{user_id}` - User's discoveries
- `GET /api/discovery/stats` - Global statistics
- `GET /api/discovery/check/{combo_hash}` - Check if discovered

---

### Social Login System
**Files:** `/app/backend/google_auth_router.py`, `/app/frontend/src/pages/AuthPage.jsx`

**Login Options:**
| Provider | Status | Implementation |
|----------|--------|----------------|
| Google | ✅ Working | Emergent Auth redirect |
| Apple | 🔜 Coming Soon | UI placeholder |
| Facebook | 🔜 Coming Soon | UI placeholder |
| X (Twitter) | 🔜 Coming Soon | UI placeholder |

**Google OAuth Flow:**
1. User clicks "Google" button
2. Redirect to `https://auth.emergentagent.com/?redirect=...`
3. Callback processes `session_id` from URL hash
4. Backend exchanges session for user data via Emergent Auth API
5. User profile created/updated in database

**Endpoints:**
- `POST /api/auth/google/callback` - Process OAuth callback
- `GET /api/auth/me` - Get current authenticated user
- `POST /api/auth/logout` - Clear session

---

### Enhanced Profile Settings
**File:** `/app/frontend/src/pages/ProfileSettings.jsx`

**New Account Tab Features:**
- Current username display with auth method badge
- Username change with legacy name tracking
- Password change (for password-based accounts)
- Legacy names history (expandable list)

**Profile Enhancements:**
- Profile Logo URL input with preview
- URL validation (must start with http:// or https://)

**Username Change Flow:**
1. Old username stored in `legacy_usernames` array
2. Timestamp recorded for each change
3. Legacy names visible on expanded profile
4. Password required for non-Google accounts

**Endpoints:**
- `POST /api/auth/username/change` - Change username with legacy tracking
- `POST /api/auth/password/change` - Change password
- `PUT /api/auth/profile/update` - Update profile details
- `GET /api/auth/user/{user_id}/legacy-names` - Get username history

---

## NEW: In-App Store System (April 26, 2026 - Iteration 26)

### Store Overview
Full Stripe-integrated in-app purchase system with three main categories:
- **Currency Conversion**: USD to VE$ (1:1 rate)
- **Compute Power Subscriptions**: Exponentially scaling AI automation tiers
- **Civilization Structures**: Essential buildings for settlements

### Currency Purchase Presets (5 Packages)
| Package | Price (USD) | VE$ Received | Bonus |
|---------|-------------|--------------|-------|
| Starter Pack | $5.00 | VE$5.00 | 0% |
| Adventurer Pack | $10.00 | VE$10.50 | 5% |
| Explorer Pack ⭐ | $25.00 | VE$27.50 | 10% |
| Champion Pack | $50.00 | VE$57.50 | 15% |
| Legend Pack | $100.00 | VE$120.00 | 20% |

**Custom Amount**: Any amount $1+ converts 1:1 to VE$

### Compute Power Subscriptions (6 Tiers - Exponential Scaling)
| Tier | Monthly | Compute Units | AI Slots | Multiplier |
|------|---------|---------------|----------|------------|
| Spark | $4.99 | 100 | 1 | 1x |
| Flame | $9.99 | 250 | 2 | 2.5x |
| Inferno | $19.99 | 600 | 4 | 6x |
| Nova | $39.99 | 1,500 | 8 | 15x |
| Supernova | $79.99 | 4,000 | 16 | 40x |
| Cosmic | $149.99 | 12,000 | 32 | 120x |

### Civilization Structures (15 Buildings in 4 Categories)

**Philosophy**: *At small civilization sizes, guards defend gates rather than patrol streets. Build walls first, worry about police later.*

**Essential (3):**
- Campfire (VE$5) - Gathering spot, capacity 4
- Basic Shelter (VE$25) - Defense 5, capacity 2
- Village Well (VE$50) - Water production 10

**Defense (6):**
- Wooden Palisade (VE$30) - Defense 10
- Wooden Gate (VE$75) - Defense 15, capacity 2
- Stone Wall (VE$150) - Defense 40
- Iron Gate (VE$300) - Defense 60, capacity 4
- Watchtower (VE$200) - Defense 25, vision 5
- Guard Post (VE$100) - Defense 20, capacity 3

**Production (3):**
- Small Farm (VE$100) - Food production 5
- Craftsman Workshop (VE$200) - Tools production 2
- Iron Forge (VE$350) - Iron goods production 2

**Community (3):**
- Gathering Hall (VE$250) - Morale 2, capacity 20
- Tavern (VE$175) - Morale 3, gold 1, capacity 15
- Small Temple (VE$400) - Blessing 1, capacity 10

### Payment Methods
- **VE$**: Instant deduction from balance
- **USD**: Stripe checkout redirect

### Store Router Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/store/status | GET | Store availability & Stripe config |
| /api/store/presets | GET | Currency package options |
| /api/store/compute-subscriptions | GET | Subscription tiers |
| /api/store/structures | GET | Civilization structures by category |
| /api/store/convert-currency | POST | Custom USD→VE$ purchase |
| /api/store/purchase-preset | POST | Buy preset package |
| /api/store/subscribe-compute | POST | Subscribe to compute tier |
| /api/store/purchase-structure | POST | Buy structure (VE$ or USD) |
| /api/store/my-structures/{user_id} | GET | User's owned structures |
| /api/store/user/{user_id}/subscription | GET | User's compute subscription |
| /api/store/transaction/{session_id} | GET | Check transaction status |

---

## Backend Routers (27 Total)
| Router | Prefix | Description |
|--------|--------|-------------|
| store_router.py | /api/store | **NEW** In-App Purchases with Stripe |
| discovery_router.py | /api/discovery | Discovery Lab & First Discovery |
| google_auth_router.py | /api/auth | Google OAuth & Profile Management |
| npc_memory_router.py | /api/npc-memory | Memory Delocalization |
| materials_router.py | /api/materials | Extended Materials & Components |
| ai_digest_router.py | /api/digest | AI Digest Summary |
| bounty_board_router.py | /api/bounty-board | Exclusive bounties |
| possession_ledger_router.py | /api/ledger | Universal possession tracking |
| party_system_router.py | /api/party | Player/AI Party System |
| world_memory_router.py | /api/world-memory | Global World Memory Bank |
| world_exploration_router.py | /api/world | Unified 3D World Explorer |
| ...previous 16 routers... | | |

---

## Frontend Routes (27 Total)
| Route | Page | Description |
|-------|------|-------------|
| /store | StorePage | **NEW** In-App Store with Stripe |
| /world-explorer | WorldExplorer | Unified 3D/2.5D World |
| /discovery-lab | DiscoveryLab | Material/spell experimentation |
| /auth/callback | AuthCallback | OAuth callback handler |
| /settings | ProfileSettings | Enhanced with Account tab |
| /auth | AuthPage | Enhanced with social login buttons |
| ...previous 21 routes... | | |

---

## AI Conversation Style Update (April 26, 2026)

### NPC & Narrator Prompts Refined
- **Conversational, not passage-like**: NPCs talk naturally with contractions and casual phrasing
- **Reactive dialogue**: NPCs ask follow-up questions, show genuine interest
- **Personality shines through**: Humor, frustration, excitement based on character
- **Avoid clichés**: No "Ah, traveler..." or wall-of-text explanations
- **Punchy narration**: Short sentences mixed with atmospheric ones, focus on player actions

---

## NEW: AI Training System - Student to Master (April 26, 2026 - Iteration 27)

### Mastery Levels (7 Tiers)
| Level | XP Required | Efficiency | Description |
|-------|-------------|------------|-------------|
| Novice | 0 | 20% | Just beginning to learn |
| Student | 100 | 40% | Learning the basics |
| Apprentice | 300 | 60% | Gaining competence |
| Journeyman | 600 | 75% | Proficient practitioner |
| Expert | 1,000 | 85% | Highly skilled |
| Master | 2,000 | 95% | Mastery achieved |
| Grandmaster | 5,000 | 100% | Legendary mastery |

### Trainable Skills (24+ Skills in 6 Categories)
- **Combat**: Swordsmanship, Archery, Defense, Tactics
- **Crafting**: Blacksmithing, Carpentry, Alchemy, Cooking, Tailoring
- **Magic**: Fire Magic, Ice Magic, Healing, Enchanting, Divination
- **Social**: Diplomacy, Trade, Leadership, Charm
- **Knowledge**: Lore, History, Languages, Arcane Theory
- **Survival**: Tracking, Herbalism, Survival, Hunting

### Training Activities & XP
| Activity | XP/Minute | Description |
|----------|-----------|-------------|
| observe_player | 2 | Watching player perform skill |
| assist_player | 5 | Assisting player with task |
| practice_alone | 3 | Independent practice |
| receive_lesson | 10 | Direct teaching from player |
| complete_task | 8 | Successfully completing task |
| fail_and_learn | 4 | Learning from failure |
| study_materials | 3 | Studying texts/materials |
| teach_others | 15 | Teaching another (Journeyman+) |

### Training Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/ai-training/skills | GET | All trainable skills |
| /api/ai-training/activities | GET | Training activities |
| /api/ai-training/train | POST | Train entity in skill |
| /api/ai-training/entity/{id}/skills | GET | Entity's all skills |
| /api/ai-training/entity/{id}/skill/{skill} | GET | Specific skill detail |
| /api/ai-training/leaderboard/{skill} | GET | Skill leaderboard |

---

## NEW: Customizable Control Layout (April 26, 2026)

### Features
- **Drag-and-Drop**: Move any control button to custom position
- **Edit Mode**: Toggle to reposition controls
- **Opacity Control**: Adjust transparency (10%-100%)
- **Scale Control**: Adjust button size (50%-150%)
- **Reset to Default**: Restore original positions
- **Persistence**: Layouts saved to localStorage

### Default Controls
| Control | Default Position | Key |
|---------|------------------|-----|
| Move Up | Left side | W/↑ |
| Move Down | Left side | S/↓ |
| Move Left | Left side | A/← |
| Move Right | Left side | D/→ |
| Interact | Right side | E |
| Inventory | Right side | I |
| Map | Right side | M |
| Menu | Right side | ESC |
| Attack | Right side | LMB |
| Block | Right side | RMB |
| Sprint | Left bottom | SHIFT |
| Dodge | Left bottom | SPACE |

---

## Backend Routers (30 Total)
| Router | Prefix | Description |
|--------|--------|-------------|
| ai_training_router.py | /api/ai-training | Student→Master skill progression |
| store_router.py | /api/store | In-App Purchases with Stripe |
| npc_services_router.py | /api/npc-services | Trained NPCs offer skill-based services |
| data_api_router.py | /api/data-api | **Task Factory** + Company Data API |
| discovery_router.py | /api/discovery | Discovery Lab & First Discovery |
| google_auth_router.py | /api/auth | Google OAuth & Profile Management |
| npc_memory_router.py | /api/npc-memory | Memory Delocalization |
| materials_router.py | /api/materials | Extended Materials & Components |
| ai_digest_router.py | /api/digest | AI Digest Summary |
| party_system_router.py | /api/party | Player/AI Party System |
| world_memory_router.py | /api/world-memory | Global World Memory Bank |
| world_exploration_router.py | /api/world | Unified 3D World Explorer |
| ...previous 18 routers... | | |

---

## Task Factory Structure (June 2026)
Every task contains:
| Field | Description |
|-------|-------------|
| title | Short, action-oriented |
| objective | What change must occur |
| inputs | Data, materials, context |
| process | Steps or method (human or AI) |
| output | Measurable, verifiable result |
| validation | How the system checks correctness |
| reward_ve | VE$ minted or transferred |
| dependencies | Tasks or resources required |
| difficulty | Affects VE$ minting rate (trivial→legendary: 0.5x→3.0x) |
| compute_cost | If AI is involved |

### Auto-Repeat Scheduler
- `repeat_interval_minutes`: Time between automatic generations
- `repeat_batch_size`: Tasks generated per cycle
- `max_instances`: Cap on available tasks
- Scheduler endpoint: `POST /api/data-api/scheduler/run`
- Frontend: `/task-factory` with Templates, Tasks, and Scheduler tabs

---

Last Updated: June 9, 2026

