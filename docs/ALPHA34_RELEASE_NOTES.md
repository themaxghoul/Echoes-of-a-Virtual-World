# Echoes of Virtuality Alpha 34 — Routed Resource Frontier

Alpha 34 keeps the persistent 64×64 world from Alpha 33 and makes the next interaction layer authoritative and inspectable.

## Implemented and verified

- Server-owned approach routing evaluates every reachable tile beside a resource and preserves the traveler’s current region through route execution.
- Resource receipts distinguish proposals, completed site changes, evidence-only inspections, and material actually held in actor inventory.
- Consumed inputs such as seed and feed are reported as negative inventory deltas; extracted material is not awarded until the canonical shared-action workflow verifies it.
- Autonomous proximity speech rotates through eligible residents using persisted last-spoke attention, even when belonging needs are uneven.
- Ephemeral social memories are bounded without evicting procedural evidence such as pending witnessed-conduct records.
- The same authoritative action and persistence rules continue to apply to human and AI performers.
- Client and server displays are unified at `0.3.0-alpha.34`.

## Prototype or limited

- The first frontier remains bounded to 64×64; streamed chunks are deferred.
- Character presentation uses readable isometric markers rather than finished models or animation.
- Resource extraction still requires proposal, acceptance, reservation, execution, independent verification, and custody transfer.
- Autonomous society systems are functional foundations, not a claim of AGI.
- CU remains internal, nonspendable accounting with no withdrawal, redemption, fiat, or crypto function.

## Running the release

Extract the server archive, create a private `.env` from `.env.example` (or review `ALPHA34_WORLD_SERVER.env.example`), install `persistent-world-requirements.txt`, and launch `run_persistent_server.ps1`. Configure the desktop client's World Server URL to the server address and authenticate through an EoV session provider using the same signing secret.

Never reuse test credentials for a public server. Do not publish the generated database or `.env` file.
