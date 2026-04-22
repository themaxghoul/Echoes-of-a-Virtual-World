# AI Village: The Echoes - Production Ready PRD
## Pre-Release for itch.io

## Overview
A virtual world storytelling experience where AI companions learn and evolve through player interactions. Features real-world monetization (ApexForge Collective), dynamic world events, a **persistent memory system**, and **full AI autonomy** where NPCs can make decisions, converse with each other, and shape the world.

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
- **ALL MAPS OPEN** - No progression locks for exploration
- Chat with NPCs, build your 2D world
- Skills gain XP through actions
- AI remembers past conversations

### 2. First Person 3D (Web)
- Immersive 3D experience in browser
- D-Pad controls
- Camera drag navigation
- 3D interactable models and NPCs

### 3. Unity 3D
- High-fidelity Unity client download
- Cross-platform sync between web and Unity
- Download from itch.io: https://aivillage.itch.io/echoes-unity

---

## P0 SYSTEMS (NEW - April 2026)

### 1. Skills System (`/api/skill-system/*`)
**6 Categories, 30 Skills:**
| Category | Skills | Color |
|----------|--------|-------|
| Combat | Swordsmanship, Archery, Defense, Tactics, Berserker | Red |
| Magic | Elemental, Healing, Enchanting, Divination, Shadow | Purple |
| Crafting | Blacksmithing, Alchemy, Woodworking, Tailoring, Engineering | Amber |
| Gathering | Mining, Herbalism, Hunting, Fishing, Foraging | Green |
| Social | Diplomacy, Trading, Leadership, Intimidation, Charm | Blue |
| Knowledge | Lore, Languages, Investigation, Arcana, Nature | Indigo |

**Skill XP Gains from Actions:**
- `attack_melee` → Swordsmanship (1-5 XP)
- `cast_elemental` → Elemental Magic (2-8 XP)
- `forge_item` → Blacksmithing (3-10 XP)
- `conversation` → Charm (1-3 XP)
- `build_structure` → Engineering (10-30 XP)
- ...25+ action mappings

### 2. Titles System (31 Titles)
Titles provide stat boosts when active:
| Title | Requirement | Boosts |
|-------|-------------|--------|
| Sword Saint | Swordsmanship Lv.100 | +10 STR, +5 AGI, +5 END, +3 WIS |
| Archmage | Elemental Lv.100 | +10 INT, +8 WIS, +50 Mana |
| Legendary Forger | Blacksmithing Lv.100 | +8 STR, +30% Crafting |
| The Omniscient | Lore Lv.100 | +15 INT, +15 WIS, +10 PER |
| World Shaper | 100 World Edits | +3 All Stats, +25% Building |
| Transcendent | 5 Max Skills | +10 All Stats |

### 3. Entity Earnings (VE$ for Players AND AI)
**18 Earning Activities:**
- `quest_completed` - $0.50/quest (max 20/day)
- `trade_completed` - $0.05/trade (max 100/day)
- `structure_built` - $1.00/build (max 10/day)
- `data_labeled` - $0.01/label (max 500/day)
- `conversation_value` - $0.01/convo (AI only, max 200/day)
- `world_improvement` - $0.25/improve (AI only, max 20/day)

**Reputation Tiers (Multipliers):**
- Newcomer: 1.0x
- Established: 1.1x (earned $10+)
- Respected: 1.25x (earned $100+)
- Renowned: 1.5x (earned $1000+)
- Legendary: 2.0x (earned $10000+)

### 4. AI Autonomy System (`/api/ai-autonomy/*`)
**Personality Traits:**
- Cooperative, Aggressive, Curious, Creative
- Social, Territorial, Mercantile, Spiritual

**Free Will (0-1 scale):**
- Controls how autonomous NPCs are
- Higher = more likely to take independent actions

**Autonomous Actions:**
- `initiate_conversation` - Talk to other NPCs
- `form_alliance` / `break_alliance`
- `start_conflict` / `resolve_conflict`
- `build_structure` / `destroy_structure`
- `modify_terrain` / `create_landmark`
- `establish_trade_route`
- `claim_territory` / `relocate`
- ...20+ autonomous actions

