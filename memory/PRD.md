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

## What's Been Implemented (Jan 2026)

### Phase 1 - MVP Complete
- [x] Landing page with immersive dark fantasy entry
- [x] Character creation (name, background, traits, appearance)
- [x] Village Explorer with 6 unique locations
- [x] AI storyteller chat using GPT-5.2 via Emergent LLM
- [x] Location navigation with atmosphere descriptions
- [x] Global Dataspace page with memory visualization
- [x] Conversation persistence in MongoDB
- [x] Character persistence per user

### Phase 1.5 - Progression & NPC System (Jan 2026)
- [x] Fixed sidebar visibility bug (content hides when closed)
- [x] NPC visual appearances with avatar images
- [x] Milestone-based world progression (6 milestones)
- [x] XP system (+10 conversations, +20 new locations)
- [x] Locked/unlocked location system
- [x] Per-location background images
- [x] XP progress bar in sidebar
- [x] LocalStorage persistence for progression

### Phase 1.6 - UI Fixes & Real-World Integration (Jan 2026)
- [x] Fixed action buttons placement - moved outside input field to bottom right
- [x] Added "Quick:" action buttons bar below input (explore, talk, rest, observe)
- [x] Real-world news integration via Google News RSS
- [x] News caching (1 hour) to reduce API calls
- [x] AI system prompt now includes world news for fantasy-context responses
- [x] News indicator button in header (globe icon)
- [x] Click news button to ask "What news from the outer world?"

### Phase 2.0 - Multiplayer & AI Expansion (Jan 2026)
- [x] **Oracle Veythra** - Special NPC who sees real-world news as prophecies
- [x] **Sirix-1 Supreme Account** - Immutable user with max permissions (cannot be overwritten)
- [x] **User Profile System** - Persistent profiles across characters with resources
- [x] **Permission Tiers**: Basic → Advanced → Admin → Sirix-1
- [x] **Quest System** - Both NPCs and players can create quests with resource payouts
- [x] **NPC Location Stamps** - Each NPC has home location + visitable locations
- [x] **Quest Board UI** - View, create, and accept quests
- [x] **Profile Page** - View resources, XP, permissions, characters
- [x] **WebSocket Multiplayer** - Real-time chat infrastructure
- [x] **Message Boards** - Async communication per location
- [x] **8 NPCs initialized** with personalities, roles, and knowledge domains

### Tech Stack
- Frontend: React + Tailwind CSS + Shadcn/UI
- Backend: FastAPI + MongoDB
- AI: OpenAI GPT-5.2 via Emergent Integrations
- Theme: "The Void & The Flame" dark fantasy

## Prioritized Backlog

### P0 (Next Sprint)
- [ ] Outer Realms expansion (unlocked at 1000 XP)
- [ ] NPC relationship tracking with affinity meters
- [ ] Quest/objective system with story arcs
- [ ] Character stat progression (skills)

### P1 (Future)
- [ ] Multiple character support
- [ ] Save/load game states
- [ ] Inventory system
- [ ] Dynamic NPC dialogue memory

### P2 (VR Phase - Hardware Rendering)
- [ ] Voice input/output integration
- [ ] 3D environment rendering (VR console handles GPU)
- [ ] VR controller integration
- [ ] Full-Dive interface prep
- [ ] Spatial audio for immersion

## VR Integration Notes
The VR consoles will handle:
- Graphics rendering memory
- 3D scene processing
- Controller input mapping
- Spatial tracking

Backend will provide:
- AI narrative generation
- World state management
- Character/NPC data
- Progression tracking

## Next Tasks
1. Add more dynamic NPCs with unique personalities
2. Implement quest/mission system
3. Add character stat progression
4. Enhanced dataspace visualization with network graph
