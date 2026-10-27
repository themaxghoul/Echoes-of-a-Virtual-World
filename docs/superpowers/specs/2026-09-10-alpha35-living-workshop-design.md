# Alpha 35: The Living Workshop

**Status:** Proposed for owner review  
**Target:** Echoes of a Virtual World Alpha 35  
**Purpose:** Convert EoV's autonomous-society foundation into one dependable, visible, end-to-end production loop without diluting the project's original direction.

## Permanent design charter

Alpha 35 and later work must preserve these constraints:

1. Humans and AI citizens use the same consequential-action rules. AI citizens may own property, refuse work, negotiate, leave, organize, communicate, and form beliefs.
2. Authoritative world state, recorded evidence, and an individual's beliefs or memories remain separate. An entity knows only what it perceived, was credibly told, or learned through evidence.
3. Competence comes from demonstrated, reproducible practice. Titles, prompts, or administrator declarations do not create expertise.
4. Physical work accounts for materials, tools, access, time, energy, measurements, precision, durability, useful output, and inspectable failure at an understandable level of abstraction.
5. Speech may change relationships, memory, rumor, agreements, institutions, and later choices. Speech alone cannot directly alter terrain or material state.
6. CU remains a nonspendable internal accounting and valuation unit. Alpha 35 adds no withdrawals, redemption, guaranteed payout, cryptocurrency, or speculative market.
7. The world is persistent, deterministic where replay requires it, bounded during offline catch-up, recoverable after interruption, and owned by one authoritative server process.
8. The 2.5D isometric world is the primary playable view. Reliability, legibility, and depth take priority over visual spectacle, first-person work, VR, or planetary scale.
9. Luciferous/Sirix operator authority is service-derived, authenticated, audited, and outside the simulated social hierarchy. It must not manifest as an in-world supernatural status or hidden statistical advantage.
10. Settlements may develop different governments, economies, cultures, and consequences while preserving practical exit, privacy by default, and persistent citizen rights.
11. Any future keyboard, controller, VR, motion-capture, BCI, robotics, or sensor input must translate into the same shared-action representation. No device becomes authoritative.
12. Physical hardware control remains postponed. A future bridge begins as authenticated, read-only sensor measurement rather than remote actuation.

When a feature conflicts with these invariants, adapt the feature instead of weakening the model.

## Competitive position

Klang Games' SEED is a benchmark for communicating a persistent society: readable offline continuity, visible citizen routines, approachable relationship feedback, market clarity, and live-service reliability. EoV should learn from those public-facing strengths without copying proprietary content or changing into a scale-first colony MMO.

EoV's distinction is causal depth. A returning player should be able to inspect not merely that something changed, but who perceived the need, why they chose an action, which material and tools they used, which evidence supported the result, who verified it, what failed, what each participant learned, and how the outcome affects the next decision.

## Alpha 35 scope

Alpha 35 delivers one vertical slice: **The Living Workshop — restore a failing settlement water installation**.

The existing well/pump and routed-resource foundations make this a better prerequisite than smithing. The workflow exercises observation, measurement, carrying, repair/assembly, inspection, documentation, teaching, rest, social negotiation, finite materials, and infrastructure reliability. It prepares later cooking and construction without introducing another broad system.

The scenario begins when declining water output or quality creates need-generated demand. A citizen perceives evidence of the shortage, discusses it with nearby residents, and proposes a work order. A human or AI may accept, refuse, renegotiate, help, verify, or observe. Participants gather finite components from discoverable land or storage, reserve the required site and tools, diagnose the installation, attempt repair, and submit the result for independent verification. The outcome may restore service, partially improve it, or fail visibly. The causal record produces subjective memories, demonstrated competency evidence, and provisional CU valuation. Maintenance condition then influences future needs and decisions.

### Explicit non-goals

- No broad profession, combat, governance, family, child, religion, vehicle, VR, or first-person expansion.
- No real-money settlement, withdrawal, payment, token, or spendable CU.
- No autonomous model parallel to the existing society/competency/shared-action architecture.
- No planetary scale, distributed simulation, or unbounded offline processing.
- No visual overhaul beyond what is required to make this workflow traversable and understandable.
- No administrator action represented to citizens as divine intervention.

## Canonical architecture

### Shared action orchestrator

Extend the existing canonical shared-action schema and orchestrator. Do not create a workshop-specific action engine. Human commands and AI decisions produce the same proposal shape, pass through the same authorization, reservation, execution, verification, and ledger stages, and differ only in how the proposal was initiated.

Every action records an actor, perspective, intention, target, location, required capabilities, expected inputs and outputs, access basis, time cost, risk, deterministic seed where relevant, and current state. Valid states are proposed, accepted or refused, reserved, executing, succeeded or failed, awaiting verification, verified or rejected, and closed. Transitions are explicit and idempotent.

### Needs, perception, and decisions

