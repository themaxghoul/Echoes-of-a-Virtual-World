# AI Village: The Echoes - PRD

## Original Problem Statement
Build an AI Village storytelling experience where users interact with AI companions in a dynamic world. The AI learns alongside users with different day-to-day tasks, learning how to be a companion rather than a tool, and building a virtual world for future VR Full-Dive interface.

## User Personas
1. **Storytelling Enthusiasts** - Users who want immersive narrative experiences
2. **Gamers** - Players looking for AI-driven interactive fiction
3. **Future VR Adopters** - Early adopters building towards Full-Dive experiences
4. **AI Curious** - Users interested in AI companions vs tools

## Core Requirements
- Interactive story dialogue with AI companion
- Character creation/customization
- Village exploration with location-based interactions
- Global dataspace for AI learning/memory
- AI villagers with professions who can trade and have daily lives
- World expansion through travel and building
- Day/night cycles affecting gameplay
- Survival elements with demon infestations
- AI emotional memory system

## Special Accounts

### Sirix-1 (Supreme Account)
- **Username**: sirix_1
- **Permission Level**: sirix_1 (highest)
- **Is Transcendent**: true
- **Is Immutable**: true (cannot be modified)
- **Cannot Degenerate**: true (values never decrease)
- **Stats**: All resources stored as `None` (immeasurable/infinite)
- **Scan Protection**: When scanned/viewed by others, returns distorted cryptic symbols (∞, ???, █████, ▓▓▓)
- **Self-View**: Sees own stats as "∞" symbols with "Your power is beyond all measurement"

## What's Been Implemented

### Phase 1 - MVP Complete (Jan 2026)
- [x] Landing page with immersive dark fantasy entry
- [x] Character creation (name, background, traits, appearance)
- [x] Village Explorer with 7 unique locations
- [x] AI storyteller chat using GPT-5.2 via Emergent LLM
- [x] Location navigation with atmosphere descriptions
- [x] Global Dataspace page with memory visualization
- [x] Conversation persistence in MongoDB

### Phase 2.0 - Multiplayer & AI Expansion (Jan 2026)
- [x] Oracle Veythra - NPC who sees real-world news as prophecies
- [x] User Profile System with permission tiers
- [x] Quest System - NPCs and players can create quests
- [x] WebSocket Multiplayer infrastructure
- [x] 8 NPCs initialized with personalities and roles

### Phase 2.5 - First Person & Auth System (Jan 2026)
- [x] Login/Register Auth with bcrypt password hashing
- [x] Mode Selection Screen (First Person or Story Mode)
- [x] First Person View with D-Pad controls
- [x] Official Rankings (13 ranks from citizen to sovereign)
- [x] Standing System (Outcast → Legendary)

### Phase 3.0 - Building & Trading System (Mar 2026)
- [x] 5 Building Materials with stats (wood, stone, iron, crystal, obsidian)
- [x] 19 Building Schematics across 4 tiers
- [x] Trading System for player-to-player exchanges
- [x] Contribution Points system

### Phase 3.5 - AI Professions & World Expansion (Mar 2026)
- [x] **18 AI Professions** across 7 tiers:
  - Commoner: serf, farmer
  - Craftsman: chef, miner, blacksmith, butcher, carpenter
  - Warrior: swordsman, archer, knight
  - Scholar: scribe, alchemist
  - Mystic: court_mage, priest
  - Noble: merchant, baron
  - Leadership: guildmaster, captain
- [x] **12 Starter AI Villagers** with unique personalities
- [x] Villager Daily Work system
- [x] Villager-to-Villager and Villager-to-Player Trading
- [x] **World Seedling System** - "The First Echo" origin village
- [x] **5 Discoverable Lands**: Eastern Plains, Northern Mountains, Western Forest, Southern Coast, Underground Realm
- [x] **5 House Types**: campsite, cottage, house, manor, guild_hall
- [x] Land Discovery via travel or building requirements

### Phase 4.0 - Day/Night, Guilds, Demons, AI Mood (Mar 2026)

#### Day/Night Cycle System
Uses **APPROXIMATE location only** (timezone offset, never precise coordinates)
- [x] **7 Time Phases**:
  - Dawn (5-7): danger 0.2
  - Morning (7-12): danger 0.1
  - Afternoon (12-17): danger 0.1
  - Dusk (17-20): danger 0.3
  - Night (20-24): danger 0.7
  - Witching Hour (0-3): danger 1.0
  - Pre-Dawn (3-5): danger 0.5

