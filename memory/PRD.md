# AI Village: The Echoes - Production Ready PRD
## Pre-Release for itch.io

## Overview
A virtual world storytelling experience where AI companions learn and evolve through player interactions. Features real-world monetization (ApexForge Collective) and dynamic world events driven by AI.

## Deployment: READY FOR ITCH.IO PRE-RELEASE

### Core Game Modes

#### 1. Story Mode (2D Chat Adventure)
- Text-based adventure with AI narrator
- **2D World Building** - Players can build structures in their 2D world
- Chat with NPCs, shape the narrative
- Location progression with unlockable areas
- No 3D vessels - pure text/chat experience

#### 2. First Person 3D Mode
- Immersive 3D experience with CSS perspective
- **3D Interactable Models** - Walk through the village
- D-Pad controls for movement
- Camera drag for looking around
- Full 3D vessel for player representation

### Authentication System

#### Dedicated Login with Stats Tracking
- Username + Password authentication
- bcrypt password hashing
- Login tracking with session stats
- Sirix-1 admin account with transcendent stats

#### User Stats Tracked
- Total logins
- Quests completed
- NPCs talked to
- Demons defeated
- Buildings placed
- Trades completed
- Gold/VE$ earned

### Navigation System

#### Back Button Support
- All screens have back navigation (← arrow)
- Users can exit screens accidentally clicked
- Navigation history tracking
- Fallback paths for all routes

#### Navigation Paths
```
Auth → Mode Selection → Story Mode / 3D Mode → Sub-pages
         ↓
    Quick Access: Builder, Trading, Earnings, Quests
```

### World Engine (Dynamic Events)

**World Bosses (5 types)**
| Boss | HP | Diplomatic? | Demands |
|------|-----|-------------|---------|
| Malachar the Shadow Lord | 5000 | No | - |
| Azrael, Prince of Flames | 4000 | Yes | souls, territory, artifacts |
| Vyrmathax the Eternal | 8000 | Yes | knowledge, respect, treasure |
| Netharis the Undying | 3500 | Yes | corpses, dark knowledge, souls |
| Goldric the Magnificent | 2000 | Yes | trade rights, monopoly, tribute |

**Diplomatic Factions (5)**
- Village Council (lawful_good)
- Cult of the Void (chaotic_evil)
- Merchant's Consortium (true_neutral)
- Legions of the Abyss (chaotic_evil)
- Circle of Echoes (lawful_neutral)

**Dynamic Events (15 types)**
Boss Spawn, Invasion, Diplomatic Crisis, Resource Discovery, Plague, Festival, Merchant Caravan, Natural Disaster, Prophecy, Rebellion, Alliance Offer, War Declaration, Mysterious Stranger, Artifact Appearance, Portal Opening

### AI Chat System

NPCs can understand context and trigger world actions:

**AI Action Tags**
- `[MOOD:]` - Change emotional state
- `[QUEST:]` - Create quests for players
- `[RUMOR:]` - Spread rumors
- `[PROPHECY:]` - Oracle visions
- `[RELATION:]` - Modify relationships

### Earnings Hub (VE$ Currency)
- 7 Task Providers
- Stripe Deposits (Buy VE$ with card)
- $0.25 Withdrawal Fee
- MetaMask Web3 Integration
- 1:1 USD to VE$ ratio

### Key Routes
| Route | Mode | Description |
|-------|------|-------------|
| `/auth` | - | Login/Register with password |
| `/select-mode` | - | Choose Story/3D mode |
| `/village` | Story | 2D chat adventure |
| `/play` | 3D | First person 3D view |
| `/building` | Story | 2D builder |
| `/earnings` | - | VE$ monetization |
| `/quests` | Both | Quest board |
| `/profile` | Both | User profile |

### API Endpoints (100+ Total)

#### Auth Endpoints
```
POST /api/auth/login      - Login with password
POST /api/auth/register   - Create account
POST /api/users/track-login - Track login stats
GET  /api/users/stats/{id}  - Get user stats
```

#### World Engine
```
GET  /api/world-engine/state
POST /api/world-engine/spawn-boss
POST /api/world-engine/diplomatic-action
POST /api/world-engine/create-event
```

#### AI Chat
```
POST /api/ai-chat/chat
POST /api/ai-chat/narrator
GET  /api/ai-chat/context/{loc}/{char}
```

### Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB (motor async driver)
- **AI**: GPT-5.2 via Emergent Integrations
- **Payments**: Stripe via emergentintegrations
- **Auth**: bcrypt password hashing
- **Web3**: MetaMask wallet integration
- **PWA**: Service Worker, offline support

### Test Credentials
- **Sirix-1 Admin**: `sirix_1` / `k3bdp0wn!0nr(?8vd&74v2l!`

### Completed Features
- [x] Password authentication with stats tracking
- [x] Back navigation on all screens
- [x] Story Mode (2D chat + building)
- [x] First Person 3D Mode (3D models)
- [x] Mode selection with clear differentiation
- [x] World Engine (bosses, events, diplomacy)
- [x] AI Chat with context integration
- [x] VE$ earnings system
- [x] PWA deployment ready

### Immediate Priorities
- [ ] Frontend UI for boss encounters
- [ ] 2D Building interface for Story Mode
- [ ] Event notification popups

### Future Roadmap
- P1: Complete server.py refactoring
- P1: Real task provider API connections
- P2: Voice input/output for VR
- P2: Mount system for travel

---
Last Updated: April 21, 2026