Water availability, hydration, sanitation risk, workload, hunger, fatigue, safety, commitments, relationships, and observed evidence generate bounded needs and goals. AI initiative scores available proposals using perceived needs, goals, demonstrated competence, personality traits mapped to defined decision factors, relationships, resources, risk, expected utility, obligations, and available perceptions. It must never consult hidden authoritative state when the citizen has no evidence of it.

This replaces free-will probability and unrelated specialty counters. Refusal is a normal outcome with a recorded reason, not a conversational dead end.

### Reservations and conservation

Materials, tools, containers, stations, site access, and participant time are reserved before execution. Reservations expire or release predictably. Atomic state transitions prevent duplicate claims, double consumption, and conflicting work. Material deltas conserve quantities: consumed, transformed, damaged, recovered, and wasted amounts must reconcile with inputs.

### Measurement, experiment, and repair

The installation exposes measurable symptoms such as flow, contamination indicator, pressure, leakage, wear, alignment, or seal condition. Actions require appropriate instruments and evidence quality. Diagnosis produces hypotheses rather than omniscient truth. Repair consumes components and time, depends on competence and tool condition, and produces a deterministic but potentially unsuccessful result from recorded inputs.

### Evidence and causal ledger

Every physical change links to its action, actor, inputs, tools, measurements, site, elapsed world time, output, failure evidence, and verifier. Evidence is immutable; corrections append superseding records. The ledger answers custody and causality questions without becoming a citizen's automatic knowledge.

### Memory and competency

Subjective memories are derived only from causal events an entity perceived or learned through credible communication. Memories record confidence, source, emotional importance, relevance, and possible contradiction. Completed work and independent verification create competency evidence. Teaching may transfer a method or hypothesis, but the learner gains demonstrated competence only through subsequent practice and evidence.

### CU valuation

Verified contributions receive provisional, nonspendable CU estimates based on negotiated work, public-work priority, evidence quality, outcome utility, material value, labor/time, precision, durability, scarcity, and reproducibility. Failed work may still earn research or documentation value when it creates useful verified evidence. Valuation is an internal projection and cannot modify a wallet balance.

### Read models and UI projection

The server projects authoritative read models for the isometric client, activity feed, inspection panels, and receipts. UI projections are disposable and rebuildable; they never become authoritative simulation state. External AI/dialogue or payment providers remain behind adapters and cannot directly mutate the world.

## End-to-end action flow

The single canonical lifecycle is:

> perception → need/goal → proposed action → acceptance/refusal → resource/tool/station reservation → execution → state change → verification → causal ledger → subjective memory → competency/learning → future decision

For the water repair:

1. A deterministic world tick changes water demand and installation condition.
2. A citizen perceives a symptom available from their location and senses or instruments.
3. Their decision model forms a goal and proposes observation, discussion, measurement, supply, repair, or verification.
4. Participants negotiate scope, responsibility, access, and provisional valuation.
5. The server atomically reserves the selected inventory, tool, station/site, and time window.
6. Routed movement brings the participant within interaction range; execution consumes world time.
7. Recorded inputs, competence, tool condition, measurements, and deterministic randomness produce a material delta and evidence.
8. An eligible independent entity inspects the result and verifies or rejects it.
9. The causal ledger closes the work order and projects provisional CU.
10. Only perceiving participants receive subjective memories; evidence-backed practice updates competence.
11. Citizens reconsider water, rest, food, maintenance, and social goals from their resulting perceptions.

## Isometric play and observability

The map must remain visible, traversable, and persistent. Click-to-route movement crosses multiple tiles smoothly enough to avoid one-square command repetition. The server validates the route and interaction range; the client interpolates presentation without inventing position.

Finite resources exist as inspectable deposits, vegetation, stored goods, water sites, and recoverable components. A tile may expose multiple individually collectible items; collecting one must not require or consume an unrelated item. Discovery expands the observable map without pre-authorizing exploitation or revealing hidden composition.

NPCs visibly travel, collect, carry, measure, converse, work, pause, fail, eat, and rest. Selecting an entity or active job explains the currently perceived need, goal, destination, reservation, progress, constraint, and latest decision reason. Work must occur in the world; a menu cannot claim completion without corresponding actions.

Receipts show route, custody, material changes, measurements, inspection, and outcome. The player can return after absence and reconstruct the settlement's recent history.

## Communication and autonomy

Nearby citizens may initiate speech from their own perceptions, needs, relationships, personality, schedule, and conversational context. Directed speech makes a nearby recipient eligible to respond regardless of language, with English receiving the best initial support. Response remains a decision: the citizen may answer, defer, refuse, ask for clarification, or act later, but schedule phrases such as “the shift has ended” cannot mechanically terminate all social reasoning.

Conversation appears as proximity-weighted audible/visible chatter and persists in relevant subjective memory. Repetitive physical-impact disclaimers become a pinned interface note, not an NPC's repeated response. Accumulated speech may alter trust, rumor, agreements, goals, and eventual physical actions; the speech event itself creates no terrain or inventory delta.

