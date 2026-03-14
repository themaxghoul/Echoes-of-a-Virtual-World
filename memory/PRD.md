# AI Village: The Echoes - PRD

## Original Problem Statement
Build an AI Village storytelling experience where users interact with AI companions in a dynamic world. The AI learns alongside users with different day-to-day tasks, learning how to be a companion rather than a tool, and building a virtual world for future VR Full-Dive interface.

## Core Philosophy
- AIs are "raised like humans" - they learn from player interactions, other AIs, and their environment
- The world starts as a single "seedling" village and expands through exploration
- Player actions have consequences - wrong steps lead to trial and error learning
- Day/night cycles affect gameplay (demons active at night)

## Special Accounts

### Sirix-1 (Supreme Account)
- **Username**: sirix_1
- **Password**: k3bdp0wn!0nr(?8vd&74v2l!
- **Permission Level**: sirix_1 (highest)
- **Is Transcendent**: true - stats appear as immeasurable (∞, ???, █████)
- **Is Immutable**: true (cannot be modified)
- **Cannot Degenerate**: values never decrease
- **Scan Protection**: Others see distorted cryptic symbols when viewing
- **AI Helper Access**: Only user with access to test device features on mobile

## What's Been Implemented

### Phase 1-2: Foundation (Jan 2026)
- [x] Landing page, auth, character creation
- [x] Village Explorer with 7 locations
- [x] AI storyteller chat (GPT-5.2)
- [x] Quest system with NPC/player quests
- [x] User profiles with permission tiers
- [x] WebSocket multiplayer infrastructure

### Phase 3: Building & Trading (Mar 2026)
- [x] 5 Building materials, 19 schematics
- [x] Trading system between players
- [x] Contribution points system

### Phase 4: World Systems (Mar 2026)

#### AI Professions (18 total)
| Tier | Professions |
|------|------------|
| Commoner | serf, farmer |
| Craftsman | chef, miner, blacksmith, butcher, carpenter |
| Warrior | swordsman, archer, knight |
| Scholar | scribe, alchemist |
| Mystic | court_mage, priest |
| Noble | merchant, baron |
| Leadership | guildmaster, captain |

#### Day/Night Cycle
Uses **APPROXIMATE location only** (timezone offset, never precise)
- Dawn (5-7): 20% danger
- Morning (7-12): 10% danger
- Afternoon (12-17): 10% danger
- Dusk (17-20): 30% danger
- Night (20-24): 70% danger
- **Witching Hour (0-3): 100% danger**
- Pre-Dawn (3-5): 50% danger

#### Biblical Demon Infestations
| Rank | Demons | Source |
|------|--------|--------|
| Lesser | Tormenting Imp, Wandering Shade | - |
| Standard | Soldier of Legion, Whispering Tempter | Mark 5:9, Genesis 3 |
| Greater | Spawn of Asmodeus, Collector of Mammon, Herald of Belphegor | Tobit, Matthew 6:24 |
| Arch | Avatar of Beelzebub, Abaddon the Destroyer | 2 Kings 1:2, Rev 9:11 |

#### AI Emotional Memory
- **9 Mood States**: joyful → content → neutral → annoyed → angry → furious
- AIs remember player interactions and carry mood forward
- Negative actions (property damage, theft) cause AI to refuse service
- Moods decay toward neutral over time

#### Guild System
| Type | Focus | Key Bonus |
|------|-------|-----------|
| Trade | Commerce | +20% gold gain |
| Combat | Fighting | +15% damage |
| Crafting | Creation | +25% craft speed |
| Exploration | Discovery | +30% travel speed |
| Mystical | Magic | +25% essence gain |

### Phase 5: Combat & Device Access (Mar 2026)

#### Combat System
**Actions:**
- **Attack**: 10 stamina, 15 base damage, 1s cooldown
- **Heavy Attack**: 25 stamina, 35 base damage, 2.5s cooldown
- **Block**: 5 stamina/sec, 70% damage reduction
- **Dodge**: 15 stamina, 0.5s invulnerability, 1.5s cooldown
- **Sprint**: Variable stamina drain, 2x movement speed

**Sprint Stamina Formula:**
```
drain = base_drain + (armor_weight × 0.5) / ((strength/endurance) × 0.75)
```
- Higher strength/endurance = less drain
- Heavier armor = more drain

**Equipment:**
- Armor Types: none, cloth, leather, chain, plate, legendary
- Weapon Types: fists, dagger, sword, greatsword, mace, spear, staff

#### AI Helper (Test Feature - Sirix-1 Mobile Only)
Device capabilities for enhanced gameplay:
- **geolocation_approximate**: Timezone/region only (NEVER precise)
- **vibration**: Haptic feedback (alert, success, damage, critical, heartbeat patterns)
- **notification**: Game notifications
- **orientation**: Device tilt for controls
- **battery**: Power-saving mode
- **network**: Quality adjustment
- **wake_lock**: Keep screen on
- **clipboard**: Copy game data

## API Endpoints

### Combat & Movement
- `GET /api/combat/stats` - Combat definitions
- `GET /api/character/{id}/combat-stats` - Character combat stats
- `POST /api/character/{id}/action` - Perform combat action
- `POST /api/character/{id}/move` - Move with optional sprint
- `POST /api/character/{id}/equip` - Equip weapon/armor
- `POST /api/character/{id}/regenerate` - Heal when out of combat

### Guilds
- `POST /api/guilds` - Create guild
- `GET /api/guilds` - List all guilds
- `POST /api/guilds/{id}/join` - Join guild
- `POST /api/guilds/{id}/leave` - Leave guild

### AI Helper (Sirix-1 Only)
- `GET /api/ai-helper/status` - Check availability
- `GET /api/ai-helper/capabilities` - Get device capabilities
- `POST /api/ai-helper/request-access` - Request capability access
- `POST /api/ai-helper/execute` - Execute device command

## Frontend Pages
- `/` - Landing
- `/auth` - Login/Register
- `/create-character` - Character creation
- `/select-mode` - Mode selection
- `/village` - Text-based explorer
- `/play` - First-person view with combat UI
- `/guilds` - Guild management
- `/quests` - Quest board
- `/profile` - User profile
- `/building` - Building system
- `/trading` - Trading system

## Prioritized Backlog

### P0 (Next Sprint)
- [ ] Multiplayer chat UI with channel selection
- [ ] Travel distance tracking for land discovery
- [ ] Demon combat visual effects

### P1 (Near Future)
- [ ] Day/night visual effects in game view
- [ ] AI villager dialogue based on mood
- [ ] Equipment inventory UI

### P2 (Future)
- [ ] Guild halls as buildable structures
- [ ] PvP combat between players
- [ ] Mount system for faster travel

### P3 (VR Phase)
- [ ] Voice input/output
- [ ] 3D environment rendering
- [ ] VR controller integration

## Technical Notes
- Backend: FastAPI, MongoDB (motor), WebSockets
- Frontend: React, TailwindCSS, Shadcn/UI
- AI: GPT-5.2 via Emergent Integrations
- Auth: bcrypt password hashing
- Location: Uses ONLY approximate (timezone), NEVER precise coordinates
