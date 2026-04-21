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

## Persistent Memory System (NEW)

The foundation for AI learning and ecosystem growth.

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

#### Ecosystem Memories
| Type | Description |
|------|-------------|
| eco_world_event | Major world events |
| eco_collective | Collective player patterns |
| eco_evolution | AI evolution milestones |
| eco_cultural | Emerging cultural patterns |

### Memory Importance Levels
- **Trivial** (1-2): May be forgotten quickly
- **Minor** (3-4): Weak retention
- **Moderate** (5-6): Standard retention
- **Significant** (7-8): Strong retention
- **Critical** (9-10): Never forgotten

### Player Models
AI builds understanding of each player:
- Play style (aggressive, diplomatic, explorer, builder)
- Decision patterns
- Preferred locations
- Favorite NPCs
- Trust level (0-1)
- Emotional tendencies
- Interaction history

### AI Evolution Tracking
Each AI tracks its growth:
- Total memories
- Unique players met
- Conversations had
- Knowledge domains
- Language sophistication (1-10)
- Emotional intelligence (1-10)
- World awareness (1-10)
- Prediction accuracy (0-1)

### Memory API Endpoints
```
POST /api/memory/create              - Create new memory
POST /api/memory/recall              - Query memories
POST /api/memory/reinforce/{id}      - Strengthen memory
POST /api/memory/associate           - Link memories
GET  /api/memory/entity/{type}/{id}  - Get entity memories
GET  /api/memory/stats               - System statistics
POST /api/memory/player-model/update - Update player model
GET  /api/memory/player-model/{ai}/{player} - Get AI's player model
GET  /api/memory/ai-evolution/{id}   - Get AI evolution state
POST /api/memory/maintenance/decay   - Apply memory decay
POST /api/memory/synthesize-context/{type}/{id} - Generate context
```

---

## Core Game Modes

### Story Mode (2D Chat Adventure)
- Text-based adventure with AI narrator
- **2D World Building** 
- Chat with NPCs
- Location progression
- **AI remembers past conversations**

### First Person 3D Mode
- Immersive 3D experience
- **3D Interactable Models**
- D-Pad controls
- Camera drag
- **AI uses memories for personalized interactions**

---

## Authentication System
- Username + Password (bcrypt hashed)
- Login tracking with stats
- Sirix-1 secured with dedicated password
- Stats tracked: logins, quests, NPCs talked

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

## AI Chat System

NPCs use persistent memories to:
- Remember past conversations with players
- Build trust/distrust based on interactions
- Personalize responses based on player model
- Create memories of significant moments
- Evolve their understanding over time

### AI Action Tags
- `[MOOD:]` - Change emotional state
- `[QUEST:]` - Create quests
- `[RUMOR:]` - Spread rumors
- `[PROPHECY:]` - Oracle visions
- `[RELATION:]` - Modify relationships

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
| server.py | Core routes (6700+ lines) |
| memory_router.py | **NEW** Persistent memory system |
| ai_chat_router.py | AI conversations with memory |
| world_engine_router.py | Dynamic events, bosses |
| ecosystem_support_router.py | Tech tiers, AI evolution |
| earnings_router.py | VE$ income |
| stripe_payout_router.py | Deposits/withdrawals |
| task_providers_router.py | Micro-tasks |
| npc_gaming_router.py | NPC game emulation |

---

## Completed Features
- [x] Sirix-1 password secured (HCLynnTV04)
- [x] Persistent memory system for users
- [x] Persistent memory system for AI
- [x] AI player modeling
- [x] AI evolution tracking
- [x] Memory integration in chat
- [x] Back navigation on all screens
- [x] Story Mode vs First Person 3D
- [x] World Engine
- [x] VE$ earnings system
- [x] PWA deployment ready

---

## Immediate Priorities
- [ ] 2D Building interface for Story Mode
- [ ] Memory visualization UI (show AI memories to players)
- [ ] Ecosystem dashboard showing collective AI evolution

## Future Roadmap
- P1: Complete server.py refactoring
- P1: Real task provider API connections
- P2: Voice input/output for VR
- P2: Cross-game AI memory persistence

---
Last Updated: April 21, 2026
