# Alpha 35 Living Workshop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Alpha 35 as a reproducible Windows client and persistent server in which either a human or an autonomous citizen can detect, negotiate, perform, verify, remember, and value a failing-water-installation repair through the same authoritative action lifecycle.

**Architecture:** Extend the existing `SharedActionEngine` and SQLite-backed `PersistentWorldStore`; do not create another simulation or citizen model. Scenario definitions supply the water installation and repair recipe, while the kernel owns transitions, reservations, deterministic execution, evidence, memory, competency, and nonspendable CU projection. The React/Electron client renders authenticated server projections, routes actors smoothly between server positions, and explains active work without owning simulation state.

**Tech Stack:** Python 3 dataclasses and standard library, SQLite event store, FastAPI/WebSockets, React 19, Electron 37, Node test runner, Playwright, pnpm, PowerShell release tooling.

**Spec:** `docs/superpowers/specs/2026-09-10-alpha35-living-workshop-design.md`

## Global Constraints

- Humans and AI citizens use identical consequential-action gates and transitions.
- Authoritative state, immutable evidence, and subjective belief/memory remain separate.
- Competence changes only through traceable instruction, practice, evidence, and verified outcomes.
- Speech cannot directly mutate terrain, inventory, installations, or other physical state.
- CU remains an internal, nonspendable valuation projection with no redemption or withdrawal path.
- One server owns deterministic world time, event order, offline catch-up, and recovery.
- The server derives actor identity from an authenticated session; request bodies and URLs cannot override it.
- Operator authority is world-scoped, service-derived, separately audited, and absent from simulated social status.
- The client sends intentions and renders projections; it never commits physical state locally.
- Alpha 35 implements only the Living Workshop water-repair vertical slice and supporting reliability work.
- Preserve the unrelated working-tree changes in `backend/economy/settlement_projection.py` and `backend/tests/test_settlement_projection.py`.

## File structure

- Create `backend/scenarios/__init__.py`: scenario package boundary.
- Create `backend/scenarios/living_workshop.py`: water-installation scenario catalog, measurement definitions, repair recipe, and seeded demand thresholds.
- Modify `backend/action_engine.py`: canonical lifecycle metadata, expiry/release rules, deterministic repair result, material reconciliation, and verification outcome.
- Modify `backend/society_engine.py`: bounded initiative scoring with explicit factors and normalized personality mappings.
- Modify `backend/competency_engine.py`: evidence-derived repair/measurement learning; no profession counters.
- Modify `backend/persistent_world.py`: schema migration, water demand, autonomous workflow orchestration, persistence, subjective memory projection, and offline replay.
- Modify `backend/persistent_world_app.py`: authenticated workshop reads/actions and WebSocket projection events.
- Create `backend/tests/test_living_workshop.py`: end-to-end human/AI, failure, replay, memory, valuation, and recovery invariants.
- Modify `backend/tests/test_action_engine.py`: pure canonical repair and reservation tests.
- Modify `backend/tests/test_society_engine.py`: bounded-knowledge initiative tests.
- Modify `backend/tests/test_persistent_world.py`: migration, identity, catch-up, and restart tests.
- Create `frontend/src/lib/livingWorkshopView.cjs`: pure server-snapshot projection for work, explanations, receipts, and water status.
- Create `frontend/src/lib/livingWorkshopView.test.cjs`: projection and redaction tests.
- Modify `frontend/src/lib/worldServer.js`: shared-action and workshop read helpers using authenticated headers.
- Modify `frontend/src/pages/IsometricSettlement.jsx`: server-observed workflow controls, multi-tile route presentation, and work explanation.
- Modify `frontend/src/pages/IsometricSettlement.css`: status, route, worker, evidence, and failure presentation.
- Modify `frontend/src/components/AuthoritativeWorkPanel.jsx`: stage, blocker, custody, verification, and CU receipt display.
- Modify `frontend/src/lib/autonomousChatter.js`: proximity conversation projection without physical effects.
- Modify `frontend/src/lib/isometricInteractions.test.cjs`: individual-resource and routed-interaction regression coverage.
- Modify `frontend/electron/authoritative-world-view.test.cjs`: workshop projection integration.
- Modify `frontend/e2e/isometric.spec.js`: visible persistent workflow smoke test.
- Modify `frontend/package.json`: Alpha 35 version and Node test registration.
- Create `scripts/package_alpha35_release.ps1`: deterministic client/server archives and checksums.
- Create `scripts/verify_alpha35_release.ps1`: clean-extraction, secret, database, version, and health verification.
- Create `docs/ALPHA35_RELEASE_NOTES.md`: demonstrable feature matrix, setup, known limits, and test evidence.
- Modify `docs/CANONICAL_ACTION_MIGRATION.md`: retained/adapted/deprecated/replaced architecture record.
- Modify `backend/ALPHA34_WORLD_SERVER.env.example`: rename through Git to `backend/ALPHA35_WORLD_SERVER.env.example` and document Alpha 35 settings without credentials.

