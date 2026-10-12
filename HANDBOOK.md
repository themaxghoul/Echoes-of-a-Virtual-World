# AI Village: The Echoes — Creator's Handbook

Welcome! This guide explains how the whole game economy and societal system works —
written so you can understand it fast and extend it with confidence.

## 1. The Big Picture

The game had many separate "earn VE$" mini-apps (gig tasks, job boards, marketplaces).
**All of those were deleted** and replaced with ONE unified system: the **Hybrid Economy**.
You don't do chores to earn anymore — you just *play*, and the simulation pays you.

## 2. The Three Currencies

| Currency | What it is | How you get it |
|---|---|---|
| **VE₀** (proto-currency) | The warm-up money, active NOW | Playing: presence, moving, NPC chat, quantum stabilizing |
| **VE Vouchers** | Sealed "future-value" tickets indexed to Bitcoin | Lifetime mining milestones per channel (50/200/600/1500/4000 VE₀) |
| **VE$** (final currency) | The real economy, LOCKED until launch | Activates at the Quantum Awakening |

Old VE$ balances were converted to VE₀ at 1:1 — nothing was lost.

## 3. The Bitcoin Formula (no crypto involved!)

VE$'s value follows: **f(BTC) = α·ln(BTC) + β + γ·BTC^δ**
- `α·ln(BTC)` = slow, stable log growth (the backbone)
- `β` = guaranteed minimum value floor
- `γ·BTC^δ` = small polynomial term that surges when BTC hypes
- Hard cap: VE$ can never exceed 1% of BTC's price
- BTC price comes from CoinGecko (live, cached 5 min, admin can override)
- *Data provided by CoinGecko* (required attribution — keep it!)

Defaults: α=1.8, β=5.0, γ=0.02, δ=0.22. All tunable in the Admin tab (sirix only).

## 4. Mining (metaphorical — no hashing!)

Four channels, each with a per-call max and daily cap (see `CHANNELS` in
`backend/hybrid_economy_router.py`):

1. **XR Presence** — being in Story Mode / 3D world (auto, 1 tick/min)
2. **XR Spatial Work** — movement + interactions (auto, counted by `useVE0Mining` hook)
3. **AI Cognitive Yield** — every NPC conversation (hooked in `ai_chat_router.py`)
4. **Quantum Entropy** — the Stabilizer button in Economy Nexus (biggest entropy)

Every mint also adds **entropy** to the global `quantum_progress` counter.

## 5. The Quantum Awakening (economic launch)

When `quantum_progress >= milestone_target` (default 25,000):
- A gold mine ("The Aurum Breach") springs from the landscape (world event)
- All VE₀ converts to VE$ at the configured ratio (default 0.25)
- Every voucher pays out: `f(BTC at launch) × btc_units × voucher_multiplier`
- Mining starts minting VE$ directly

Admin can force it: Economy Nexus → Admin tab → "Force Quantum Awakening".

## 6. Societal Standing (Tab key in first-person)

Four standings, computed LIVE from real play data (`backend/society_router.py`):
- **Social** — NPC relationships + conversation counts
- **Political** — guild membership/leadership + faction
- **Economic** — net worth + lifetime mining
- **Undercover** — adopt a cover identity (alias + persona); integrity starts at 100
  and erodes via `/society/event` deltas

## 7. Crafting (C key in first-person)

Minecraft/Terraria structure with Sims-depth specs (`backend/crafting_router.py`):
- Materials: wood / stone / iron / crystal (stored on `user_profiles.materials`)
- **Stations gate recipes**: Workbench → Forge → Lab (craft them in order!)
- Quality roll: crude → common → fine → superior → masterwork
  (surplus materials improve your odds)
- Every item gets a spec sheet: durability, weight, aesthetics, utility,
  comfort (furniture), precision (scientific), composition, flavor text
- Crafting feeds the economy (XR spatial yield) and counts toward vouchers

## 8. In-Game Keys (First-Person 3D)

| Key | Action |
|---|---|
| WASD / arrows | Move |
| **Tab** | Societal Standing menu |
| **/** | Open multiplayer chat |
| **C** | Crafting Workshop |
| E / Space | Interact |
| Esc | Close overlay / pause |

## 9. Where Everything Lives

- `backend/hybrid_economy_router.py` — currencies, formula, mining, vouchers, launch
- `backend/society_router.py` — standings + cover identities
- `backend/crafting_router.py` — recipes, quality, spec sheets
- `backend/data_api_router.py` — Task Factory (INTERNAL ONLY — generates tasks, no player access)
- `frontend/src/pages/EconomyNexus.jsx` — the /economy page (Overview/Mining/Vouchers/Guide/Spend/Admin)
- `frontend/src/hooks/useVE0Mining.js` — passive presence mining (drop into any page)
- `frontend/src/components/SocietyStandingOverlay.jsx` — Tab menu
- `frontend/src/components/CraftingOverlay.jsx` — C menu

## 10. Golden Rules

1. Never credit `balance_ve` directly pre-launch — use `record_contribution()`
2. All new API routes need the `/api` prefix
3. Secrets live in `backend/.env` only (CoinGecko key is `COINGECKO_API_KEY`)
4. MongoDB docs returned by APIs must exclude `_id` (use projections or `dict()` copies on insert)
5. Admin = `sirix_1_supreme`