#### Guild System
- [x] **5 Guild Types**:
  - Trade: +20% gold, -10% trade discount
  - Combat: +15% damage, +10% defense
  - Crafting: +25% craft speed, -15% material cost
  - Exploration: +30% travel speed, +20% discovery chance
  - Mystical: +25% essence gain, +15% spell power
- [x] Guild Ranks: Initiate → Member → Veteran → Officer → Leader
- [x] Guild creation, joining, leaving

#### Biblical Demon Infestations
- [x] **9 Demon Types** across 4 ranks:
  - **Lesser**: Tormenting Imp, Wandering Shade
  - **Standard**: Soldier of Legion (Mark 5:9), Whispering Tempter (Genesis 3)
  - **Greater**: Spawn of Asmodeus (Book of Tobit), Collector of Mammon (Matthew 6:24), Herald of Belphegor
  - **Arch**: Avatar of Beelzebub (2 Kings 1:2), Abaddon the Destroyer (Revelation 9:11)
- [x] Spawn chance based on time phase and infestation level
- [x] Location infestation levels: clear → stirring → infested → overrun → hellmouth
- [x] Combat system with drops and counter-attacks
- [x] Biblical origin lore for each demon

#### AI Emotional Memory System
- [x] **9 Mood States**: joyful, content, neutral, annoyed, angry, furious, fearful, grieving, inspired
- [x] **12 Interaction Types**:
  - Positive: positive_trade, generous_tip, friendly_chat, helped_quest, gift_received, saved_from_demon
  - Negative: insult, theft_attempt, property_damage, violence, betrayal, witnessed_demon
- [x] Mood affects trade prices and dialogue tone
- [x] AI remembers which players wronged them (refuses_service_to list)
- [x] Shop can close when villager is too upset
- [x] Mood decay over time toward neutral
- [x] **Environmental Learning**: AIs are raised by their environment and player interactions

## Tech Stack
- Frontend: React + Tailwind CSS + Shadcn/UI
- Backend: FastAPI + MongoDB (motor async driver)
- AI: OpenAI GPT-5.2 via Emergent Integrations
- Auth: bcrypt password hashing
- Theme: "The Void & The Flame" dark fantasy

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/register` - Register new user

### Time & Location
- `POST /api/time/phase` - Get current phase (requires timezone_offset only)
- `GET /api/time/phases` - Get all phase definitions

### Guilds
- `POST /api/guilds` - Create guild
- `GET /api/guilds` - List all guilds
- `POST /api/guilds/{id}/join` - Join guild
- `POST /api/guilds/{id}/leave` - Leave guild
- `GET /api/guild-types` - Get guild type bonuses

### Demons & Infestations
- `GET /api/demons` - List all demon types
- `GET /api/demons/{type}` - Get demon details
- `POST /api/demons/spawn/{location_id}` - Spawn demon
- `GET /api/demons/active/{location_id}` - Get active encounters
- `POST /api/demons/{encounter_id}/attack` - Attack demon
- `GET /api/infestation/{location_id}` - Get infestation level

### AI Villagers & Mood
- `GET /api/villagers/{id}/mood` - Get villager mood
- `POST /api/villagers/{id}/interact` - Interact with villager
- `POST /api/villagers/decay-moods` - Decay all moods toward neutral

### Scan & Profile (with Sirix-1 Protection)
- `GET /api/scan/{target_id}` - Scan entity (distorted for Sirix-1)
- `GET /api/profile/view/{user_id}` - View profile (masked for Sirix-1)

## Prioritized Backlog

### P0 (Next Sprint)
- [ ] Make D-pad/joystick functional with movement
- [ ] Multiplayer chat UI (WebSocket backend exists)
- [ ] Travel distance tracking for land discovery

### P1 (Near Future)
- [ ] Demon combat UI in frontend
- [ ] Guild management UI
- [ ] AI villager conversation UI showing mood

### P2 (Future)
- [ ] Day/night visual effects in game view
- [ ] Demon infestation visual indicators
- [ ] Guild halls as buildable structures

### P3 (VR Phase)
- [ ] Voice input/output integration
- [ ] 3D environment rendering
- [ ] VR controller integration