---

### Task 1: Scenario Boundary and Canonical Repair Definition

**Files:**
- Create: `backend/scenarios/__init__.py`
- Create: `backend/scenarios/living_workshop.py`
- Modify: `backend/action_engine.py`
- Modify: `backend/tests/test_action_engine.py`

**Interfaces:**
- Produces: `WaterInstallationSpec`, `living_workshop_seed() -> dict[str, object]`, `water_installation_repair(spec: WaterInstallationSpec) -> ActionDefinition`.
- Extends: `ActionRecord` with `accepted_tick`, `completed_tick`, `verification`, and `material_reconciliation`.
- Produces execution model `water_installation_repair`, whose samples contain `flow_lpm`, `leak_rate_ml_min`, `contamination_index`, `pressure_kpa`, and `seal_alignment_mm`.

- [ ] **Step 1: Write failing pure-kernel tests for identical gates and conserved repair materials**

```python
def test_water_repair_has_identical_human_and_ai_requirements(self):
    outcomes = []
    for kind in ("human", "ai"):
        worker = domain_actor(f"{kind}-worker", kind, "mechanical_repair", perceptions={"spatial_layout", "instrumentation"})
        outcomes.append(run_water_repair_to_submission(worker))
    self.assertEqual(outcomes[0]["consumed"], outcomes[1]["consumed"])
    self.assertEqual(outcomes[0]["duration_ticks"], outcomes[1]["duration_ticks"])
    self.assertEqual(outcomes[0]["state"], "submitted")

def test_repair_material_reconciliation_balances(self):
    record = run_water_repair_to_submission(domain_actor("worker", "human", "mechanical_repair"))
    self.assertEqual(record["before"] - record["consumed"], record["after"])
    self.assertEqual(record["consumed"], record["installed"] + record["waste"] + record["recovered"])
```

- [ ] **Step 2: Run `python -m unittest backend.tests.test_action_engine -v` and verify failure for the missing scenario module and repair execution model**
- [ ] **Step 3: Create the scenario catalog with a `WaterInstallationSpec` dataclass and a `water_installation_repair()` definition requiring seal material, fasteners, wrench, calibrated measure, installation site, mechanical-repair competence, instrumentation perception, energy, and duration**
- [ ] **Step 4: Extend `SharedActionEngine.execute()` with deterministic repair calculation derived only from recorded pre-measurements, demonstrated competence, tool condition, specification tolerances, and `sha256(action_id + deterministic_seed)`; record installed, recovered, damaged, and waste quantities**
- [ ] **Step 5: Make `verify()` accept explicit post-repair samples, independently decide `verified` or `rejected`, and include tolerance comparison plus material reconciliation in the causal event**
- [ ] **Step 6: Run the action-engine suite and confirm calibration, meals, extraction, custody, and repair all pass**
- [ ] **Step 7: Commit the scenario boundary and canonical repair kernel**

