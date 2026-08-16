# Discoverable Frontier Release Design

## Purpose

This milestone replaces the fixed 18×18 isometric board and its few predetermined resource sites with a dependable, persistent, traversable frontier. It must make exploration and physical work playable without creating a second simulation model or weakening the canonical shared-action invariants.

The release delivers a bounded 64×64 world now. Its storage and query boundary must permit later migration to streamed chunks without changing action semantics, causal evidence, inventory custody, or economic valuation.

## Authoritative World Model

The persistent multiplayer server owns the frontier. The client renders authenticated observations and submits intentions; it does not generate authoritative resources or accept client-supplied physical outcomes.

The initial frontier is generated deterministically from the world seed. Each tile has stable coordinates and records:

- surface terrain and elevation;
- passability and travel cost;
- visible surface features and finite resources;
- underground material strata and excavation depth;
- structures, prepared foundations, and access restrictions;
- current reservation and revision information;
- causal references for physical modifications.

Untouched tile attributes are reproducible from the seed. Persistence stores discovered knowledge and deviations from generated state rather than requiring every unchanged property to be rewritten. The world-grid interface isolates coordinate lookup, observation, mutation, and neighborhood queries so a future chunked implementation can replace the bounded backing store.

## Knowledge and Discovery

Authoritative state, evidence, and belief remain distinct.

Each player and autonomous entity has an individual discovery record. The server reveals only information supported by that entity's location, perception, and evidence:

- entering visual range reveals surface terrain and visible objects;
- `observe` improves surface descriptions;
- `survey` records layout, slope, access, and construction suitability;
- prospecting or measurement provides evidence about underground material;
- another entity learns those findings only through witnessing, communication, teaching, or access to records.

Unknown tiles remain concealed. A client must not infer deterministic hidden resources from the world seed because the seed is not an observation credential.

## Movement

The player selects a reachable destination instead of issuing repeated single-tile commands. The server computes or validates a route across adjacent passable tiles, reserves the actor's travel commitment, and advances the route with deterministic world time.

The client interpolates between authoritative route positions for smooth isometric motion. Interpolation is presentation only and cannot move an actor through an invalid tile. Travel cost depends on terrain, elevation, exhaustion, carried mass, and obstructions.

Movement stops with a visible reason when the route becomes obstructed, the actor cannot continue, the commitment is preempted by a survival need, or the request uses stale world state. Every completed route segment can expand the actor's perceived area.

## Consequential Terrain Actions

Humans and AI entities use the existing canonical pipeline:

`perception → need/goal → proposal → acceptance/refusal → reservation → execution → state change → verification → causal ledger → subjective memory → competency/learning → future decision`

The first terrain slice supports:

- exploration and progressive discovery;
- routed walking with smooth client presentation;
- finite tree harvesting;
- shallow excavation and mineral removal;
- carrying and depositing extracted material;
- surveying and preparing a buildable plot.

Harvesting and excavation require physical access, suitable tools, competence, time, energy, and finite material. Excavation changes the tile: depth increases, removed material is conserved, and the resulting pit can change passability or safety. Tree resources may regenerate only through an explicit growth process; mined minerals do not regenerate.

Extracted material enters the performer's physical inventory. It cannot teleport into communal storage or satisfy a construction input until a canonical transport/deposit action transfers custody. CU remains provisional, internal, nonspendable valuation attached to independently verified contributions.

Plot preparation requires survey evidence, acceptable slope and access, tools, labor, and inspection. This milestone prepares a foundation but does not introduce instant building placement. Later construction workflows must consume delivered materials through the same action and custody rules.

## Autonomous Participation

Autonomous residents perceive only what their current location and evidence allow. Need-generated demand or negotiated work orders may cause them to explore, survey, extract, carry, deposit, or prepare land. They cannot select hidden deposits, receive resources without travel, or bypass requirements through role names or prompts.

Initiative continues to derive from needs, goals, competence, personality, relationships, available perceptions, resources, risk, and expected utility. Human and AI actions differ only in how an intention is selected; physical execution and verification requirements are identical.

## Concurrency, Recovery, and Failure

Tile and resource mutations use expected revisions, exclusive reservations, and idempotent action identifiers. Competing actions cannot extract the same material twice or prepare the same plot through conflicting writes.

Failure remains inspectable. Actions can stop because of missing tools, inadequate access, insufficient competence, exhaustion, depleted material, unsafe excavation, absent evidence, stale revisions, or interrupted commitments. Failed and cancelled actions release reservations without creating material.

World snapshots use recoverable writes. Restart restores the last valid snapshot and applies bounded deterministic catch-up. Causal records provide enough information to audit material conservation and detect partially completed operations; replay must not duplicate commissioned output.

## Isometric Presentation

The visual direction retains EoV's dark technological-frontier atmosphere. The renderer adds:

- terrain color and texture variation;
- fog and distinct unknown boundaries;
- elevation cues;
- resource silhouettes;
- excavation and prepared-foundation marks;
- route previews and destination feedback;
- smoothly interpolated player and resident motion.

The renderer prioritizes legibility and stable interaction over advanced lighting, expensive effects, or elaborate character animation. It must remain usable when the server is temporarily unavailable by clearly showing a disconnected state; it must not silently fall back to a divergent local authoritative simulation.

## Testable Invariants

Automated tests must prove:

- identical seeds create identical untouched tiles;
- different coordinates provide stable deterministic variation;
- an entity receives no hidden tile or substrate knowledge without evidence;
- routes never cross impassable or undiscovered-for-routing tiles without a valid exploration step;
- route progress is deterministic and recoverable;
- harvested and excavated output equals the finite stock removed from its source;
- concurrent or retried extraction cannot duplicate material;
- excavation persists and changes tile depth and passability as specified;
- extracted material remains in actor custody until an explicit deposit transfer;
- subjective memory contains perceived causal events rather than omniscient state;
- human and AI performers satisfy the same tools, competence, access, time, energy, reservation, and verification rules;
- CU valuation remains nonspendable and balanced against verified evidence;
- interrupted writes reopen from a valid state without repeating output.

## Release Contents and Boundaries

The milestone release contains:

- a packaged Windows desktop client;
- an authoritative persistent server package;
- environment and configuration templates;
- database and launch instructions;
- release notes describing implemented, simulated, and deferred behavior;
- SHA-256 checksums for downloadable archives and executables.

The packages exclude test credentials, private saves, local databases, secrets, real-money activation, withdrawals, redemption, guaranteed payouts, and production-readiness claims.

The release is successful when a tester can start the server and desktop client, authenticate, enter the 64×64 frontier, click a destination and travel smoothly, discover previously unknown land, harvest or excavate a finite resource through the canonical action workflow, carry and deposit the verified output, prepare a surveyed plot, close and reopen the software, and observe the same persistent world state.

## Deferred Work

The following are deliberately outside this milestone:

- infinite or streamed world generation;
- complete structural construction and architectural editing;
- deep mines, cave simulation, collapse engineering, and groundwater flow;
- advanced lighting, skeletal animation, first-person graphics, and VR;
- real-money settlement or external CU redemption;
- making any specific input device authoritative.

Future keyboard, mouse, controller, VR, motion-capture, BCI, and robotics adapters must continue to express intentions through the same shared-action representation.
