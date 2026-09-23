# Public alpha handoff — updated 2026-09-23

## Start here on another device

Clone this repository and read this file before modifying the alpha. The original React/FastAPI/MongoDB prototype remains in place. The public game is a separate, deliberately bounded implementation; original MongoDB saves are not migrated.

- Public Worker: https://echoes-world-alpha.echoes-world-free-runtime.workers.dev
- GitHub browser modes: https://themaxghoul.github.io/Echoes-of-a-Virtual-World/
- Cloudflare project: `cloudflare/`; Worker name `echoes-world-alpha`.
- Static clients: `docs/play/`; `config.json` selects the shared backend for GitHub Pages.
- Offline/self-hosted alternative: `alpha/` (Python/FastAPI and SQLite).
- Architecture and execution history: [ALPHA_DESIGN.md](ALPHA_DESIGN.md), [ALPHA_PLAN.md](ALPHA_PLAN.md).

Cloudflare accepted the initial deployment and its public HTTPS two-player network test passed. GitHub Pages is enabled and its deployment succeeded (HTTP 200 verified). The latest persistence update and its verification are documented in PERSISTENT_WORLD_PLAN.md.

## Implemented game slice

Story/text, isometric canvas, and experimental first-person canvas share the same accounts, position, construction, chat, and ledger. Only the selected renderer is imported; story mode does not download graphics modules or a Unity client. Unity is explicitly marked in development with a link to releases, not a fabricated download.

Create a named account with a password and retain that password. There is no password recovery yet. Sessions expire after 30 days. WASD/arrows and the direction pad move; first-person arrows turn. Return to commons escapes blocked locations. Gather, build, research, chat, talk to Samaritans, propose cooperation, and transfer experimental credits through the sidebar. Chat collapses to leave more room for the world.

The world starts with radius 512 tiles. Each new account's first join expands it by 32 tiles. Reconnects and mode changes do not expand it. Terrain retains the original stored seed and coordinate algorithm. Chunks are instantiated on demand, then stored with versioned hierarchical seed provenance. Saved chunks are never rerolled by a replacement generator. World → region → settlement → parcel seeds are recorded; new construction adds structure, room and object seed records (these are provenance, not rendered interiors). A global limit of 1000 newly instantiated chunks per UTC day protects the free database allowance; existing chunks remain readable. Clients can request only nearby chunks. This is one shared world, not separate personal universes. Camps, farms and labs persist, but farms/labs do not yet run production chains. Soil research is a small procedural experiment, not a validated scientific model.

Mira, Oren and Sol now have persistent positions, intentions, personal supplies and bounded memories. Their former clock-driven wandering is removed. One independent model decision is scheduled every two hours across the three agents (up to 12/day); decisions can reflect, gather, research, explore or speak in the activity journal. Physics, resource ownership and allowed actions are checked by the server. A rejected or interrupted decision has no committed physical consequence. The journal reports the outcome and next scheduled cycle. This is a bounded free-runtime adaptation, not full parity with the legacy autonomy router or continuous real-time cognition. The original village characters remain narrative characters.

Workers AI enriches HTTP conversations with remembered context. The shared budget is 50 calls per UTC day, including autonomous decisions. Timeout, quota exhaustion or model errors fall back to contextual conversation. Ordinary dialogue never directly executes world commands; messages to the three Samaritans can inform their later independent decisions. Diplomacy remains an explicit limited cooperation action. It is not a model-negotiated treaty engine.

Harvest patches are shared and persistent: twelve available units per tile, two per harvest, one unit regenerating each minute. Moving to another patch or waiting restores access. Agent gathering consumes the same patch supply and goes into the agent's own inventory. Model output cannot award player credits or grow the world.

## Economy boundary

Credits are experimental in-game units with **no monetary value**. No BTC deposits, withdrawals, conversion, payout or mining are enabled. Transfers use whole amounts, server authorization, balanced double-entry rows and replay keys; balances cannot be set by clients. Initial grants and research awards are recorded. This is not a reviewed real-money financial system.

## Free hosting and capacity

