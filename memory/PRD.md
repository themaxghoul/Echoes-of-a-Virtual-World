# AI Village: The Echoes - Production Ready PRD
## Pre-Release for itch.io

## Overview
A virtual world storytelling experience where AI companions learn and evolve through player interactions. Features real-world monetization (ApexForge Collective), dynamic world events, and a **persistent memory system** that enables AI learning and ecosystem growth.

## Deployment: READY FOR ITCH.IO PRE-RELEASE

### Sirix-1 Admin Account
- Username: `sirix_1`
- Password: `HCLynnTV04` (SECURED - do not share publicly)
- Permissions: Transcendent (infinite stats, all access)

---

## Game Modes (3 Options)

### 1. Story Mode (2D Chat Adventure)
- Text-based adventure with AI narrator
- **ALL MAPS OPEN** - No progression locks for exploration
- Chat with NPCs, build your 2D world
- Location progression awards XP but doesn't gate content
- AI remembers past conversations

### 2. First Person 3D (Web)
- Immersive 3D experience in browser
- D-Pad controls
- Camera drag navigation
- 3D interactable models and NPCs
- AI uses memories for personalized interactions

### 3. Unity 3D (NEW - April 2026)
- High-fidelity Unity client download
- Cross-platform sync between web and Unity
- Full gamepad and keyboard support
- Real-time combat system with AI enemies
- Download from itch.io: https://aivillage.itch.io/echoes-unity
- Supported platforms: Windows, macOS, Linux

---

## Unity Offload System (NEW)

### Features
- **Cross-Platform Sync**: Progress syncs between web and Unity
- **Session Tokens**: Secure authentication between platforms
- **State Management**: Character, inventory, world position sync
- **Heartbeat System**: Keep-alive for active sessions

### API Endpoints
```
GET  /api/unity/config                    - Server configuration
GET  /api/unity/downloads                 - Download links
POST /api/unity/session                   - Create session token
POST /api/unity/session/{id}/connect      - Mark session connected
POST /api/unity/session/{id}/disconnect   - Mark session disconnected
GET  /api/unity/session/{id}/state        - Get current state
POST /api/unity/sync                      - Sync state from Unity
POST /api/unity/heartbeat/{id}            - Keep-alive
GET  /api/unity/stats                     - Platform statistics
```

---

## Persistent Memory System

### Memory Types

#### User Memories
| Type | Description | Decay Rate |
|------|-------------|------------|
| user_interaction | Conversations with NPCs | 0.02 |
| user_preference | Play style, choices | 0.02 |
| user_achievement | Milestones | 0.01 (slow) |
| user_relationship | NPC relationships | 0.01 |
| user_knowledge | Discovered information | 0.02 |
| user_emotion | Emotional reactions | 0.05 |

#### AI Memories
| Type | Description | Decay Rate |
|------|-------------|------------|
| ai_learned_behavior | Patterns from interactions | 0.01 |
| ai_world_knowledge | World state awareness | 0.005 |
| ai_player_model | Understanding of players | 0.005 (very slow) |
| ai_conversation | Important conversations | 0.01 |
| ai_relationship | Relationships with players | 0.005 |
| ai_prediction | Behavioral predictions | 0.02 |

### Memory API Endpoints
```
POST /api/memory/create              - Create new memory
POST /api/memory/recall              - Query memories
POST /api/memory/reinforce/{id}      - Strengthen memory
POST /api/memory/associate           - Link memories
GET  /api/memory/entity/{type}/{id}  - Get entity memories
```

---

## Jobs & Career System (NEW)

### Job Categories (21 Jobs Total)
1. **Task Work**: Data Labeler, Transcriber, Survey Specialist
2. **AI Training**: AI Trainer, Feedback Analyst
3. **Commerce**: Merchant, Resource Broker
4. **Construction**: Builder, Infrastructure Engineer
5. **Exploration**: Explorer, Resource Gatherer
6. **Diplomacy**: Diplomat, Faction Liaison
7. **Scholarship**: Scholar, Lorekeeper
8. **Combat**: Guardian, Demon Hunter
9. **Crafting**: Crafter, Enchanter
10. **Mysticism**: Oracle Apprentice, Ritual Master

### Job Features
- VE$ hourly earnings
- Ecosystem points per hour
- AI benefit descriptions
- Level progression with titles
- Work sessions with real-time earnings

### API Endpoints
```
GET  /api/jobs/catalog               - All available jobs
GET  /api/jobs/details/{key}         - Job details
POST /api/jobs/enroll                - Enroll in job
GET  /api/jobs/player/{id}           - Player's jobs
POST /api/jobs/start-work-session    - Start working
POST /api/jobs/end-work-session/{id} - End session, get earnings
GET  /api/jobs/economy-stats         - Overall economy stats
```

---

## World Engine

### World Bosses (5)
- Malachar the Shadow Lord (5000 HP)
- Azrael, Prince of Flames (4000 HP)
- Vyrmathax the Eternal (8000 HP)
- Netharis the Undying (3500 HP)
- Goldric the Magnificent (2000 HP)

### Diplomatic Factions (5)
- Village Council
- Cult of the Void
- Merchant's Consortium
- Legions of the Abyss
- Circle of Echoes

### Dynamic Events (15 types)
Boss Spawn, Invasion, Diplomatic Crisis, Resource Discovery, Plague, Festival, Merchant Caravan, Natural Disaster, Prophecy, Rebellion, Alliance Offer, War Declaration, Mysterious Stranger, Artifact Appearance, Portal Opening

---

## Earnings Hub (VE$ Currency)
- 7 Task Providers
- Stripe Deposits
- $0.25 Withdrawal Fee
- MetaMask Web3 Integration
- 1:1 USD to VE$ ratio

---

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB (motor async driver)
- **AI**: GPT-5.2 via Emergent Integrations
- **Payments**: Stripe via emergentintegrations
- **Auth**: bcrypt password hashing
- **Web3**: MetaMask wallet integration
- **PWA**: Service Worker, offline support

---

## Backend Routers
| Router | Description |
|--------|-------------|
| server.py | Core routes (~6700+ lines) |
| memory_router.py | Persistent memory system |
| ai_chat_router.py | AI conversations with memory |
| world_engine_router.py | Dynamic events, bosses |
| ecosystem_support_router.py | Tech tiers, AI evolution |
| earnings_router.py | VE$ income |
| stripe_payout_router.py | Deposits/withdrawals |
| task_providers_router.py | Micro-tasks |
| npc_gaming_router.py | NPC game emulation |
| jobs_router.py | Career system (NEW) |
| unity_router.py | Unity offload (NEW) |

---

## Completed Features
- [x] Sirix-1 password secured (HCLynnTV04)
- [x] Persistent memory system for users
- [x] Persistent memory system for AI
- [x] AI player modeling
- [x] AI evolution tracking
- [x] Memory integration in chat
- [x] Back navigation on all screens
- [x] Story Mode vs First Person 3D vs Unity 3D (3 modes)
- [x] All maps open in Story/Chat mode (NEW)
- [x] Unity offload system (NEW)
- [x] Jobs & Career system (NEW)
- [x] World Engine
- [x] VE$ earnings system
- [x] PWA deployment ready

---

## Immediate Priorities
- [ ] 2D Building interface for Story Mode
- [ ] Memory visualization UI (show AI memories to players)
- [ ] Real Unity client WebSocket integration

## Future Roadmap
- P1: Complete server.py refactoring
- P1: Real task provider API connections
- P2: Voice input/output for VR
- P2: Cross-game AI memory persistence
- P2: WebGL Unity build

---
Last Updated: April 22, 2026
