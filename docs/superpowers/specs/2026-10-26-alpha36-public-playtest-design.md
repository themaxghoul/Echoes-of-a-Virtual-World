# Alpha 36: public playtest and lived-in settlement design

## Intent

Move EoV from a private packaged test toward a public, accurately described Windows playtest. Give the existing settlement a modest but visible sense of daily life, and make its game surface and public support page feel like parts of the same dark-fantasy/neural setting.

## Goals

- Publish the Windows client and a self-hosted persistent-world server source bundle as GitHub Release assets, built from a version tag.
- Add a dedicated GitHub Pages support/playtest page with a verified link to the latest release, clear server requirements, feature status, feedback route, and transparent funding status.
- Let off-duty Samaritans autonomously choose and travel to locally perceived public places using deterministic, persisted routes; needs, active work, refusals/commitments, and world visibility remain respected.
- Improve the in-game dashboard's hierarchy and legibility without hiding important authority, needs, work, or evidence state.
- Keep one authoritative persistent-world model and the existing authenticated action transport.

## Non-goals

- No second simulation kernel, client-side NPC movement authority, unrestricted teleportation, or movement outside discovered/passable paths.
- No claim of 24/7 hosted multiplayer; the release includes a server package, not managed hosting.
- No in-world spendable or redeemable currency, real-money checkout, or automatic Codex-credit replenishment.
- No placeholder combat, first-person, Unity, VR, or crafting controls presented as functional.

## Approaches considered

1. **Add autonomous routing to the existing persistent tick and publish tagged assets (chosen).** Reuses world persistence, route progression, and current React/Electron client. It is the narrowest route to visible NPC life and a reproducible public playtest.
2. **Rebuild the separate Cloudflare public-alpha kernel.** This provides a deployment reference, but creates an incompatible authority and save model; rejected.
3. **Only redesign the front-end and fake NPC motion locally.** Cheaper visually, but would diverge from persistent state and misrepresent autonomy; rejected.

## Design decisions

- A Samaritan is eligible for leisure/social travel only when autonomously controlled, not committed to a consequential action, not already routing, outside its work shift, and above urgent survival thresholds.
- Candidate destinations come only from public places/resource sites in the resident's current region and within the resident's discovered, passable terrain. Selection and route IDs are deterministic from world seed, entity, and tick. Routes persist in the NPC record and advance through the existing world tick. Each segment emits a movement event; arrivals update a small, bounded subjective memory. Urgent survival and accepted work retain precedence.
- The first release proves local roaming within discovered land. Cross-region expeditions for AI residents remain a follow-up because region transitions currently change player state through a distinct adventure action and need explicit shared-action modeling.
- The existing Pages workflow keeps the browser alpha at the site root and publishes `docs/support/` at `/support/` from protected `main`. Its download panel points at versioned GitHub Release assets. The release workflow creates the client zip and persistent-server source zip on `eov-alpha36` tags.
- The support page is informational and contribution-oriented (feedback, issues, code). No checkout appears until an owner-controlled payout destination is verified; any future sponsor proceeds are not automatically converted into OpenAI/Codex usage credits.
- UI refinement focuses on clear status hierarchy, restrained overlays, responsive layout, focus visibility, and simpler grouped information; existing causal/economic details remain available rather than being discarded.

## Acceptance

- Backend tests prove eligible residents get a reproducible route, routes advance one passable step per tick, discovered-world visibility expands as they travel, and urgent needs/commitments block leisure movement.
- The game renders NPCs from authoritative server snapshots and provides a clearer responsive control/status hierarchy without breaking chat, camera, or world controls.
- A clean release workflow produces both expected asset names from a tag; page links match those names and explains self-hosted server requirements and non-production status.
- Unit, integration, E2E, production-build, and package checks pass before any public tag/publish action.
