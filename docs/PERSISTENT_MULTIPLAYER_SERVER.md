# Persistent multiplayer server

The standalone world authority is `backend/persistent_world_app.py`. It stores snapshots, revisions, leases, idempotency keys, and replayable events in a SQLite database using WAL journaling and full synchronous commits.

## Start a development server

Set a new random signing secret in `EOV_SESSION_SECRET`; never reuse a game login password. The authentication API and world authority must use the same secret. Then run from `backend`:

```powershell
$env:EOV_SESSION_SECRET = '<new-random-secret-of-at-least-32-bytes>'
$env:EOV_OWNER_USER_ID = '<persisted-Luciferous-account-UUID>'
$env:EOV_WORLD_DATABASE = '.\data\persistent-world.sqlite3'
uvicorn persistent_world_app:app --host 127.0.0.1 --port 8765
```

For a client build, set `REACT_APP_WORLD_SERVER_URL` to the public HTTPS origin before packaging. World actions use the short-lived EoV access token; the server ignores client-supplied actor identifiers and derives the actor from the signed `sub` claim.

## Authority model

- The server is the only runclock writer.
- A database lease prevents multiple server processes from advancing the same world simultaneously.
- Each tick and player action commits a monotonically increasing revision.
- Player actions carry idempotency keys and may include an expected revision.
- Stale expected revisions return a conflict instead of overwriting newer state.
- Clients read snapshots and replay events after a sequence cursor.
- Catch-up is bounded per pass and resumes until the backlog is exhausted.
- The desktop simulation runs only when no multiplayer server URL was configured.

## Audited creator influence

Schema 8 gives the bound owner a privileged proposal route without granting invisible divine intervention. `POST /worlds/{world_id}/owner-directives` requires a signed session whose subject exactly matches `EOV_OWNER_USER_ID`. The ordinary action route rejects attempts to forge `owner_directive` actions.

A directive records an objective, a recognized settlement priority, and required evidence. It has `proposal_only` scope and no immediate physical effect. The closest resident perceives and remembers it; on a later tick that resident performs a review and council knowledge records the decision. Measurable sanitation, storage, water, or food proposals become public endorsements that affect a later pressure-ranked initiative. Unmeasurable proposals are durably rejected with a reason. Submission, review, adoption or rejection, and later public work remain replayable history, and the idempotency key prevents duplicate influence after retries or restarts.

Schema 9 carries that provenance through actual work. A commissioned initiative cites the directive and council observation that caused it. Required evidence is an inspection gate: missing criteria stop completion, change the inspector's intention, and generate supplemental measurement work on later ticks. Only recovered and independently inspected work marks the directive fulfilled, changes the facility, creates provisional contribution claims, and records measured postconditions. The next pressure observation cites those completed initiatives, making the new decision demonstrably depend on the world produced by the previous decision.

## Reproducible player engineering

Schema 10 introduces the first design whose validated physics changes later gameplay. At the measurement laboratory, a player may document a lever-pump design using SI dimensions for effort arm, load arm, piston diameter, stroke, and expected efficiency. The authority calculates mechanical advantage and piston swept volume rather than accepting a claimed output.

Mira peer-reviews the dimensional prediction, Ada consumes real settlement materials to assemble the prototype, Mira measures observed flow against the prediction, and Emil independently rebuilds and reproduces it. Invalid dimensions and failed predictions remain durable negative research. Material shortages stop the lifecycle. Only a successful independent reproduction enters the tool catalog and generates balanced provisional claims for design, precision assembly, review, testing, and reproduction.

A validated pump is still not a global modifier. A player must check out a wrench, complete a well, stand beside it, and physically install the one available reproduced unit. Subsequent `draw_water` actions cite the installed design and produce measured output derived from its predicted liters per stroke. The technology therefore becomes a new world cause: documented information consumes materials, becomes reproducible hardware, changes a site, changes later labor energy and water output, and enters subsequent evidence and economic history.

