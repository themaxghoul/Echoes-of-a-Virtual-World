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

---

## Remaining Tasks
- [ ] World Map UI (frontend visualization)
- [ ] Building UI (frontend grid placement)
- [ ] Task Marketplace UI (frontend task listing)
- [ ] Real micro-task provider API connections

---
Last Updated: April 22, 2026
