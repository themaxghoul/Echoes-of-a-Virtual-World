# Persistent world and agent restoration

Status: implementation and local verification complete; deployed to the free Worker on 2026-09-23. Production account, world, story history and terrain comparison passed. Published for review in PR #8. The production alarm fired and rescheduled; its first model response exposed a parser mismatch, which is fixed in the final deployment.

## Evidence and preservation

The reference is Main726 (`a1eecd907de8a9b52827c6dd37e074fbeb4353e9`), plus the user's existing Emergent chat. Read-only history inspected on 2026-09-22 shows June Field Ops tests, a July economy-removal request, interrupted removal commands, repeated credit exhaustion, and later missing frontend imports. These historical test claims are not proof that the current application passes. No Emergent credits, upgrades, or paid code access are required for this work. Credentials appearing in that history must not enter this repository.

The legacy autonomy router is still present. Its model call differs from the working story call: `LLM_API_KEY` versus `EMERGENT_LLM_KEY`, a plain string versus `UserMessage`, and a thread-wrapped call/dictionary response versus an awaited asynchronous call/string response. Repair the integration without replacing the NPC's personality or decision policy. The public Cloudflare runtime is a separate implementation; decorative NPC movement there is not evidence of restored autonomy.

## Implementation sequence

1. Add a regression test for the legacy conversation contract and repair that call.
2. Introduce a versioned classical possibility generator and hierarchical seeds. Preserve the exact existing terrain algorithm. Persist chunks when instantiated; subsequent reads must use stored data even after a provider changes. Both renderers continue consuming the same canonical API.
3. Add persistent agent state, bounded memory, validated decisions and consequence records. Connect perception and player conversations to decisions. Replace clock-driven NPC wandering with actual stored actions. Use durable scheduling and a small shared free AI budget; report unavailable reasoning honestly.
4. Add shared, persistent ecosystem depletion/regeneration and retry-safe consequences. Keep player credits and property outside model authority.
5. Test restart recovery, duplicate delivery, failure rollback, old terrain compatibility and provider substitution. Review, publish and verify the public build.

The hierarchy is world → region → settlement → parcel → structure → room/object. A seed describes possibilities; it does not create all descendants. Generation and persistence are separate steps. MOTH is a future provider, not an implemented quantum service.

Existing accounts, ledger entries, structures, world seed and frontier are retained. Frontier growth remains tied to first joins. First-person and isometric rendering are preserved. Story travel remains narrative travel rather than secretly moving the shared-world avatar.

## Verification and limits

- Node: 27 passing tests (24 Cloudflare runtime tests, two terrain retry tests, one connection freshness test).
- Python: 14 passing alpha tests, including the legacy async-chat regression. Two existing FastAPI/Starlette dependency deprecation warnings remain.
- Browser: existing local account connected in isometric, first-person and story modes; the activity panel loaded. The renderers themselves were not rewritten.
- Production deployment: `df489000-eb05-4f9d-b0e8-5ef28d4c80ba`. Existing QA account state, world seed/radius/membership, story state/history and all 256 origin-chunk tiles compared equal before/after deployment. The new hierarchical path and scheduled alarm were returned by the live API.
- Review findings fixed: global generation quota and nearby-only chunk requests; interrupted pending cycles; atomic story memory; per-player movement handling at generation exhaustion; client retry backoff.

The free runtime schedules at most twelve independent reasoning attempts daily, one every two hours across Mira/Oren/Sol, within the shared fifty-call daily AI allowance. This is deliberately slow and bounded. Village story characters keep their original narrative profiles but do not receive new spatial agents. Legacy MongoDB saves, every old economy/quest router, model-negotiated diplomacy and MOTH execution are not included. Structure/room/object seeds are persisted provenance for future detail, not finished interiors.

Source of truth: `cloudflare/src/kernel.js` for player state/actions, `possibilities.js` for generation and terrain persistence, `agents.js` for the decision lifecycle, `story.js` for narrative state, and `worker.js` for network/scheduling. Both graphical modes use the same kernel/chunk API. The Python `alpha/` server is an alternative older runtime, not schema-compatible with these Worker tables.

## Provider verification

A real Workers AI call returned an already-parsed object in `response`, rather than JSON text. The decision parser now accepts either representation and subjects both to identical action validation. The shared model is the documented `@cf/meta/llama-3.1-8b-instruct-fp8`. See [model documentation](https://developers.cloudflare.com/workers-ai/models/llama-3.1-8b-instruct-fp8/) and [structured response documentation](https://developers.cloudflare.com/workers-ai/features/json-mode/).

An isolated local Durable Object using the actual Workers AI binding successfully committed Mira's independently chosen reflection about soil moisture. The public alarm fired and retained its next scheduled wake-up; the first failed decision remains honestly recorded as rejected rather than being rewritten. The corrected public deployment returned a model-generated soil-comparison answer in about five seconds, preserved its replay result, and returned authenticated WebSocket snapshots with the persisted agents. Subsequent production alarms ran on schedule: Oren independently gathered two food into personal supplies. Research attempts without food were rejected. Those failures now enter memory atomically, and perceptions include recent outcomes and currently affordable actions so future decisions can learn from rejection.

Model calls have a twenty-second deadline; the browser waits thirty seconds, leaving time to receive a saved fallback. Diagnostic warnings record only error category and response shape, never player text or credentials. No paid plan was enabled.
