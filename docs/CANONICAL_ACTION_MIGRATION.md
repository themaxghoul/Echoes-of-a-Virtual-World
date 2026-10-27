# Canonical action architecture migration

Updated: 2026-08-09

## Branch decision

The open remote branches were inspected before implementation. PR #5,
`agent/desktop-foundation-alpha`, is the most advanced coherent committed
foundation: it contains the recoverable desktop boundary and subsumes the
isometric work in PR #4. PR #3 is a broad legacy prototype line containing
direct wallet rewards, independent skills, and request-driven mutations that
conflict with the current invariants.

The current `agent/virtuconomy-cu-valuation` working tree contains substantial
uncommitted Alpha.32 work newer than PR #5: the depth roadmap, autonomous
society foundation, persistent world, competency engine, causal ledger,
security boundary, and desktop regression fixes. It is therefore the active
consolidation source. No PR was blindly merged and no dirty work was discarded.

## System disposition

| System | Disposition | Migration rule |
| --- | --- | --- |
| `persistent_world.py` | Retained, then adapted | Remains durable clock/state owner. Its scenario reducers must migrate behind canonical action commands incrementally. |
| `causal_ledger.py` | Retained as authority | Every consequential shared action transition appends a hash-linked event. |
| `competency_engine.py` | Retained and authoritative | Demonstrated, evidence-bearing competency is the only expertise source. |
| `society_engine.py` | Adapted | Specialties are now projections of demonstrated competency; decisions use deterministic feasible utility. |
| `ai_autonomy_router.py` | Deprecated as an execution authority | Retained as an API compatibility adapter. It may select proposals; it may not bypass reservations, execution, verification, or the ledger. |
| Legacy `free_will` probability | Replaced | Initiative is derived from needs, goals, personality/category alignment, relationships, demonstrated competence, resources, perceptions, risk, and expected utility. |
| Legacy memory arrays/global knowledge | Adapted/deprecated | New memory is subjective belief derived from perceived causal events. Authoritative state and evidence remain separate. |
| Independent specialty/skill XP counters | Deprecated | Titles, prompts, and arbitrary XP cannot establish competence. |
| Direct wallet/reward/payment paths | Quarantined | CU is balanced, integer internal valuation attached to verified evidence and remains non-spendable. |
| Operator/owner controls | Retained outside simulation | Operator capability can administer infrastructure but is never an in-world supernatural rank or action advantage. |
| Lore catalogs | Scenario-only | Demons, governments, materials, recipes, names, and similar definitions do not belong in the action kernel. |

## Canonical vertical slice

`action_engine.py` implements measurement-tool calibration as the prerequisite
workflow before cooking heat control or smithing. A degraded/uncertain measuring
tool creates safety demand. Human and AI actors use the same definition and
must pass the same perception, material, tool condition, station, energy,
competency, timing, and independent-verification gates.

The completed lineage is:

`proposed -> accepted/refused -> reserved -> in_progress -> submitted/failed -> verified/needs_rework -> commissioned`

Execution consumes a finite reference strip and energy, wears the tool, advances
deterministic ticks, and records ordered readings. Missing readings fail with an
inspectable cause. Excess spread requires rework. Only independently verified
output can be commissioned. Commissioning creates equal-and-opposite integer
CU valuation postings and a non-spendable evidence claim. Subjective memory is
created only for entities that perceived the relevant causal event.

Schema 24 now persists these records, reservations, causal events, material
consumption, competency provenance, memories, and balanced milli-CU valuation
inside the same SQLite world transaction. The runclock can generate a degraded
tool demand and an eligible AI entity can propose the same calibration action a
human uses. Restart/replay tests cover both actor kinds. Snapshot, HTTP event,
and WebSocket projections redact uncommissioned evidence from remote entities;
physical presence at the measurement laboratory permits observation.

The runclock now advances need-originated AI calibration without privileged
mutation. It invokes the same `accept`, `reserve`, `execute`, `verify`, and
`commission` commands exposed to human clients, performs no more than one
gated transition per action per tick, moves performer and verifier into physical
range, and derives instrument readings from deterministic tool condition.
Founding measurement competence is limited to named pre-settlement practice
records with explicit provenance; neither role labels nor prompts create it.

## Interaction and presentation corrections

Autonomy no longer means blanket refusal or silence. Addressed NPC speech is
routed to the selected nearby entity, produces bounded context-sensitive
responses, records conversational memory, and remains non-physical unless a
later consequential action passes the canonical pipeline. Autonomous chatter
may continue without treating dialogue as direct geography mutation.

The isometric client validates and repairs sparse legacy snapshots before
rendering. Click-to-walk and held-key movement interpolate visually across a
multi-tile route while the server continues to authorize each adjacent step.
This keeps movement responsive without allowing the renderer or input device to
become a second world-state authority.

The laboratory is now an operable isometric work surface. It projects current
demand, tool condition, perspective access, demonstrated competence, action
lineage, ordered readings, performer, verifier, and inspectable output. Human
participants submit the same durable commands used by autonomous scheduling;
server rejection reasons remain visible instead of being bypassed in the UI.

## Schema 25: canonical survival production

New communal meal work no longer uses the legacy cooking reducer as its state
authority. Hunger creates a durable survival-production demand that selects an
entity through demonstrated cooking competence. The actor must accept the work,
travel to the communal kitchen, reserve finite raw food, tested water, fuel,
cooking pot, thermometer, and hearth, then submit a measured thermal history.
The deterministic thermal model derives safety, quality, peak temperature, and
heated duration from those observations. It does not accept a prompt assertion
that food is safe.