Schema 11 closes the first field-technology lifecycle. Every pump cycle now persists condition loss and measured output, so output declines rather than remaining a permanent bonus. Observed wear opens one durable maintenance order; critical wear stops the pump. The order changes Ada's repair intention, Dev's supply intention, Mira's verification intention, and council knowledge. A nearby player with a wrench, timber brace, and replacement container/seal can perform the work first. Otherwise Dev assigns Ada after an observation interval and the settlement consumes accountable stores six ticks later. Missing inputs persist as blockers and targeted procurement demand instead of being silently invented. Orin draws each delivery from a recorded finite region, Dev verifies its amount, scarcity changes its provisional value, and the order retains its supply history. If all known regional stock is depleted, that fact remains unresolved until regeneration or another source changes the world. Successful supply lets Ada resume the same order; repair restores condition, records material provenance and inspection evidence, creates a balanced provisional claim, and becomes remembered history. Failure, assignment, depletion, delivery, repair, and recovered output all survive server restart.

Schema 12 connects that field machine to public survival. Water drawn at the well remains raw player inventory. At the measurement lab, `submit_water_batch` consumes a bounded amount and binds it to the latest unclaimed authoritative draw record, preventing one collection from supporting duplicate submissions. Mira tests the batch two ticks later. The deterministic safety measurement incorporates recorded pump condition: acceptable water enters communal tested supply and receives evidence-linked provisional valuation, while unsafe water is rejected without payment. Every twelve ticks, the most dehydrated residents consume available verified water and their persistent needs change. Exhausted supply can therefore generate later hydration shortages, while a newly verified batch resolves the shortage and changes subsequent NPC priorities.

Schema 13 removes the player as a required trigger for that survival loop. A recorded hydration shortage proposes a persistent communal-water work order. Emil receives the collection assignment, moves one authoritative tile per tick to the well, uses finite site stock and communal tools, records pump wear, carries the raw batch back to the measurement laboratory, and waits for Mira's existing independent test. An incomplete well, exhausted stock, failed pump, or exhausted worker blocks the order with a reason. Rejected water returns the same obligation to a quality-blocked state; pump maintenance can then change the source conditions and cause an autonomous retry. The successful second batch resolves the shortage and completes the original work order without erasing the failed attempt.

Schema 14 makes worker dependency actionable. A hungry resident walks one tile per tick toward the communal kitchen and consumes one finite safe meal; the evidence record preserves the cook, input, location, need before and after, and remaining portions. With no meal available, one persistent shortage accumulates affected residents and adds measured food pressure to the council rather than inventing supply. A fatigued resident travels to their household or recovery room and rests over multiple ticks. Public work stores the exact interrupted phase, so a carrier who becomes exhausted while collecting or delivering water recovers first and then resumes that phase without duplicating the collection. Movement, consumption, shortages, rest, recovery memories, and resumed work survive restart.

Schema 15 turns that meal pressure into kitchen production. An unresolved safe-meal shortage commissions a persistent cooking order with portions, raw food, tested water, fuel, Lena as cook, and Imani as inspector. Missing ingredients block the order and normal finite-stock procurement can later recover it. Assigned work reserves its tested-water requirement so ordinary drinking cannot consume already committed inputs. Lena walks to the operational kitchen, preparation consumes inputs and time, and Imani walks in to inspect the recorded batch. Only an accepted safety result adds portions, culture, memories, and balanced provisional claims. Hungry residents then consume those portions, closing the same shortage that commissioned the work.

Schema 16 replaces anonymous meal counts with aging batch inventory. Every accepted batch records remaining portions, preservation method, storage-derived shelf life, and expiration tick. Hungry residents consume the accepted batch nearest expiration and the evidence record identifies that batch. When shelf life expires, all unconsumed portions leave safe inventory, enter persistent waste history, inform council knowledge, and create a causal loss record. If a resident is already hungry, spoilage can create a replacement cooking order in the same tick: prior production becomes waste, waste becomes shortage, and shortage becomes new work.

Schema 17 lets the institution learn from accumulated waste. Three lost portions propose a drying trial linked to the specific expired batches. The trial requires raw food, fuel, a container, Lena's labor, Imani's inspection, and four ticks; missing inputs persist until finite procurement supplies them. A successful measured trial becomes cultural and technical practice rather than a global bonus. Later cooking orders explicitly reserve one container and additional fuel, label the resulting batch as dried, and derive 24 additional shelf-life ticks from the validated program. Waste therefore changes research, research changes material demand, and verified knowledge changes later physical outcomes.