```powershell
git add backend/scenarios backend/action_engine.py backend/tests/test_action_engine.py
git commit -m "feat: add canonical water repair action"
```

### Task 2: Explicit Initiative Model and Competency Provenance

**Files:**
- Modify: `backend/society_engine.py`
- Modify: `backend/competency_engine.py`
- Modify: `backend/tests/test_society_engine.py`
- Modify: `backend/tests/test_competency_engine.py`

**Interfaces:**
- Produces: `DecisionContext(perceived_needs, goals, relationships, resources, risks, obligations, personality)`.
- Produces: `score_option(agent: Agent, option: DecisionOption, context: DecisionContext) -> DecisionScore` with named components `need`, `goal`, `competence`, `relationship`, `resource`, `risk`, `utility`, `obligation`, and `personality`.
- Produces: `record_practice_evidence(profile, domain, action_id, evidence_ids, verified, quality) -> Competency`.

- [ ] **Step 1: Write failing tests proving hidden facts cannot affect initiative and personality traits map to defined factors**

```python
def test_unperceived_water_failure_does_not_change_decision_score():
    visible = decision_context(perceived_needs={"hydration": 0.8})
    hidden = decision_context(perceived_needs={"hydration": 0.8}, authoritative_only={"pump_failure": 1.0})
    self.assertEqual(score_option(ada, repair_option, visible), score_option(ada, repair_option, hidden))

def test_personality_components_name_real_decision_factors():
    score = score_option(ada, repair_option, decision_context())
    self.assertEqual(set(score.personality), {"diligence", "sociability", "caution", "curiosity", "cooperation"})
```

- [ ] **Step 2: Run `python -m unittest backend.tests.test_society_engine backend.tests.test_competency_engine -v` and verify the new context and scorer are absent**
- [ ] **Step 3: Replace opaque free-will weighting with a deterministic weighted score whose complete component breakdown is returned for inspection; retain `decide_initiative()` as an adapter calling the new scorer**
- [ ] **Step 4: Normalize legacy personality inputs into the five named traits and reject unknown action-category modifiers instead of silently applying them**
- [ ] **Step 5: Route teaching to unverified familiarity and route verified practice to demonstrated competency with action/evidence provenance; make specialization a read-only projection of highest demonstrated domains**
- [ ] **Step 6: Run both suites and assert no title, profession, prompt text, or unverified lesson increases demonstrated competence**
- [ ] **Step 7: Commit initiative and competency consolidation**

```powershell
git add backend/society_engine.py backend/competency_engine.py backend/tests/test_society_engine.py backend/tests/test_competency_engine.py
git commit -m "refactor: ground initiative in perceived evidence"
```

### Task 3: Durable Living Workshop State and Need-Generated Demand

**Files:**
- Modify: `backend/persistent_world.py`
- Create: `backend/tests/test_living_workshop.py`
- Modify: `backend/tests/test_persistent_world.py`

**Interfaces:**
- Consumes: `living_workshop_seed()`, `water_installation_repair()`, `score_option()`, and `record_practice_evidence()`.
- Produces state keys `installations.water`, `living_workshop.demands`, `living_workshop.work_orders`, `living_workshop.measurements`, and `living_workshop.recent_outcomes`.
- Produces: `_process_living_workshop(state: dict, tick: int) -> list[dict]` called exactly once per tick by `reduce_world_tick()`.

- [ ] **Step 1: Write a failing migration test that upgrades an Alpha 34 save without resetting runclock, frontier discovery, actors, inventory, or ledger sequence**

```python
def test_alpha34_save_migrates_living_workshop_without_losing_history(self):
    before = alpha34_fixture_state()
    after = migrate_state(before)
    self.assertEqual(after["clock"], before["clock"])
    self.assertEqual(after["discoveries"], before["discoveries"])
    self.assertIn("water", after["installations"])
    self.assertEqual(after["shared_actions"]["ledger"], before["shared_actions"]["ledger"])
```