**AI-to-AI Conversations:**
```
POST /api/ai-autonomy/conversation/start
POST /api/ai-autonomy/conversation/{id}/continue
```

---

## World Instances (`/api/worlds/*`)

### World Types
| Type | Description | Max NPCs |
|------|-------------|----------|
| Private | Personal realm (owner only) | 10 |
| Shared | Multi-player accessible | 50 |
| Story | Main story with original characters | 100 |
| Instance | Temporary event/quest world | 20 |

### Sirix-1 Private Realm
- **Exclusive access** - Only sirix_1 can enter
- Fixed seed for consistent world
- Personal NPCs and structures
- Endpoint: `GET /api/worlds/sirix-1/realm?user_id=sirix_1`

### Main Story World
**8 Original Characters:**
1. Elder Morvain (Village Elder) - Village Square
2. Lyra the Wanderer (Explorer) - Village Square
3. Oracle Veythra (Seer) - Oracle Sanctum
4. Kael Ironbrand (Blacksmith) - The Forge
5. Archivist Nyx (Lorekeeper) - Ancient Library
6. Innkeeper Mara (Tavern Owner) - Wanderer's Rest
7. The Grove Keeper (Forest Guardian) - Shadow Grove
8. Sentinel Theron (Watchtower Guard) - Watchtower

---

## Chat History & Resume
- View past dialogues grouped by NPC or Date
- Search through conversation messages
- Resume conversations from where you left off
- Unlimited message storage

---

## Jobs & Career System (21 Jobs)
- Task Work: Data Labeler, Transcriber, Survey Specialist
- AI Training: AI Trainer, Feedback Analyst
- Commerce: Merchant, Resource Broker
- Construction: Builder, Infrastructure Engineer
- ...and more categories

---

## Persistent Memory System
### Memory Types
- User memories: interactions, preferences, achievements
- AI memories: learned behaviors, player models, predictions
- Memory decay rates control how long memories persist

---

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB (motor async driver)
- **AI**: GPT-5.2 via Emergent Integrations
- **Payments**: Stripe via emergentintegrations

---

## Backend Routers (15 Total)
| Router | Prefix | Description |
|--------|--------|-------------|
| server.py | /api | Core routes (~6800 lines) |
| skills_router.py | /api/skill-system | Skills & Titles |
| ai_autonomy_router.py | /api/ai-autonomy | AI-to-AI, Free Will |
| world_instances_router.py | /api/worlds | Private/Story worlds |
| entity_earnings_router.py | /api/entity-earnings | VE$ for all entities |
| conversation_history_router.py | /api/conversations | Chat logs & resume |
| jobs_router.py | /api/jobs | Career system |
| unity_router.py | /api/unity | Unity offload |
| memory_router.py | /api/memory | Persistent memory |
| ai_chat_router.py | /api/chat | AI conversations |
| world_engine_router.py | /api/world-engine | Dynamic events |
| ...others | | |

---

## Completed Features
- [x] Skills system (6 categories, 30 skills)
- [x] Titles system (31 titles with stat boosts)
- [x] Entity earnings (VE$ for players AND AI)
- [x] AI autonomy (free will, AI-to-AI conversations)
- [x] World instances (private, shared, story)
- [x] Sirix-1 exclusive private realm
- [x] Chat history with resume
- [x] Jobs & Career system
- [x] Unity offload support
- [x] All maps open in Story Mode
- [x] Persistent memory system
- [x] World Engine (bosses, factions, events)

---

## Upcoming P1 Features
- [ ] Top-down stylized world map view
- [ ] Multiplayer 3D environment with consistent seed
- [ ] 2D Building interface for Story Mode
- [ ] Real micro-task provider connections

## P2 Backlog
- [ ] NPC cloud gaming emulation
- [ ] Voice input/output for VR
- [ ] WebGL Unity build

---
Last Updated: April 22, 2026