Schema 18 adds accumulated social causality. Nearby NPC witnesses can retain a player's civic concern as a discourse claim, but speech has no direct physical effect. Repetition in the same tick is collapsed, and a concern enters the council record only after it has been heard on three distinct ticks by at least two witnesses. The resulting public pressure is durable, auditable, and incorporated into a later council evidence review. If that review selects the concern, the existing negotiated, supplied, inspected public-work lifecycle performs any eventual physical change. Words can therefore influence history through accumulated social and institutional consequences without functioning as geography-changing commands.

Schema 19 removes the player as a prerequisite for social history. Once the settlement has completed its founding work and has institutional experience, autonomous residents voice concerns derived from measured settlement pressures even when nobody is connected. Only residents within audible proximity become witnesses. They retain private source memories, while qualifying multi-witness discussion enters Sora's public record with message, speaker, witness, topic, and tick provenance. Residents can later choose to continue discussing a remembered concern, and accumulated concern influences the next available council review. This produces an AI-originated loop of observation, communication, learning, intention, institutional interpretation, and further work.

Schema 20 makes relationship history operational. Dev's trust in an actor is derived from recorded custody outcomes and now affects future access and dialogue. Trust below the ordinary-access threshold creates a durable, rate-bounded refusal record containing the decision maker, trust value, reason, and remedy. It does not create permanent exclusion: an actor without unresolved restitution may request a one-unit supervised checkout, return it through the same custody ledger, and rebuild trust. Successful recovery closes the refusal record, restores ordinary access once the threshold is reached, changes Dev's explanation, and becomes a new causal record. Repeated supervised agreements provide a path back even from zero trust.

Schema 21 turns severe local tree depletion into autonomous ecological work. A tree site at or below one quarter of capacity creates a durable stewardship order after founding. The order reserves finite seed and tested water, blocks visibly when either is missing, and resumes when supply changes. Cal and Mira travel from their actual tiles to the depleted site; planting creates a measured baseline and a delayed recovery period rather than instant stock. Mira's later inspection restores only the surviving amount to both site and regional inventories, updates the timber valuation signal, and supports provisional CU claims for verified labor and inspection. The order closes only after both residents return to the settlement. Depletion, blockers, travel, planting, elapsed recovery, measurement, valuation, return, and memory all persist across restarts.

Schema 22 makes verified practice teachable. Completing stewardship establishes Cal's demonstrated environmental-stewardship competency and Mira's ecological-inspection competency, then creates a teaching order linked to the exact restoration evidence. Instructor and learner must be safe to work and meet at the hall; instruction takes four ticks and can pause for survival needs. Rae receives competency only after a documented demonstration inspected by Mira. Instruction and demonstration receive separate provisional CU estimates. Later stewardship assignment selects a safe qualified resident from persistent competency records, so an unavailable Cal causes trained Rae to receive the next restoration order. Work therefore changes knowledge, knowledge changes capability, and capability changes later autonomous labor allocation.

Schema 23 gives environmental labor an explicit provisional contract. Local depletion and regional timber scarcity derive an urgency/scarcity multiplier; worker and inspector publish role-specific asks, Sora records treasury counteroffers on a later tick, and the parties accept negotiated midpoints on another tick. Stewardship cannot reserve materials or begin travel before acceptance. Mira's verified surviving-stock measurement determines Cal or Rae's outcome ratio, while independent inspection retains its agreed value. Claims and journal records reference the contract, valuation inputs, outcome, evidence, and `spendable: false`. The isometric panel shows agreed provisional terms and the multiplier without presenting CU as withdrawable currency.

## Recursive civic causality

After the Founding Table, the authority does not stop at a completed mission. On recurring evidence reviews it:

1. Measures pressures from resident needs, resource inventories, and facility condition.
2. Persists those observations as council knowledge and ranks a public agenda.
3. Creates the highest-pressure sanitation, storage, water, or food initiative.
4. Accepts, supplies, performs, and independently inspects that work over later ticks.
5. Records evidence, memories, provisional contribution claims, and explicit cause/effect links.
6. Changes facilities, food storage, water dependability, meals, and inventories.
7. Measures the changed settlement again to decide what happens next.

