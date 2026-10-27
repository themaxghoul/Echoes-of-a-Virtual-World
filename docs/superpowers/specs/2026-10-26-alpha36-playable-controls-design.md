# Alpha 36: Playable controls and public playtest design

## Intent

Make EoV easier to return to and test by centering one dependable isometric play surface, exposing responsive proximity chat without consuming the whole screen, and shipping a downloadable desktop client. The larger vision—combat, crafting, vertical exploration, construction, an economy and public support—must arrive as real, stateful gameplay rather than decorative controls.

## Goals

- Keep the Alpha 35 persistent-world and shared-action model authoritative.
- Keep isometric exploration as the only promoted graphical view until another view has usable movement, perception and server-backed actions.
- Let players reveal and hide proximity chat with `T`, retain a visible button for mouse/controller accessibility, and keep keyboard movement usable while chat is open.
- Deliver a versioned desktop build for owner playtesting and document its exact support/publication status.
- Stage the next systems in dependency order: unified action mappings, itemized inventory/crafting, combat, elevation, construction, then any change to the economy.

## Non-goals for this build

- No nonfunctional combat/crafting buttons or UI implying unsupported mechanics.
- No first-person, Unity, VR or mod tools promoted as ready.
- No spendable or redeemable CU, paid in-game currency, deposits, withdrawals, or real-world settlement.
- No physical hardware actuation.
- No claim that a local desktop binary has been published to GitHub Pages or that a support payment route is active until the destination and deployment are verified.

## Approaches considered

1. **Continue Alpha 35's React/Electron + persistent-world service (chosen).** It contains the latest canonical action, evidence, competency and world-clock work. It is the least disruptive path to a usable test build.
2. **Replace the public surface with `feat/playable-public-alpha`.** Its Cloudflare Durable Object, Pages, and two-player test offer a valuable deployment reference, but the handoff explicitly identifies a separate simplified simulation and incompatible persistence. Copying it wholesale would create a competing world/action model.
3. **Move to the `EoaVW-FG` Unity scaffold.** It is a small project shell, not a comparable playable implementation, and would delay the requested playable build.

## Architecture and boundaries

Keep the current local Alpha 35 branch as the simulation source of truth. Adapt useful deployment lessons from the public-alpha handoff only behind an explicit future transport/persistence adapter; do not merge its second kernel into the shared simulation. Keep any future combat, item, crafting, and elevation inputs mapped to the canonical consequential-action pipeline, with the server deciding access, time, state change and evidence. CU remains the internal provisional valuation record; a later spendable game unit must be explicitly separate and must not imply real-world value.

The immediate implementation is a `T`-controlled chat drawer within the isometric view, with all existing server-authenticated proximity behavior retained. The packaged Alpha 35 client is a test artifact, not a public release. A support page may only advertise a checkout after the owner has a verified, authorized payout destination. Neither a static page nor CU can directly top up OpenAI/Codex credits; external sponsorship proceeds and provider credit purchases remain separate steps.

## Acceptance

- `T` opens/closes the in-world chat drawer when focus is outside editable/interactive controls; text entry and keyboard movement are not hijacked.
- The mouse-accessible chat control has correct expanded state and an accessible name.
- Chat continues to use the authenticated persistent-world action and nearby resident replies; no fictional fallback is introduced.
- A clean frontend production build succeeds and a desktop package is produced for local testing.
- First-person, Unity, unimplemented combat/crafting, spendable currency, and live donation checkout are not presented as ready.