## Persistence and deterministic time

One authoritative server owns each world's runclock and monotonically ordered event stream. Durable tick checkpoints contain world time, simulation version, deterministic random seed/cursor, last committed event, and pending action/reservation identifiers. Restart replays committed events after the checkpoint and safely retries idempotent pending work.

Offline catch-up is bounded by configured world duration and processing budget. It processes deterministic scheduled events in batches, persists progress, and exposes catch-up status. No client clock advances authoritative time. WebSocket clients authenticate, subscribe to projections, and may reconnect without losing or duplicating actions.

## Failure and recovery

Work stops with an inspectable reason when access, materials, energy, food, competence, tools, evidence, or verifier independence is insufficient. Failed attempts consume only recorded time and materials actually used or damaged. Citizens can revise hypotheses, seek instruction, source alternatives, rest, renegotiate, or abandon the work.

Interrupted writes use transactional or atomic conditional updates plus idempotency keys. Save recovery selects the last valid checkpoint and ledger sequence. Corrupt or incompatible records quarantine rather than silently disappearing. Client disconnection never makes the client authoritative and does not cancel accepted work unless the work's explicit policy requires the actor's continued presence.

## Security and operator boundary

All actions derive actor identity from an authenticated server session or signed service identity, never a caller-supplied user ID. WebSockets authenticate before subscription. Ownership, role, rate limits, resource access, and operator privileges are enforced centrally.

Operator actions use a separate audited service-control path with explicit confirmation for irreversible changes. Operator identity and permissions are not exposed as citizen statistics, a character power, theology, or an explanation for events. If an operator correction has an observable world effect, citizens perceive an anomaly and may form scientific or cultural interpretations from available evidence; the simulation does not reveal privileged implementation knowledge.

## Executable invariants and tests

Alpha 35 tests must cover:

- Human and AI proposals face identical access, competence, tool, material, time, and verification requirements.
- Citizens cannot act on hidden authoritative facts or receive memories for unperceived events.
- Objective state, evidence, and subjective belief may disagree without overwriting one another.
- Competence changes only from traceable teaching/practice/evidence and verified outcomes.
- Invalid action-state transitions, duplicate execution, and duplicate verification are rejected idempotently.
- Material input, output, waste, damage, and recovery quantities reconcile.
- A fixed initial state, event sequence, and random seed replay to the same result.
- Reservations prevent double use and release on expiry, refusal, rejection, failure, and closure.
- Verification independence and evidence thresholds are enforced.
- CU remains nonspendable and is calculated only as a projection from recorded contribution evidence.
- Conversation may alter beliefs and intentions but cannot directly change physical state.
- Save interruption and WebSocket reconnection do not duplicate work or lose committed history.
- Bounded offline catch-up produces the same state as equivalent online ticks.
- Authenticated identity, ownership, and operator separation cannot be overridden by request parameters.

## Alpha 35 acceptance criteria

Alpha 35 is ready for owner testing when:

1. A clean local setup can start the persistent server and client using documented commands and seeded fixtures.
2. The isometric world loads visibly, supports multi-tile click-to-route movement, persists discovery and position, and exposes individually collectible resources.
3. A water shortfall emerges from deterministic simulation state rather than a button-triggered script.
4. At least one AI citizen can perceive it, communicate, propose work, negotiate, reserve resources, travel, perform an attempt, and adapt after success or failure without player prompting.
5. A human can perform the same workflow through the same server-side action schema.
6. The repair requires physical inputs, tools, a site, measurements, competence, world time, and independent verification.
7. Success, partial success, and failure are visible and reconstructible from causal records.
8. Perceiving entities form subjective memories and verified practice changes competency; uninvolved entities do not gain the knowledge.
9. Provisional CU is shown as an evidence-backed valuation only and cannot be spent or withdrawn.
10. Restart and bounded offline catch-up preserve the runclock, work state, material conservation, citizen state, and event history.
11. Authenticated sessions and WebSockets derive Luciferous/player identity server-side; operator controls remain separate and audited.
12. Automated invariant, replay, persistence, API, and client smoke tests pass in a clean checkout.

## Sequence after Alpha 35

1. **Cooking and communal provisioning:** apply the proven workflow to nutrition, safety, heat, water, fuel, preservation, meals, morale, and the Founding Table.
2. **Construction and maintenance:** expand reusable measurement, logistics, reservations, inspection, durability, and failure mechanics to buildings and settlement infrastructure.
3. **Presentation and scale:** improve graphics, animation, audio, client responsiveness, population breadth, and eventually distributed operation only after the authoritative loop remains observable and reliable under load.

This sequence uses SEED as a quality benchmark for a world that feels alive, but keeps EoV pointed at its original purpose: a comprehensible civilization whose economic, scientific, social, and physical history emerges from accountable actions.