- [ ] **Step 2: Write failing demand tests showing declining flow or unsafe quality creates one idempotent demand from perceived evidence, while healthy water creates none**
- [ ] **Step 3: Run `python -m unittest backend.tests.test_living_workshop backend.tests.test_persistent_world -v` and verify the migration and processor failures**
- [ ] **Step 4: Add the next schema migration and seed a water installation with condition, finite service capacity, measurement history, maintenance interval, location, and no omniscient diagnosis**
- [ ] **Step 5: Implement deterministic deterioration and local symptoms; generate demand only after an eligible entity perceives the symptom or receives credible evidence**
- [ ] **Step 6: Use the canonical shared-action command adapter to create the repair proposal; store the decision-score explanation and perceived evidence IDs, not hidden causes**
- [ ] **Step 7: Register `_process_living_workshop()` in one stable position in `reduce_world_tick()` and prevent the legacy `_process_autonomous_water_work()` and `_process_maintenance()` paths from opening duplicate repair orders**
- [ ] **Step 8: Run the living-workshop and persistent-world suites and confirm exactly one demand/action exists across repeated ticks and process restart**
- [ ] **Step 9: Commit durable demand generation and migration**

```powershell
git add backend/persistent_world.py backend/tests/test_living_workshop.py backend/tests/test_persistent_world.py
git commit -m "feat: generate durable water repair demand"
```

### Task 4: Negotiation, Reservations, Routed Execution, and Failure Recovery

**Files:**
- Modify: `backend/persistent_world.py`
- Modify: `backend/tests/test_living_workshop.py`
- Modify: `backend/tests/test_persistent_world.py`

**Interfaces:**
- Produces commands `negotiate_work_order`, `respond_work_order`, and existing `shared_action` operations for reservation/execution/verification/commission.
- Work-order records expose `status`, `proposer_id`, `candidate_ids`, `assigned_actor_id`, `verifier_id`, `terms`, `decision_explanation`, `blockers`, and `canonical_action_id`.
- Reservations expose `expires_tick`, `materials`, `tools`, `station`, `site`, and `actor_time`.

- [ ] **Step 1: Write failing end-to-end tests for AI acceptance, refusal with reason, player acceptance, concurrent reservation conflict, expiry release, shortage stoppage, fatigue stoppage, and retry after supply/rest**

```python
def test_worker_can_refuse_and_another_actor_can_accept_same_order(self):
    order = create_perceived_water_demand(self.store)
    refused = respond(self.store, "orin", order["id"], accepted=False, reason="risk exceeds my demonstrated competence")
    accepted = respond(self.store, "ada", order["id"], accepted=True)
    self.assertEqual(refused["status"], "refused")
    self.assertEqual(accepted["assigned_actor_id"], "ada")
```

- [ ] **Step 2: Run the named tests and verify failure at missing negotiation and reservation-expiry behavior**
- [ ] **Step 3: Implement negotiation as append-only proposals/responses; never overwrite a refusal, and bind final terms to the canonical action ID**
- [ ] **Step 4: Extend reservations with deterministic expiry and atomic release of material, tool, station, site, and actor commitment on refusal, cancellation, rejection, failure, closure, or timeout**
- [ ] **Step 5: Require a server-approved route to interaction range before execution; advance the actor one route segment per tick and expose destination/reason/progress**
- [ ] **Step 6: Model inspectable stops for missing seal material, unavailable calibrated measure, inadequate competence, insufficient energy, and lack of independent verifier; preserve consumed time and only actually damaged material**
- [ ] **Step 7: Let citizens rescore alternatives after a blocker, including gathering, requesting supplies, seeking instruction, resting, renegotiating, or abandoning**
- [ ] **Step 8: Run living-workshop, action-engine, terrain, and persistent-world suites**
- [ ] **Step 9: Commit the negotiated routed workflow**

