# AI Village: The Echoes - Production Ready PRD
## Pre-Release for itch.io

## Overview
A virtual world storytelling experience where AI companions learn and evolve through player interactions. Features real-world monetization (ApexForge Collective) and dynamic world events driven by AI.

## Deployment: READY FOR ITCH.IO PRE-RELEASE

### Key Systems

#### 1. AI World Engine (NEW - Dynamic World)
The World Engine enables NPCs and AI to commit real actions that change the game world:

**World Bosses (5 types)**
| Boss | HP | Diplomatic? | Demands |
|------|-----|-------------|---------|
| Malachar the Shadow Lord | 5000 | No | - |
| Azrael, Prince of Flames | 4000 | Yes | souls, territory, artifacts |
| Vyrmathax the Eternal | 8000 | Yes | knowledge, respect, treasure |
| Netharis the Undying | 3500 | Yes | corpses, dark knowledge, souls |
| Goldric the Magnificent | 2000 | Yes | trade rights, monopoly, tribute |

**Diplomatic Factions (5)**
- Village Council (lawful_good) - Elder Morin
- Cult of the Void (chaotic_evil) - High Priest Vex
- Merchant's Consortium (true_neutral) - Guildmaster Helena
- Legions of the Abyss (chaotic_evil) - Archdemon Bael
- Circle of Echoes (lawful_neutral) - Archmage Seraphina

**Dynamic Events (15 types)**
- Boss Spawn, Invasion, Diplomatic Crisis, Resource Discovery
- Plague, Festival, Merchant Caravan, Natural Disaster
- Prophecy, Rebellion, Alliance Offer, War Declaration
- Mysterious Stranger, Artifact Appearance, Portal Opening

**World State Variables**
- Chaos Level (0-100): Affects spawn rates
- Prosperity Level (0-100): Affects prices and NPC moods
- Danger Level (0-100): Affects demon spawns

#### 2. AI Chat System (Isolated & Context-Aware)
NPCs can understand world context and trigger actions:

**AI Action Tags**
- `[MOOD:happy/angry/fearful]` - Change emotional state
- `[QUEST:description]` - Create a quest for players
- `[RUMOR:text]` - Spread rumors through the village
- `[PROPHECY:text]` - Oracle-only divine visions
- `[RELATION:+10/-5]` - Modify relationship with player
- `[TRADE]` - Open trade interface

**Context Integration**
- Location details and atmosphere
- Nearby NPCs and players
- Active world events and bosses
- Recent rumors and prophecies
- Character state and quests

#### 3. Earnings Hub (VE$ Currency)
Real-world monetization tied 1:1 to USD:
- 7 Task Providers (Toloka, Appen, etc.)
- Stripe Deposits (Buy VE$ with card)
- $0.25 Withdrawal Fee
- MetaMask Web3 Integration

#### 4. Ecosystem Support System
Players contribute to AI evolution:
- 7 Technology Tiers (Primitive → Transcendent)
- 7 AI Intelligence Levels (Dormant → Transcendent)
- 11 Contribution Actions

## API Endpoints (100+ Total)

### World Engine Endpoints (NEW)
```
GET  /api/world-engine/state           - Current world state
GET  /api/world-engine/bosses          - Available bosses
GET  /api/world-engine/factions        - Faction details
GET  /api/world-engine/events/active   - Active events
POST /api/world-engine/spawn-boss      - Spawn a boss
POST /api/world-engine/attack-boss/{id} - Attack boss
POST /api/world-engine/negotiate-boss/{id} - Negotiate
POST /api/world-engine/diplomatic-action - Faction diplomacy
POST /api/world-engine/create-event    - Create event
POST /api/world-engine/trigger-random-event - Random event
```

### AI Chat Endpoints (NEW)
```
POST /api/ai-chat/chat                 - Chat with NPC
POST /api/ai-chat/narrator             - Narrator descriptions
GET  /api/ai-chat/context/{loc}/{char} - World context
GET  /api/ai-chat/conversation/{id}    - Conversation history
POST /api/ai-chat/npc-autonomous-action - NPC autonomous action
```

### Earnings Endpoints
```
GET  /api/payments/packages            - Payout packages
POST /api/payments/deposit/checkout    - Stripe deposit
POST /api/payments/withdraw/initiate   - Initiate withdrawal
GET  /api/payments/balance/{user_id}   - VE$ balance
```

### Ecosystem Endpoints
```
GET  /api/ecosystem/status             - Current tier & AI level
POST /api/ecosystem/contribute         - Submit contribution
POST /api/ecosystem/support            - Direct VE$ support
GET  /api/ecosystem/user/{user_id}     - User contributions
GET  /api/ecosystem/leaderboard        - Top contributors
```

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB (motor async driver)
- **AI**: GPT-5.2 via Emergent Integrations
- **Payments**: Stripe via emergentintegrations
- **Web3**: MetaMask wallet integration
- **PWA**: Service Worker, offline support

## Backend Architecture (Modularized)
```
/app/backend/
├── server.py                    # Core server (6700 lines - being refactored)
├── config/
│   ├── database.py              # DB connection
│   └── constants.py             # Game constants
├── world_engine_router.py       # Dynamic events, bosses, diplomacy
├── ai_chat_router.py            # Isolated AI chat system
├── earnings_router.py           # VE$ income streams
├── stripe_payout_router.py      # Deposits & withdrawals
├── ecosystem_support_router.py  # Tech tiers & AI evolution
├── task_providers_router.py     # Micro-task providers
├── npc_gaming_router.py         # NPC game emulation
```

## Frontend Routes (15)
- `/` - Landing
- `/auth` - Login
- `/create-character` - Character creation
- `/select-mode` - Mode selection
- `/village` - Text explorer
- `/play` - First person 3D view
- `/dataspace` - AI memory visualization
- `/quests` - Quest board
- `/profile` - User profile
- `/building` - Building system
- `/trading` - Trading system
- `/guilds` - Guild management
- `/inventory` - Equipment
- `/earnings` - Earnings Hub

## itch.io Pre-Release Checklist
- [x] AI Chat with world context integration
- [x] Dynamic boss spawning and combat
- [x] Diplomatic faction system
- [x] World events (15 types)
- [x] VE$ earnings system
- [x] Stripe payment integration
- [x] Ecosystem support system
- [x] PWA deployment ready
- [x] First Person 3D view
- [x] Multiplayer chat

## Immediate Priorities
- [ ] Frontend integration of World Engine UI
- [ ] Boss encounter UI component
- [ ] Diplomatic negotiation interface
- [ ] Event notification system

## Future Roadmap
- P1: Complete server.py refactoring
- P1: Real task provider API connections
- P2: Voice input/output for VR
- P2: Mount system for travel
- P3: More demon types and boss encounters
- P3: Cross-server guild wars

---
Last Updated: April 21, 2026