Authenticated players can submit `endorse_priority` actions. An endorsement changes the next council pressure review, but cannot directly create a physical result. If an initiative lacks material, it records a failure and creates measured procurement work against finite environmental stocks. Successful procurement recovers the failure on a later tick; depleted stocks remain a persistent blocker for future systems to answer.

## Witnessed conduct and due process

Schema 3 adds a spatial social consequence chain:

1. An authenticated player joins at a server-validated tile and moves one adjacent tile per action.
2. `misappropriate_resource` physically transfers a bounded quantity from settlement stock to that player's authoritative inventory.
3. Only NPCs within perception range form firsthand memories. Distance affects confidence and personal trust; an unwitnessed act does not magically enter institutional knowledge.
4. Autonomous witnesses decide to report after time passes. Reports open an investigation rather than immediately imposing punishment.
5. Sora substantiates a case only when a physical conduct record and credible firsthand report coexist. A failed evidence test closes the case without penalty.
6. A substantiated case creates a visible restitution obligation and a recovery deadline. Only then does public reputation change.
7. `return_resource` restores the exact held and owed material, closes the case, records recovery, and cancels any active bounty.
8. Ignoring the deadline creates a provisional public bounty and changes Orin's later intention to recovery duty. The reward is valuation data, not spendable CU.

World snapshots and replay reads now require the signed session used for writes. Other players' inventories, NPC-private memories and relationships, witness identities, and reports unrelated to the requesting actor are removed from their view. An accused player retains access to reports used in their own case. WebSocket streams authenticate with the `eov-session` subprotocol followed by the short-lived access token; tokens are not accepted in the URL.

## Spatial recovery duty

Schema 4 continues an expired restitution case rather than ending at a decorative bounty:

- A bounty remains open for two ticks so authenticated players have the same opportunity to accept it as an autonomous resident.
- The first accepted assignment wins atomically inside the authoritative action transaction. A subject cannot accept their own bounty.
- If nobody accepts, Orin autonomously takes the assignment, provided survival needs permit the work.
- NPC recovery moves one tile per tick toward the subject's last persistent location. Player recovery uses the same server-validated adjacent movement action.
- Recovery requires co-location and a documented restitution request. Remote inventory return is rejected after escalation.
- Before escalation, voluntary return must physically occur at the meeting hall.
- No reward claim exists for acceptance, travel, or mere contact. Only complete material restoration creates the evidence-linked provisional public-recovery claim.
- Player and NPC collectors receive the same 6.0 provisional-CU valuation. It remains non-spendable shadow accounting.
- Completed recovery restores settlement stock, closes the case, changes reputation, closes the bounty, writes causal history, and keeps the ledger balanced.

The isometric client now joins and moves through authoritative multiplayer actions when connected to the world server. It displays open duties, allows players to accept them, records co-located restitution requests, and lets subjects return the exact owed materials when the physical conditions are satisfied.

## Institutions learn from history

Schema 5 makes a substantiated incident capable of changing later economic behavior without imposing an unexplained global restriction:

1. A substantiated stock case becomes evidence available to governance.
2. At the next council review, Sora and Dev propose recorded checkout while keeping general access available through a legible process.
3. The proposal remains pending for a separate deliberation interval. It cannot become policy in the same tick that it is proposed.
4. The next review enacts the rule and writes the proposal-to-world-rule causal link.
5. Players at the meeting hall can receive bounded material custody with a purpose, quantity, borrower, issue tick, and due tick.
6. On-time return restores stock, improves public reputation and Dev's personal trust, and becomes positive remembered history.
7. An overdue record changes Dev's intentions, council knowledge, personal trust, reputation, and the borrower's future checkout access.
8. Returning overdue material records recovery, partially repairs standing, and reopens future access. Delinquency is therefore consequential but not permanent exile.

The resulting loop is historical rather than scripted: conduct creates evidence; evidence causes deliberation; deliberation changes available actions; those actions create obligations; fulfillment or neglect changes relationships and future access. The isometric authority panel displays the live policy, proposal rationale, player inventory, active checkouts, due ticks, and return controls.

SQLite is appropriate for the first single-authority settlement. Before multi-region operation, move the same transaction and lease semantics to PostgreSQL rather than sharing the SQLite file over a network filesystem.