```powershell
git add backend/persistent_world.py backend/tests/test_living_workshop.py backend/tests/test_persistent_world.py
git commit -m "feat: negotiate and execute routed repair work"
```

### Task 5: Verification, Causal Receipts, Subjective Memory, and CU Projection

**Files:**
- Modify: `backend/persistent_world.py`
- Modify: `backend/causal_ledger.py`
- Modify: `backend/economy/ledger.py`
- Modify: `backend/tests/test_living_workshop.py`
- Modify: `backend/tests/test_causal_ledger.py`

**Interfaces:**
- Produces: `living_workshop_receipt(state, action_id, viewer_id) -> dict[str, object]`.
- Receipt contains actor, action, custody deltas, tools, measurements, elapsed ticks, result, verifier, evidence IDs, causal parents, competency provenance, and `provisional_cu` with `spendable: false`.
- Produces memories with `source_event_ids`, `perceived_channels`, `confidence`, `importance`, `relevance`, `belief`, and `contradictions`.

- [ ] **Step 1: Write failing tests for independent rejection, append-only correction, selective memory, verified competency, failed-research value, and zero spendable CU**

```python
def test_unwitnessed_repair_changes_world_but_not_bystander_memory(self):
    action = complete_repair(self.store, witnesses={"ada", "mira"})
    state = self.store.snapshot()["state"]
    self.assertGreater(state["installations"]["water"]["flow_lpm"], 0)
    self.assertTrue(memory_mentions(state["npcs"]["ada"], action["id"]))
    self.assertFalse(memory_mentions(state["npcs"]["orin"], action["id"]))

def test_verified_claim_is_valuation_only(self):
    receipt = verified_repair_receipt(self.store)
    self.assertGreater(receipt["provisional_cu"]["milli"], 0)
    self.assertFalse(receipt["provisional_cu"]["spendable"])
    self.assertEqual(sum(self.store.snapshot()["state"]["shared_actions"]["valuation_accounts_milli"].values()), 0)
```

- [ ] **Step 2: Run causal-ledger and living-workshop tests and verify missing receipt/memory semantics fail**
- [ ] **Step 3: Append verification evidence and corrections without altering earlier events; enforce verifier identity, perception, competency, and non-participation**
- [ ] **Step 4: Derive each memory from viewer-filtered causal events and credible witnessed communication; never copy full authoritative records into every citizen**
- [ ] **Step 5: Record repair and measurement competency only after evidence-qualified practice; represent profession labels as a projection over demonstrated records**
- [ ] **Step 6: Calculate provisional CU from negotiated terms, public priority, material/labor cost, precision, durability, utility, evidence quality, and reproducibility; append a balanced valuation claim with `spendable=False` and no wallet mutation**
- [ ] **Step 7: Implement a viewer-filtered receipt that redacts hidden diagnosis, operator data, and unperceived evidence while preserving public verification facts**
- [ ] **Step 8: Run action, competency, causal-ledger, economy-ledger, and living-workshop suites**
- [ ] **Step 9: Commit receipts, memory, learning, and valuation**

```powershell
git add backend/persistent_world.py backend/causal_ledger.py backend/economy/ledger.py backend/tests/test_living_workshop.py backend/tests/test_causal_ledger.py
git commit -m "feat: record subjective repair outcomes"
```

### Task 6: Authenticated Server Projection, Replay, and Recovery

**Files:**
- Modify: `backend/persistent_world.py`
- Modify: `backend/persistent_world_app.py`
- Modify: `backend/auth_security.py`
- Modify: `backend/tests/test_persistent_world.py`
- Modify: `backend/tests/test_persistent_world_app.py`
- Modify: `backend/tests/test_auth_security.py`

**Interfaces:**
- Produces authenticated `GET /worlds/{world_id}/living-workshop` and existing `POST /worlds/{world_id}/actions` support for workshop commands.
- WebSocket `/worlds/{world_id}/stream` authenticates before accept and emits ordered `revision`, `tick`, and viewer-filtered projection changes.
- Checkpoint metadata exposes `simulation_version`, `last_committed_sequence`, `random_cursor`, and `pending_action_ids`.

