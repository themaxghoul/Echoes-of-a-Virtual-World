# Public alpha design — 2026-09-21

## User intent and acceptance
People can choose text/story, isometric, or first-person browser play without installing Unity. All three views share a persistent scientific/life-simulation sandbox. Conversation does not grant arbitrary world powers; diplomacy uses explicit actions. Samaritans have goals, useful responses, and memory. Existing Unity work remains a future integration, not a fictional download.

## Inspection and decision
The original React/FastAPI/MongoDB prototype is retained. Its 7,000-line server exposes unauthenticated mutations, login returns no session token, and the AI fallback intentionally says nothing. Its pseudo-3D movement clamps coordinates to 5–95. Making every legacy endpoint public would expose unfinished financial systems.

Original self-hosting design (superseded for public hosting by the free-tier decision below): the public entry point uses a separate, small alpha runtime in `alpha/` and static browser clients in `docs/play/`. No legacy endpoints are mounted. FastAPI serves authenticated commands and WebSocket snapshots. SQLite on a persistent disk owns accounts, sessions, terrain seed, memberships, positions, construction, messages, relations, and double-entry ledger rows. One process/worker is supported for this alpha. This is an incremental playable foundation, not a replacement or migration of existing saved games.

## World and movement
A seeded 1024-by-1024-tile starting area provides room for individual settlements. Each distinct authenticated account joining the world expands its radius by 32 tiles; reconnects, time, movement and mode switches never expand it. Existing terrain is coordinate-derived and never rerolled. Terrain and buildings constrain server-controlled movement at 20 Hz; snapshots go out at 10 Hz. Clients interpolate rendering and request nearby 16-by-16 chunks. Guests use named accounts with passwords; repeated account farming remains an alpha limitation requiring moderation before a large launch.

## Play loop and social behavior
Players explore, gather renewable resources with cooldowns, build camps/farms/labs, and conduct basic local soil experiments. State changes are explicit commands. Text players can use the same commands, inspect surroundings, chat, and propose cooperation. Samaritans move autonomously between their work sites and respond using individual goals and per-player history. An optional server-side language model can enrich dialogue; deterministic contextual dialogue remains usable without a paid key. Generated prose cannot execute commands or change balances.

## Economy
EoV credits have no monetary value, BTC conversion, deposit, withdrawal or payout. Awards and transfers are atomic, integer-only, balanced double-entry transactions with idempotency keys. Resource/action requirements are checked on the server. Ledger history is retained; UI makes the experimental status explicit. Real-money integration needs a separate reviewed project.

## Hosting and verification
GitHub Pages publishes only static clients and mode links. A Render blueprint packages the single-worker runtime with a persistent disk; deployment requires the user's account and billing setup. No public persistent server is claimed until an external health check and two-client test succeed. Local tests cover persistence, seed stability, growth, authority, replay protection, ledger balance, conversation and simultaneous clients. Browser tests cover each mode, controls, lazy downloads, and connection failure. Handoff records exact commands, paths, commits, outstanding issues and deployment status for use on another device.

## Final hosting decision
The user cannot fund hosting. Public production therefore uses cloudflare/src/worker.js and a SQLite Durable Object on Workers Free, with optional quota-bounded Workers AI. alpha/ remains a separate self-hosting alternative. No paid Render service was created. See HANDOFF.md for limits, save incompatibility, deployment commands and verification status.
