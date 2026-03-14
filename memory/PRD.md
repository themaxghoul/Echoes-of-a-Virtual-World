# AI Village: The Echoes - PRD

## Original Problem Statement
Build an AI Village storytelling experience where users interact with AI companions in a dynamic world. The AI learns alongside users with different day-to-day tasks, learning how to be a companion rather than a tool, and building a virtual world for future VR Full-Dive interface.

## User Personas
1. **Storytelling Enthusiasts** - Users who want immersive narrative experiences
2. **Gamers** - Players looking for AI-driven interactive fiction
3. **Future VR Adopters** - Early adopters building towards Full-Dive experiences
4. **AI Curious** - Users interested in AI companions vs tools

## Core Requirements (Static)
- Interactive story dialogue with AI companion
- Character creation/customization
- Village exploration with location-based interactions
- Global dataspace for AI learning/memory
- Conversation history persistence
- Dark fantasy immersive UI
- AI villagers with professions who can trade and have daily lives
- World expansion through travel and building

## What's Been Implemented

### Phase 1 - MVP Complete (Jan 2026)
- [x] Landing page with immersive dark fantasy entry
- [x] Character creation (name, background, traits, appearance)
- [x] Village Explorer with 7 unique locations
- [x] AI storyteller chat using GPT-5.2 via Emergent LLM
- [x] Location navigation with atmosphere descriptions
- [x] Global Dataspace page with memory visualization
- [x] Conversation persistence in MongoDB
- [x] Character persistence per user

### Phase 1.5 - Progression & NPC System (Jan 2026)
- [x] Fixed sidebar visibility bug
- [x] NPC visual appearances with avatar images
- [x] Milestone-based world progression (6 milestones)
- [x] XP system (+10 conversations, +20 new locations)
- [x] Locked/unlocked location system
- [x] Per-location background images
- [x] XP progress bar in sidebar

### Phase 2.0 - Multiplayer & AI Expansion (Jan 2026)
- [x] **Oracle Veythra** - Special NPC who sees real-world news as prophecies
- [x] **Sirix-1 Supreme Account** - Immutable user with max permissions
- [x] **User Profile System** - Persistent profiles across characters with resources
- [x] **Permission Tiers**: Basic → Advanced → Admin → Sirix-1
- [x] **Quest System** - NPCs and players can create quests with resource payouts
- [x] **NPC Location Stamps** - Each NPC has home + visitable locations
- [x] **WebSocket Multiplayer** - Real-time chat infrastructure
- [x] **8 NPCs initialized** with personalities, roles, and knowledge domains

### Phase 2.5 - First Person & Auth System (Jan 2026)
- [x] **Login/Register Auth Page** - Username-based authentication
- [x] **Mode Selection Screen** - Choose First Person or Story Mode
- [x] **First Person View** - Full game view with location rendering
- [x] **D-Pad/Joystick Controls** - Movement UI (static)
- [x] **Interact Button** - For doors, NPCs, and objects
- [x] **Pause Menu** - Access to chat, quests, profile, settings
- [x] **Official Rankings** - City/State/Country tiers (13 ranks)
- [x] **Standing System** - Reputation-based (Outcast → Legendary)
- [x] **Chat Channels by Rank** - Local/City/State/Country/Global access

### Phase 3.0 - Building & Trading System (Mar 2026)
- [x] **Building Materials** - 5 types (wood, stone, iron, crystal, obsidian) with stats
- [x] **Building Schematics** - 19 schematics across 4 tiers
- [x] **Build Endpoint** - Players can build structures (ObjectId fix applied)
- [x] **Trading System** - Players can create/accept trade offers (ObjectId fix applied)
- [x] **Contribution Points** - Earn points by building, unlock schematics
- [x] **Reward Types** - Materials, gold, XP, contribution rewards

### Phase 3.5 - AI Professions & World Expansion (Mar 2026)
- [x] **18 AI Professions** across 7 tiers:
  - Commoner: serf, farmer
  - Craftsman: chef, miner, blacksmith, butcher, carpenter
  - Warrior: swordsman, archer, knight
  - Scholar: scribe, alchemist
  - Mystic: court_mage, priest
  - Noble: merchant, baron
  - Leadership: guildmaster, captain
- [x] **12 Starter AI Villagers** - Auto-initialized on startup with unique personalities
- [x] **Villager Daily Work** - Produce resources based on profession, consume needs
- [x] **Villager-to-Villager Trading** - AIs can trade with each other
- [x] **Villager-to-Player Trading** - AIs can trade with players
- [x] **World Seedling System** - Origin village "The First Echo"
- [x] **5 Discoverable Lands**:
  - Eastern Plains (travel)
  - Northern Mountains (travel)
  - Western Forest (travel)
  - Southern Coast (travel)
  - Underground Realm (requires building)
- [x] **5 House Types**: campsite, cottage, house, manor, guild_hall
- [x] **Land Discovery Mechanic** - Travel distance or building requirements
- [x] **House Building** - Players can build houses in discovered lands
- [x] **Villager Housing** - Assign villagers to live in player houses

## Tech Stack
- Frontend: React + Tailwind CSS + Shadcn/UI
- Backend: FastAPI + MongoDB (motor async driver)
- AI: OpenAI GPT-5.2 via Emergent Integrations
- Theme: "The Void & The Flame" dark fantasy

## Prioritized Backlog

### P0 (Next Sprint)
- [ ] Make D-pad/joystick functional with actual movement
- [ ] Implement multiplayer chat UI (WebSocket endpoint exists)
- [ ] Hierarchical chat access UI based on official rankings

### P1 (Near Future)
- [ ] Travel distance tracking for land discovery
- [ ] AI villager personality/mood system
- [ ] NPC relationship tracking with affinity meters
- [ ] Dynamic NPC dialogue based on relationship

### P2 (Future)
- [ ] Multiple character support per user
- [ ] Save/load game states
- [ ] Inventory UI system
- [ ] Guild formation and management

### P3 (VR Phase)
- [ ] Voice input/output integration
- [ ] 3D environment rendering
- [ ] VR controller integration
- [ ] Full-Dive interface prep
- [ ] Spatial audio for immersion

## API Endpoints Summary

### Core
- `/api/users` - User profile management
- `/api/characters` - Character CRUD
- `/api/chat` - AI storyteller interactions
- `/api/npcs` - NPC data and locations

### Building & Trading
- `/api/build` - Build structures
- `/api/materials` - Material definitions
- `/api/schematics` - Building schematics
- `/api/trade/offer` - Create trades
- `/api/trade/offers` - List open trades
- `/api/trade/{id}/accept` - Accept trade

### AI Villagers
- `/api/professions` - All 18 professions
- `/api/villagers` - All AI villagers
- `/api/villagers/{id}/work` - Villager daily work
- `/api/villagers/trade` - Villager trading

### World Expansion
- `/api/world/seedling` - Origin village
- `/api/world/lands` - Discoverable lands
- `/api/world/houses` - House schematics
- `/api/world/discover/{land_id}` - Discover new land
- `/api/world/build-house` - Build player house