A distinct entity with demonstrated food-safety competence must be physically
present to inspect the submitted batch. Only a passing inspection permits
commissioning, safe-meal inventory, shelf-life tracking, cultural recipe
provenance, subjective memories, competency evidence, and balanced non-spendable
CU valuation. Undercooked batches enter `needs_rework` and create no trusted
food or valuation. Human and AI actors use the same definition and gates.

Existing legacy cooking orders may finish through the compatibility reducer,
but it no longer creates new authoritative meal work. Its work-order and batch
shapes are retained as read projections for survival consumption, spoilage,
preservation, UI compatibility, and migration history.

## Schema 26: reproducible apprenticeship

Instruction no longer grants demonstrated competence or produces CU merely
because a teacher and learner waited through a lesson timer. A teaching action
now follows a hash-linked multi-party lineage:

`proposed -> awaiting_acceptances -> accepted -> reserved -> in_progress -> submitted -> verified -> commissioned`

The instructor must possess competence derived from a verified source outcome.
Instructor and learner consent independently, survive safely enough to
participate, travel to the same meeting place, reserve the instruction table,
and perceive both language and the underlying record. Instruction raises only
bounded theory, observation, and procedure. The learner's demonstrated value is
unchanged, no valuation claim is created, and subjective memory explicitly says
that verified practice is still required.

Commissioned instruction creates a supervised-practice obligation. The next
compatible real production opportunity may assign the learner only when a
competent supervisor is available. For the first complete slice, Rae performs a
finite reforestation order under Cal's supervision while Mira independently
inspects the ecological outcome. Only the restored, measured stock establishes
Rae's demonstrated environmental-stewardship competence and future assignment
eligibility. Human learners use the same authenticated `learner_accept` or
`learner_refuse` action available to autonomous residents.

## Schema 27: cross-domain specialist reproduction

The apprenticeship adapter is no longer created only by the stewardship
scenario. Commissioned calibration and communal-meal actions can project their
verified event into a teaching opportunity for measurement or cooking. The
adapter refuses to create a lesson unless the proposed instructor's competency
provenance contains that exact verified event.

Practice obligations can now participate in later shared-action demand. A
novice may reserve work below the normal competence threshold only when all of
the following remain true: prior instruction produced nonzero theory,
observation, and procedure; the matching practice obligation was assigned to
this action; a competent supervisor is physically present; and the ordinary
materials, tools, station, energy, perception, timing, and independent-verifier
requirements all pass. The supervisor cannot serve as the independent verifier.

Successful verification stages a bounded competency outcome, but it does not
become authoritative until the verified output is commissioned. Commissioning
then closes the practice obligation, records the verification event as
competency provenance, and allows later unsupervised work. Tests exercise this
full reproduction loop for both environmental stewardship and measurement;
the same adapter is connected to canonical cooking demand.

## Schema 28: field maintenance through the shared kernel

Mechanical pump repair is now a canonical `condition_restoration` action. A
governance maintenance order remains as a readable projection, but it no longer
consumes supplies, assigns invisible verification, changes pump condition, or
issues value itself.

Pump wear, maintenance demand, procurement history, depletion notices,
installed-pump history, and the isometric site interaction are retained.
`maintain_pump` is adapted to propose or locate canonical work. Fixed laboratory
location assumptions are replaced by structural place-or-resource-site
resolution, and station reservations are optional for genuine field work.

The old delayed maintenance reducer and `_complete_pump_maintenance` are
deprecated as authoritative mutation paths and retained only for legacy-state
read compatibility. A pump becomes operational only after independently
verified evidence is commissioned. Restocked materials do not bypass
perception, competence, tool condition, energy, custody, or verification gates;
CU remains nonspendable internal valuation.

## Schema 29: actor and time custody

Canonical consent now creates a persistent actor commitment. The same human or
AI entity cannot accept a second consequential action while committed to the
first. Commitments cover travel, reservation, execution, and the wait for
independent review; supervised work also commits its supervisor.

Legacy schedulers may still project needs and intentions, but cannot move an
actor claimed by a different canonical action. Critical eating and rest may
preempt movement without erasing the action, allowing work to pause and resume
under the ordinary need and energy gates. Owner-aware adapters, such as the
teaching projection, may move their own canonical participants.

Commissioning, refusal, inspectable failure, rework, and explicit participant
cancellation release actor custody. Cancellation of accepted or reserved work
also releases tools, stations, and reservation records without consuming
materials. Migration reconstructs commitments deterministically from active
records after restart.

## Schema 30: finite extraction and physical custody

Finite site extraction uses the shared action lifecycle for human and AI
performers. A site and its corresponding regional stock are reserved and
conserved together, output awaits independent stock-and-yield verification,
and commissioned material enters the performer's inventory rather than
teleporting into communal stores. Provisional CU remains nonspendable.

## Schema 31: observed frontier and terrain custody

The authoritative world now owns a deterministic 64×64 frontier. Each entity
has private discovery evidence; player snapshots contain only observed tiles
and never expose the seed or unobserved substrate. Server routes advance on
deterministic ticks and persist through restart.

Surveyed frontier tiles can project a finite surface or substrate source into
the existing extraction lifecycle. Excavation mutates sparse tile depth and
stock only during execution, independent verification controls custody release,
and commissioned output remains actor-held until a physical warehouse deposit.
Plot preparation consumes held material and records survey and causal evidence.
Legacy regional procurement remains an adapter slated for replacement; it does
not automatically procure new frontier materials.

## Adapter boundary and next migration

The new kernel and its durable adapter are canonical for new consequential
work, but existing persistent-world reducers still encode several workflows
directly. They remain working behind the durable-world boundary while being
migrated one workflow at a time. Keyboard, mouse, autonomous planners, and
future controller, VR, BCI, or robotics adapters must submit canonical commands;
no device-specific path may mutate world state directly.