- [ ] **Step 1: Write failing API tests showing token subject overrides supplied actor IDs, unauthenticated WebSockets close with policy violation, and one user cannot read another citizen's private memory**
- [ ] **Step 2: Write failing store tests comparing online ticks with bounded offline catch-up, interrupted action persistence, idempotent retry, and deterministic replay hashes**
- [ ] **Step 3: Run `python -m unittest backend.tests.test_auth_security backend.tests.test_persistent_world_app backend.tests.test_persistent_world -v` and verify the new boundaries fail**
- [ ] **Step 4: Derive `actor_id` exclusively from authorization claims in HTTP and WebSocket handlers; reject conflicting actor fields and preserve owner service controls on their separate audited endpoints**
- [ ] **Step 5: Add the viewer-filtered Living Workshop projection and ordered WebSocket updates without exposing hidden installation diagnosis or private memories**
- [ ] **Step 6: Persist checkpoint version, sequence, deterministic cursor, and pending identifiers transactionally with each committed batch; make replay skip committed idempotency keys**
- [ ] **Step 7: Bound offline catch-up by configured ticks and wall-clock processing budget, checkpoint between batches, and expose `catch_up_pending` in health/projection state**
- [ ] **Step 8: Run the three suites twice, including a close/reopen cycle, and compare final state and causal-ledger hashes**
- [ ] **Step 9: Commit authenticated projection and recovery**

```powershell
git add backend/persistent_world.py backend/persistent_world_app.py backend/auth_security.py backend/tests/test_persistent_world.py backend/tests/test_persistent_world_app.py backend/tests/test_auth_security.py
git commit -m "feat: secure living workshop persistence"
```

### Task 7: Server-Observed Isometric Living Workshop

**Files:**
- Create: `frontend/src/lib/livingWorkshopView.cjs`
- Create: `frontend/src/lib/livingWorkshopView.test.cjs`
- Modify: `frontend/src/lib/worldServer.js`
- Modify: `frontend/src/lib/autonomousChatter.js`
- Modify: `frontend/src/lib/isometricInteractions.test.cjs`
- Modify: `frontend/src/pages/IsometricSettlement.jsx`
- Modify: `frontend/src/pages/IsometricSettlement.css`
- Modify: `frontend/src/components/AuthoritativeWorkPanel.jsx`
- Modify: `frontend/electron/authoritative-world-view.test.cjs`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `projectLivingWorkshop(snapshot, actorId) -> {water, demand, workOrders, workers, receipts, chatter, catchUp}`.
- Produces: `submitSharedAction(operation, sharedActionId, payload, expectedRevision)` and `fetchLivingWorkshop(worldId, signal)`.
- Isometric controls send proposal/response/route/action intentions only.

- [ ] **Step 1: Write a failing Node projection test for water status, worker route, reason, blocker, evidence receipt, and hidden-belief redaction**

```javascript
test('living workshop projection explains work without exposing hidden beliefs', () => {
  const view = projectLivingWorkshop(snapshot, 'luciferous-id');
  assert.equal(view.workers[0].reason, 'measure declining well flow');
  assert.equal(view.workers[0].route.progress > 0, true);
  assert.equal(Object.hasOwn(view.workers[0], 'privateMemories'), false);
  assert.equal(view.receipts[0].provisionalCu.spendable, false);
});
```