Workers Free plus one SQLite Durable Object owns the persistent world. No paid subscription or Render service was created. `render.yaml` and `Dockerfile` are optional self-hosting/paid alternatives, not the selected deployment. Stay on the free plan unless the owner explicitly changes that decision.

This alpha admits at most 16 distinct online accounts, 3 sockets per account, 1000 registered accounts and 10000 buildings. Those limits do not guarantee enough free quota for continuous maximum load. Movement sends at most roughly 7 messages/second; idle input heartbeats occur every 30 seconds. A movement timer runs only while players are connected. Durable alarms continue the limited agent schedule when players leave. Position writes batch every 10 seconds and on disconnect; an abrupt crash can roll back up to 10 seconds of movement. Ledger/action changes persist immediately.

Cloudflare free allowances are shared with other applications on the account; exhausted quotas can interrupt service until reset. See [DO pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/) and [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/). Do not advertise unlimited capacity or guaranteed uptime. Account farming, moderation, recovery, richer simulation and large-world partitioning remain future work.

## Develop, test and deploy

Use Node 24 and pnpm 11. From `cloudflare/`:

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm exec wrangler dev
```

Open the local Wrangler URL (usually port 8787). Local mode uses its own backend and disables remote conversation AI calls and automatic agent scheduling. Do not manually trigger local alarms against the remote AI binding unless intentionally testing its quota usage. Local Python, local Wrangler and production saves are separate; their terrain algorithms and database schemas differ. Never copy one database into the other.

From the repository root, Python tests use an isolated virtual environment:

```sh
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -r alpha/requirements-dev.txt
python -m pytest alpha/tests -q
node --test cloudflare/tests/*.test.js
node --test alpha/tests/connection.test.mjs
python cloudflare/tests/network_smoke.py
```

The network test expects a running Wrangler on port 8787. Passing a public base URL creates two test accounts and permanently increases membership; use deliberately. Original legacy tests target external preview systems and are not part of this verification.

Production update, from `cloudflare/`:

```sh
pnpm exec wrangler login
pnpm exec wrangler whoami
pnpm test
pnpm exec wrangler deploy
```

Verify the account before deploying. Keep Worker name, Durable Object class, migration tag and object name `eov-shared-alpha-v1` stable. Renaming the object creates a different world. Never delete the namespace to reset a bug. Use Cloudflare's Durable Object recovery tooling before destructive storage changes; there is no in-game admin/reset endpoint. Keep tokens, `.dev.vars`, `.wrangler`, local SQLite databases and user passwords out of Git.

GitHub Pages workflow publishes only `docs/play/` when main changes. Cloudflare deployment is currently manual; a Git push alone does not update the backend. Update both when shared contracts change. Configure GitHub Pages source as GitHub Actions.

## Domain and agent setup

The workers.dev address works independently of `echoesofvirtuality.com`. The latest DNS check still found IONOS nameservers and the authenticated Cloudflare account returned no matching zone. Custom domain activation remains separate. Preserve MX/SPF/DKIM/DMARC records and verify the registrar's nameservers before routing the domain.

Cloudflare's official agent setup instructions were fetched. Fourteen Cloudflare skills were installed on this device, and MCP entries for Cloudflare, docs, bindings, builds and observability were added. Wrangler OAuth is authenticated. Docs MCP works without login; other MCP OAuth sessions require their own authentication and are not implied by Wrangler login. These device settings are outside Git. On another device, follow https://developers.cloudflare.com/agent-setup/prompt.md again.

## Verification record

- Python: 13 alpha tests passed (two dependency deprecation warnings).
- Cloudflare: 11 Node tests passed, including failed-write retry regression.
- Earlier local two-client network test passed presence, movement, chat, concurrent transfer replay, dialogue and stable membership.
- Independent review found idle quota consumption and rolled-back position retry bugs; both were corrected.
- Public HTTPS network test passed health, authorization, two-client presence/movement/chat, concurrent transfer replay, dialogue and stable membership. All three local browser modes inspected. Main726 story restoration adds locations, narrator/NPC conversations, saved history and XP; see STORY_RESTORATION.md.

The new Main726 story adapter currently runs on the Cloudflare backend only. The optional Python alpha retains its original shared-world commands and is not a feature-equivalent substitute for /api/story.