- [ ] **Step 2: Add a failing interaction test proving a tile with timber and stone offers separate collection intentions and selecting timber never requests stone**
- [ ] **Step 3: Run `pnpm --dir frontend test:desktop-store` and verify the missing projection and individual-item behavior fail**
- [ ] **Step 4: Implement the pure projection and authenticated API helpers; add its test to `test:desktop-store`**
- [ ] **Step 5: Replace local workshop completion and fallback state mutation with server intentions; retain local mode only as a clearly labeled disconnected preview that cannot overwrite server state**
- [ ] **Step 6: Render visible installation condition, citizens traveling/working/resting, multi-tile route interpolation, current reason, reservation, blocker, progress, verification state, and causal receipt**
- [ ] **Step 7: Expose separate item controls for every collectible item on a tile and preserve server custody/stock results after refresh**
- [ ] **Step 8: Project spontaneous and directed proximity speech from server communications; pin the speech-versus-physical-impact explanation once and remove repetitive disclaimer responses**
- [ ] **Step 9: Run Node tests and `pnpm --dir frontend build`; manually verify keyboard navigation, contrast, zoom, reduced motion, disconnected state, and reconnect state**
- [ ] **Step 10: Commit the isometric Living Workshop UI**

```powershell
git add frontend/src/lib/livingWorkshopView.cjs frontend/src/lib/livingWorkshopView.test.cjs frontend/src/lib/worldServer.js frontend/src/lib/autonomousChatter.js frontend/src/lib/isometricInteractions.test.cjs frontend/src/pages/IsometricSettlement.jsx frontend/src/pages/IsometricSettlement.css frontend/src/components/AuthoritativeWorkPanel.jsx frontend/electron/authoritative-world-view.test.cjs frontend/package.json
git commit -m "feat: render the living workshop in isometric view"
```

### Task 8: End-to-End Regression Gate and Architectural Migration Note

**Files:**
- Modify: `frontend/e2e/isometric.spec.js`
- Modify: `scripts/verify_core.ps1`
- Modify: `docs/CANONICAL_ACTION_MIGRATION.md`
- Modify: `docs/FEATURE_MATRIX.md`
- Rename: `backend/ALPHA34_WORLD_SERVER.env.example` to `backend/ALPHA35_WORLD_SERVER.env.example`

**Interfaces:**
- `scripts/verify_core.ps1` runs deterministic backend suites, Node projection tests, frontend build, and optional Playwright smoke using local seeded services.
- Migration note classifies legacy systems as `retained`, `adapted`, `deprecated`, or `replaced`.

- [ ] **Step 1: Add an E2E test that logs in, opens the isometric settlement, observes the live server tick, routes near the water site, inspects a demand, and sees the same work order after reload**
- [ ] **Step 2: Run `pnpm --dir frontend test:e2e -- --grep "Living Workshop"` against the local server and verify the test fails before selectors/projection are wired**
- [ ] **Step 3: Add the new backend and Node suites to `scripts/verify_core.ps1` and make any nonzero command terminate verification**
- [ ] **Step 4: Document retained `SharedActionEngine`, `PersistentWorldStore`, frontier, causal ledger, society scorer, and competency provenance; adapted water/maintenance paths; deprecated local browser simulation authority and free-will probability; replaced duplicate instant-work and direct-verification paths**
- [ ] **Step 5: Update the feature matrix using only `implemented`, `prototype`, `simulated`, `external dependency`, `planned`, and `verified` labels supported by tests**
- [ ] **Step 6: Rename the environment example and add `EOV_OFFLINE_MAX_TICKS`, `EOV_CATCHUP_BUDGET_MS`, and `EOV_WORLD_DB_PATH` with safe local defaults and no owner password or token**
- [ ] **Step 7: Run `powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1` from a clean checkout-compatible environment**
- [ ] **Step 8: Commit the regression gate and migration documentation**

```powershell
git add frontend/e2e/isometric.spec.js scripts/verify_core.ps1 docs/CANONICAL_ACTION_MIGRATION.md docs/FEATURE_MATRIX.md backend/ALPHA35_WORLD_SERVER.env.example
git commit -m "test: gate the alpha 35 vertical slice"
```

### Task 9: Alpha 35 Windows Client and Persistent Server Release

**Files:**
- Modify: `frontend/package.json`
- Create: `scripts/package_alpha35_release.ps1`
- Create: `scripts/verify_alpha35_release.ps1`
- Create: `docs/ALPHA35_RELEASE_NOTES.md`

**Interfaces:**
- Canonical release version: `0.3.0-alpha.35`.
- Produces: `outputs/EoV-Alpha35-Windows-x64.zip`, `outputs/EoV-Alpha35-Persistent-Server.zip`, and `outputs/EoV-Alpha35-SHA256.txt`.

- [ ] **Step 1: Extend the version-consistency test to reject Alpha 34, `v0.1.0`, and any loading-screen watermark not derived from `0.3.0-alpha.35`**
- [ ] **Step 2: Write `verify_alpha35_release.ps1` to fail when archives are missing, empty, wrongly versioned, contain `.env`, credentials, tokens, SQLite/database files, saves, payment activation, or omit the executable/server entrypoint/environment example**
- [ ] **Step 3: Run the version and release checks and verify they fail because Alpha 35 metadata and archives do not exist**
- [ ] **Step 4: Set `frontend/package.json` to `0.3.0-alpha.35`, source visible loading watermark text from the canonical version, and leave normal gameplay screens unwatermarked**
- [ ] **Step 5: Write the packaging script by adapting Alpha 34 staging: build Electron, stage tracked server modules and locked requirements, copy `.env.example`, create deterministic archives, and write SHA-256 hashes**
- [ ] **Step 6: Write release notes with install/start/authentication instructions, the Living Workshop acceptance checklist, implemented-versus-simulated status, migration behavior, known limits, and exact verification commands**
- [ ] **Step 7: Run backend suites, Node tests, frontend build, Playwright Living Workshop smoke, and `scripts/verify_core.ps1`; record commands and outcomes in the release notes**
- [ ] **Step 8: Run `scripts/package_alpha35_release.ps1`, then `scripts/verify_alpha35_release.ps1`; extract both archives into a temporary directory, launch the packaged server, and verify `/health` plus an authenticated world snapshot**
- [ ] **Step 9: Inspect `git status --short`, archive manifests, and staged diff; confirm the two pre-existing settlement-projection edits were neither staged nor overwritten**
- [ ] **Step 10: Commit tracked release metadata and scripts, leaving generated archives uncommitted unless repository policy explicitly tracks release binaries**

```powershell
git add frontend/package.json scripts/package_alpha35_release.ps1 scripts/verify_alpha35_release.ps1 docs/ALPHA35_RELEASE_NOTES.md
git commit -m "release: package alpha 35 living workshop"
```

## Plan self-review

- **Spec coverage:** Tasks 1–6 implement the complete canonical lifecycle, bounded knowledge, shared human/AI gates, physical accounting, evidence, memory, learning, valuation, security, persistence, and recovery. Task 7 provides the visible isometric workflow and communication behavior. Tasks 8–9 provide reproducibility, migration documentation, versioning, and downloadable artifacts.
- **Scope control:** Water repair is the only new production workflow. Cooking, construction, first-person, VR, hardware actuation, real money, and distributed scale remain outside Alpha 35.
- **Architecture consistency:** `SharedActionEngine` remains the sole consequential-action kernel; `PersistentWorldStore` remains the durable authority; society and competency modules are adapted rather than duplicated; React receives filtered projections.
- **Type consistency:** The plan consistently uses `WaterInstallationSpec`, `water_installation_repair`, `DecisionContext`, `DecisionScore`, `record_practice_evidence`, `_process_living_workshop`, `living_workshop_receipt`, and `projectLivingWorkshop`.
- **Security consistency:** Every network mutation derives identity from claims, WebSockets authenticate before subscription, and operator control remains separate.
- **Economic consistency:** Every CU output is a nonspendable projection and no wallet, withdrawal, redemption, or payment path is added.
- **Release consistency:** All user-visible release surfaces and artifacts use `0.3.0-alpha.35` / Alpha 35.
