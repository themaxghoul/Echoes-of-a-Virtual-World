# Framed Shelter Construction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one persistent framed-shelter workflow that gives human and AI residents identical causal construction rules without expanding into a general building simulator.

**Architecture:** Extend the existing `SharedActionEngine` and persistent-world shared-action records with scenario-owned shelter definitions and a small work-package coordinator. Server state remains authoritative; the isometric client projects construction state and sends commands but never advances work locally.

**Tech Stack:** Python dataclasses and `unittest`, the existing JSON persistent-world store and causal ledger, React, CommonJS projection helpers, Jest, and the existing desktop packaging pipeline.

**Spec:** `docs/superpowers/specs/2026-09-16-historical-construction-design.md`

## Global Constraints

- Execution is blocked until the Alpha 35 Living Workshop release gate, downloadable artifacts, and GitHub push are complete.
- Reuse the canonical shared-action lifecycle; do not create a parallel construction action engine.
- Actor identity is server-derived and human/AI actor kind never relaxes access, material, competence, time, or verification gates.
- Construction activity cannot wait for spendable CU; valuation remains provisional, evidence-derived, and nonspendable.
- The server owns physical state, work time, custody, reservations, uncertainty seeds, and causal history.
- The first implementation stops at one simple framed shelter: survey, design selection, delivery, foundation preparation, frame erection, basic inspection, and occupancy.
- Exclude bunkers, powered utilities, large-crew scheduling, broad archaeology, and provider-generated design execution from this increment.

---

## File Map

- Create `backend/scenarios/framed_shelter.py`: scenario-owned materials, design revision, package definitions, deterministic evaluation, and salvage rules.
- Create `backend/construction_workflow.py`: shelter instance lifecycle, package dependencies, progress, reservation expiry, handoff, inspection, occupancy, and projection-neutral blockers.
- Modify `backend/action_engine.py`: support bounded partial execution and recorded uncertainty without construction-specific lore.
- Modify `backend/persistent_world.py`: persist construction state, route authenticated commands through shared actions, advance autonomous packages, and migrate old saves.
- Create `backend/tests/test_framed_shelter.py`: end-to-end construction invariants and deterministic replay.
- Modify `backend/tests/test_action_engine.py`: generic partial-progress and handoff behavior.
- Modify `backend/tests/test_persistent_world.py`: migration, restart, offline catch-up, AI/human parity, and subjective visibility.
- Create `frontend/src/lib/constructionView.cjs`: pure progressive-disclosure projection for the HUD and history panel.
- Create `frontend/src/lib/constructionView.test.cjs`: projection and hidden-history tests.
- Modify `frontend/src/pages/IsometricSettlement.jsx`: render authoritative site phases and submit package commands.
- Modify `frontend/src/pages/IsometricSettlement.css`: flush site geometry, progress, blocker, and history presentation.
- Modify `frontend/src/components/AuthoritativeWorkPanel.jsx`: show the next useful construction action and optional provenance.
- Modify `docs/ARCHITECTURE.md`: document ownership, invariants, persistence, and the post-Alpha35 boundary.

### Task 1: Scenario-owned framed-shelter definitions

**Files:**
- Create: `backend/scenarios/framed_shelter.py`
- Create: `backend/tests/test_framed_shelter.py`

**Interfaces:**
- Consumes: `ActionDefinition` and `ActionRequirements` from `backend/action_engine.py`.
- Produces: `FramedShelterDesign`, `ShelterPackageSpec`, `FRAMED_SHELTER_V1`, `package_action_definition(package_id: str) -> ActionDefinition`, and `evaluate_shelter_package(package_id: str, context: dict) -> dict`.

- [ ] **Step 1: Write failing catalog tests**

```python
class FramedShelterCatalogTests(unittest.TestCase):
    def test_design_has_a_versioned_dependency_order(self):
        self.assertEqual(
            FRAMED_SHELTER_V1.package_order,
            ("survey", "delivery", "foundation", "frame", "inspection"),
        )
        self.assertEqual(FRAMED_SHELTER_V1.version, 1)

    def test_frame_requires_materials_tools_time_and_competence(self):
        definition = package_action_definition("frame")
        self.assertEqual(definition.requirements.materials, {"timber": 12, "fastener": 24})
        self.assertEqual(definition.requirements.tools, {"carpentry_kit": 0.5})
        self.assertEqual(definition.requirements.station, "framed_shelter_site")
        self.assertGreater(definition.requirements.duration_ticks, 1)
        self.assertEqual(definition.requirements.competence_domain, "construction_assembly")
```

- [ ] **Step 2: Run the catalog tests and confirm the missing module failure**

Run: `python -m unittest backend.tests.test_framed_shelter.FramedShelterCatalogTests -v`

Expected: FAIL because `scenarios.framed_shelter` does not exist.

- [ ] **Step 3: Add immutable scenario records and package definitions**

```python
@dataclass(frozen=True)
class ShelterPackageSpec:
    package_id: str
    dependencies: tuple[str, ...]
    definition: ActionDefinition
    progress_units: int

@dataclass(frozen=True)
class FramedShelterDesign:
    design_id: str
    version: int
    license: str
    publication_status: str
    package_order: tuple[str, ...]
    capacity: int

FRAMED_SHELTER_V1 = FramedShelterDesign(
    design_id="framed-shelter", version=1, license="settlement-construction-use",
    publication_status="published", package_order=("survey", "delivery", "foundation", "frame", "inspection"),
    capacity=4,
)

def package_action_definition(package_id: str) -> ActionDefinition:
    return PACKAGE_SPECS[package_id].definition
```

Define all five packages in `PACKAGE_SPECS`. Only `inspection` may commission occupancy; the other evaluators produce measured intermediate deltas. Evaluators return explicit `succeeded`, `output`, `evidence`, and `material_disposition` keys.

- [ ] **Step 4: Add deterministic evaluation tests**

```python
def test_same_seed_and_inputs_produce_same_foundation_result(self):
    context = {"samples": [{"level_error_mm": 3.0}], "uncertainty_seed": 41, "completed_units": 0}
    first = evaluate_shelter_package("foundation", context)
    second = evaluate_shelter_package("foundation", context)
    self.assertEqual(first, second)
    self.assertIn("recoverable", first["material_disposition"])
```

- [ ] **Step 5: Run and commit the scenario slice**

Run: `python -m unittest backend.tests.test_framed_shelter.FramedShelterCatalogTests -v`

Expected: PASS.

```powershell
git add backend/scenarios/framed_shelter.py backend/tests/test_framed_shelter.py
git commit -m "feat: define framed shelter work packages"
```

### Task 2: Generic partial work, handoff, and reservation expiry

**Files:**
- Modify: `backend/action_engine.py`
- Modify: `backend/tests/test_action_engine.py`

**Interfaces:**
- Consumes: existing `SharedActionEngine.propose`, `accept`, `reserve`, `execute`, `verify`, and `commission` methods.
- Produces: `ActionRecord.completed_units: int`, `ActionRecord.required_units: int`, `ActionRecord.uncertainty_seed: int`, `SharedActionEngine.contribute(...)`, `SharedActionEngine.handoff(...)`, and `SharedActionEngine.expire_reservations(current_tick: int) -> list[str]`.

- [ ] **Step 1: Write failing kernel tests for partial progress**

```python
def test_partial_work_accumulates_without_consuming_the_same_inputs_twice(self):
    engine, worker = framed_action_fixture(required_units=4)
    engine.contribute("frame-1", worker, units=2, samples=[], uncertainty_seed=7)
    self.assertEqual(engine.actions["frame-1"].completed_units, 2)
    stock_after_first = copy.deepcopy(engine.world.communal_inventory)
    engine.contribute("frame-1", worker, units=2, samples=[], uncertainty_seed=7)
    self.assertEqual(engine.actions["frame-1"].completed_units, 4)
    self.assertEqual(stock_after_first, engine.world.communal_inventory)
```

- [ ] **Step 2: Write failing handoff and expiry tests**

```python
def test_handoff_preserves_progress_and_rebinds_commitment(self):
    engine, first, second = framed_handoff_fixture()
    engine.contribute("frame-1", first, units=2, samples=[], uncertainty_seed=9)
    engine.handoff("frame-1", first, second)
    self.assertEqual(engine.actions["frame-1"].actor_id, second.actor_id)
    self.assertEqual(engine.actions["frame-1"].completed_units, 2)

def test_expired_reservation_releases_tools_but_not_progress(self):
    engine, worker = framed_action_fixture(required_units=4, reservation_expires_tick=8)
    engine.contribute("frame-1", worker, units=1, samples=[], uncertainty_seed=3)
    self.assertEqual(engine.expire_reservations(8), ["frame-1"])
    self.assertEqual(engine.actions["frame-1"].completed_units, 1)
    self.assertIsNone(engine.world.tools["carpentry_kit"]["reserved_by"])
```

- [ ] **Step 3: Run the focused tests and confirm missing interface failures**

Run: `python -m unittest backend.tests.test_action_engine.SharedActionEngineTests.test_partial_work_accumulates_without_consuming_the_same_inputs_twice backend.tests.test_action_engine.SharedActionEngineTests.test_handoff_preserves_progress_and_rebinds_commitment backend.tests.test_action_engine.SharedActionEngineTests.test_expired_reservation_releases_tools_but_not_progress -v`

Expected: FAIL because partial-work fields and methods are absent.

- [ ] **Step 4: Implement generic progress and custody-safe handoff**

Add these fields to `ActionRecord`:

```python
completed_units: int = 0
required_units: int = 1
uncertainty_seed: Optional[int] = None
reservation_expires_tick: Optional[int] = None
inputs_debited: bool = False
participants: List[str] = field(default_factory=list)
```

`contribute` records actor, units, seed, elapsed ticks, and an `in_progress` causal event. It debits reserved inputs only when `inputs_debited` is false, caps progress at `required_units`, and invokes the existing evaluator only at completion. `handoff` requires both actors to satisfy the same requirements, emits a handoff event, and transfers the commitment. `expire_reservations` releases tools/stations atomically and emits an expiry event without deleting progress.

- [ ] **Step 5: Run the action-engine suite and commit**

Run: `python -m unittest backend.tests.test_action_engine -v`

Expected: PASS.

```powershell
git add backend/action_engine.py backend/tests/test_action_engine.py
git commit -m "feat: support partial shared work and crew handoff"
```

### Task 3: Persistent shelter workflow and migration

**Files:**
- Create: `backend/construction_workflow.py`
- Modify: `backend/persistent_world.py`
- Modify: `backend/tests/test_framed_shelter.py`
- Modify: `backend/tests/test_persistent_world.py`

**Interfaces:**
- Consumes: Task 1 package definitions and Task 2 partial shared actions.
- Produces: `ensure_construction_state(state: dict) -> dict`, `propose_shelter(state, actor_id, site_id, design_id) -> dict`, `advance_shelter_package(state, actor_id, structure_id, package_id, units, uncertainty_seed) -> dict`, `inspect_shelter(...) -> dict`, and `construction_tick(state, tick) -> list[dict]`.

- [ ] **Step 1: Write the migration and proposal tests**

```python
def test_migration_adds_empty_construction_state_without_changing_revision(self):
    legacy = founding_table_seed(1000)
    revision = legacy["revision"]
    migrated = migrate_state(legacy)
    self.assertEqual(migrated["construction"], {"structures": {}, "artifact_versions": {}, "site_reservations": {}})
    self.assertEqual(migrated["revision"], revision)

def test_proposal_requires_observed_accessible_land_and_published_design(self):
    state = shelter_world()
    with self.assertRaisesRegex(ValueError, "site is not perceived"):
        propose_shelter(state, "human-1", "hidden-site", "framed-shelter")
```

- [ ] **Step 2: Run and confirm construction state is absent**

Run: `python -m unittest backend.tests.test_framed_shelter backend.tests.test_persistent_world -v`

Expected: FAIL at the new construction assertions.

- [ ] **Step 3: Add the authoritative structure record and command routing**

Use this persisted shape:

```python
{
  "id": structure_id,
  "design": {"id": "framed-shelter", "version": 1},
  "site_id": site_id,
  "status": "proposed",
  "package_order": ["survey", "delivery", "foundation", "frame", "inspection"],
  "packages": {package_id: {"status": "pending", "completed_units": 0, "action_ids": []}},
  "current_package": "survey",
  "physical": {"phase": "markers", "completion": 0.0, "condition": 1.0},
  "occupancy": {"capacity": 0, "approved": False},
  "version_history": [],
  "blocker": None,
}
```

Route `type == "construction"` in `apply_world_action` to operations `propose`, `accept_package`, `contribute`, `handoff`, `abandon`, and `inspect`. Derive `actor_id` from the authenticated `apply_action` argument; reject any actor ID inside the body.

- [ ] **Step 4: Add restart and bounded catch-up tests**

```python
def test_partial_foundation_survives_restart_and_bounded_catchup(self):
    store = persistent_store_with_shelter()
    before = store.snapshot("world-1")
    reopened = PersistentWorldStore(store.path, max_offline_ticks=12)
    after = reopened.snapshot("world-1", now_ms=before["saved_at_ms"] + 60_000)
    package = after["state"]["construction"]["structures"]["shelter-1"]["packages"]["foundation"]
    self.assertEqual(package["completed_units"], 2)
    self.assertLessEqual(after["state"]["clock"]["tick"] - before["state"]["clock"]["tick"], 12)
```

- [ ] **Step 5: Run persistent-world tests and commit**

Run: `python -m unittest backend.tests.test_framed_shelter backend.tests.test_persistent_world -v`

Expected: PASS.

```powershell
git add backend/construction_workflow.py backend/persistent_world.py backend/tests/test_framed_shelter.py backend/tests/test_persistent_world.py
git commit -m "feat: persist framed shelter workflow"
```

### Task 4: Autonomous Samaritan work distribution and recovery

**Files:**
- Modify: `backend/construction_workflow.py`
- Modify: `backend/persistent_world.py`
- Modify: `backend/tests/test_framed_shelter.py`

**Interfaces:**
- Consumes: existing NPC needs, initiative decisions, `shared_actions.actor_commitments`, and construction packages from Task 3.
- Produces: `construction_options(state, entity_id) -> list[DecisionOption]`, `assign_next_package(state, entity_id, structure_id) -> dict`, and explicit blocker records `{code, summary, evidence, recovery_actions}`.

- [ ] **Step 1: Write failing autonomy and blocker tests**

```python
def test_shelter_need_can_generate_a_package_without_player_prompt(self):
    state = shelter_world(exposed_residents=4)
    events = construction_tick(state, state["clock"]["tick"] + 1)
    self.assertTrue(any(event["type"] == "construction_package_proposed" for event in events))

def test_material_shortfall_exposes_one_primary_blocker_and_recovery(self):
    state = shelter_at_frame_package(timber=3)
    result = assign_next_package(state, "orin", "shelter-1")
    self.assertEqual(result["blocker"]["code"], "material_shortfall")
    self.assertIn("source timber", result["blocker"]["recovery_actions"])
```

- [ ] **Step 2: Run and confirm autonomous construction does not yet exist**

Run: `python -m unittest backend.tests.test_framed_shelter.FramedShelterAutonomyTests -v`

Expected: FAIL at missing autonomy functions.

- [ ] **Step 3: Implement needs-based proposals and voluntary participation**

Create decision options from perceived shelter demand, current needs, competence, relationships, resources, risk, and expected utility. Feed them to the existing `decide_initiative`; do not inspect `actor_kind`. An AI may accept, refuse, pause for needs, abandon safely, or propose a recovery action. A package may advance only through the same construction command and shared-action state machine available to a human.

Blocker priority is deterministic: access, dependency, competence, material, tool, station/site, energy/needs, weather/curing, verifier. Store only the primary blocker on the structure while preserving all evidence in causal records.

- [ ] **Step 4: Test human/AI parity and crew rotation**

```python
def test_human_and_ai_receive_identical_frame_requirement_failures(self):
    human = attempt_frame(actor_kind="human", competence=0.1)
    samaritan = attempt_frame(actor_kind="ai", competence=0.1)
    self.assertEqual(human["reason"], samaritan["reason"])

def test_tired_worker_can_pause_and_qualified_worker_can_continue(self):
    state = shelter_at_partial_frame(worker="orin", completed_units=2)
    rotate_construction_crew(state, "shelter-1", "orin", "ada")
    self.assertEqual(frame_package(state)["completed_units"], 2)
    self.assertEqual(frame_package(state)["active_actor_id"], "ada")
```

- [ ] **Step 5: Run and commit autonomous workflow**

Run: `python -m unittest backend.tests.test_framed_shelter backend.tests.test_persistent_world -v`

Expected: PASS.

```powershell
git add backend/construction_workflow.py backend/persistent_world.py backend/tests/test_framed_shelter.py
git commit -m "feat: let Samaritans coordinate shelter work"
```

### Task 5: Inspection, failure, salvage, history, and competence recency

**Files:**
- Modify: `backend/construction_workflow.py`
- Modify: `backend/competency_engine.py`
- Modify: `backend/tests/test_framed_shelter.py`
- Modify: `backend/tests/test_competency_engine.py`

**Interfaces:**
- Consumes: causal-ledger evidence verification and existing competency records.
- Produces: `inspection` outcomes, `salvage_structure(state, actor_id, structure_id) -> dict`, `operational_readiness(profile, domain, current_tick, maximum_age_ticks) -> dict`, and immutable version-history entries.

- [ ] **Step 1: Write failing inspection, salvage, and staleness tests**

```python
def test_builder_cannot_independently_verify_the_frame(self):
    state = shelter_at_inspection(builder="orin")
    result = inspect_shelter(state, "orin", "shelter-1", measured_frame())
    self.assertFalse(result["accepted"])
    self.assertEqual(result["reason"], "independent verifier required")

def test_failed_frame_salvage_returns_material_exactly_once(self):
    state = failed_frame_world(recoverable_timber=7)
    first = salvage_structure(state, "ada", "shelter-1")
    second = salvage_structure(state, "ada", "shelter-1")
    self.assertEqual(first["outputs"], {"timber": 7})
    self.assertFalse(second["accepted"])

def test_staleness_changes_readiness_without_deleting_evidence(self):
    profile = demonstrated_profile("construction_inspection", verified_tick=10)
    evidence = list(profile.get("construction_inspection").evidence_ids)
    readiness = operational_readiness(profile, "construction_inspection", current_tick=500, maximum_age_ticks=100)
    self.assertFalse(readiness["ready"])
    self.assertEqual(profile.get("construction_inspection").evidence_ids, evidence)
```

- [ ] **Step 2: Run and confirm failures**

Run: `python -m unittest backend.tests.test_framed_shelter backend.tests.test_competency_engine -v`

Expected: FAIL because inspection independence, single-use salvage, and recency readiness are incomplete.

- [ ] **Step 3: Implement inspectable failure and recovery**

Inspection records measured tolerances, instrument IDs, verifier identity, design revision, and outcome. Passing inspection commissions occupancy capacity. Failure leaves the physical phase visible, opens a repair or salvage recovery action, and appends a version-history entry. Salvage transfers only the recorded recoverable quantity from structure custody to communal custody and stamps `salvaged_event_id` to prevent replay.

Add `last_verified_tick` to demonstrated competency outcomes. `operational_readiness` returns `{ready, demonstrated, stale, evidence_ids, reason}` and never mutates or removes evidence.

- [ ] **Step 4: Add provisional valuation assertions**

```python
def test_verified_contribution_creates_nonspendable_cu_claim(self):
    state = completed_shelter_world()
    claim = state["economy"]["provisional_claims"][-1]
    self.assertEqual(claim["evidence_action_id"], "shelter-1:inspection")
    self.assertFalse(claim["spendable"])
    self.assertGreater(claim["cu_milli"], 0)
```

- [ ] **Step 5: Run and commit recovery behavior**

Run: `python -m unittest backend.tests.test_framed_shelter backend.tests.test_competency_engine -v`

Expected: PASS.

```powershell
git add backend/construction_workflow.py backend/competency_engine.py backend/tests/test_framed_shelter.py backend/tests/test_competency_engine.py
git commit -m "feat: verify and recover shelter construction"
```

### Task 6: Perspective-safe construction projection and isometric presentation

**Files:**
- Create: `frontend/src/lib/constructionView.cjs`
- Create: `frontend/src/lib/constructionView.test.cjs`
- Modify: `frontend/src/pages/IsometricSettlement.jsx`
- Modify: `frontend/src/pages/IsometricSettlement.css`
- Modify: `frontend/src/components/AuthoritativeWorkPanel.jsx`

**Interfaces:**
- Consumes: authenticated snapshot fields `construction.structures`, `observations`, and public causal evidence.
- Produces: `projectConstruction(state, viewerId) -> {sites, focus, history}`.

- [ ] **Step 1: Write failing progressive-disclosure tests**

```javascript
test('focus exposes the next action while history retains public provenance', () => {
  const view = projectConstruction(shelterSnapshot(), 'luciferous');
  expect(view.focus).toEqual(expect.objectContaining({
    structureId: 'shelter-1', packageId: 'frame', blocker: null,
  }));
  expect(view.history.length).toBeGreaterThan(0);
});

test('a viewer cannot see hidden authoritative history', () => {
  const view = projectConstruction(hiddenHistorySnapshot(), 'visitor');
  expect(view.history.some((entry) => entry.id === 'private-survey')).toBe(false);
});
```

- [ ] **Step 2: Run and confirm missing projection failure**

Run: `npm test -- --runInBand src/lib/constructionView.test.cjs`

Working directory: `frontend`

Expected: FAIL because `constructionView.cjs` does not exist.

- [ ] **Step 3: Implement the pure projection**

```javascript
function projectConstruction(state = {}, viewerId) {
  const perceived = new Set(state.observations?.[viewerId]?.evidence_ids || []);
  const structures = Object.values(state.construction?.structures || {});
  const sites = structures.filter((item) => item.public || perceived.has(item.site_evidence_id))
    .map((item) => ({
      id: item.id, siteId: item.site_id, phase: item.physical.phase,
      completion: item.physical.completion, condition: item.physical.condition,
      status: item.status, location: item.location,
    }));
  const active = structures.find((item) => item.status !== 'occupied' && item.status !== 'abandoned');
  return { sites, focus: active ? projectFocus(active) : null, history: projectVisibleHistory(structures, perceived) };
}
```

`projectFocus` shows the package reason, required inputs, progress, one blocker, and recovery actions. Full tolerances, licenses, and causal events stay in the expandable history view.

- [ ] **Step 4: Render authoritative physical phases and controls**

In `IsometricSettlement.jsx`, derive `constructionView` with `useMemo`, draw the server-provided site boundary flush to the existing diamond grid, and vary only the partial structure geometry by `phase` and `completion`. Buttons submit `type: 'construction'` commands through the existing authenticated `submitWorldAction`; no local timer changes package progress.

Add a compact construction card to `AuthoritativeWorkPanel.jsx` with progress, actor, blocker, and the smallest recovery action. Add an expandable history section for public evidence.

- [ ] **Step 5: Run frontend tests and production build**

Run: `npm test -- --runInBand src/lib/constructionView.test.cjs`

Run: `npm run build`

Working directory: `frontend`

Expected: tests PASS and build exits 0.

- [ ] **Step 6: Commit the client projection**

```powershell
git add frontend/src/lib/constructionView.cjs frontend/src/lib/constructionView.test.cjs frontend/src/pages/IsometricSettlement.jsx frontend/src/pages/IsometricSettlement.css frontend/src/components/AuthoritativeWorkPanel.jsx
git commit -m "feat: render authoritative shelter construction"
```

### Task 7: End-to-end invariants, documentation, and release gate

**Files:**
- Modify: `backend/tests/test_framed_shelter.py`
- Modify: `backend/tests/test_persistent_world.py`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: all prior task interfaces.
- Produces: one reproducible framed-shelter regression gate and architecture ownership documentation.

- [ ] **Step 1: Add the complete replay test**

```python
def test_human_and_ai_can_replay_the_same_shelter_history(self):
    human = run_complete_shelter(actor_kind="human", uncertainty_seed=73)
    samaritan = run_complete_shelter(actor_kind="ai", uncertainty_seed=73)
    self.assertEqual(human["physical"], samaritan["physical"])
    self.assertEqual(human["material_reconciliation"], samaritan["material_reconciliation"])
    self.assertEqual(normalize_actor_ids(human["ledger"]), normalize_actor_ids(samaritan["ledger"]))
```

- [ ] **Step 2: Add the conservation and sandbox tests**

```python
def test_every_material_unit_is_installed_waste_recovered_or_remaining(self):
    result = run_complete_shelter(actor_kind="human", uncertainty_seed=73)
    for material in result["material_reconciliation"].values():
        self.assertEqual(material["before"], material["installed"] + material["waste"] + material["recovered"] + material["remaining"])

def test_concept_artifact_cannot_mutate_live_construction(self):
    state = shelter_world()
    before = copy.deepcopy(state["construction"])
    simulate_concept_artifact(state, {"render": "bunker.png"})
    self.assertEqual(state["construction"], before)
```

- [ ] **Step 3: Run the full backend and frontend regression gates**

Run: `python -m unittest discover -s backend/tests -v`

Expected: PASS.

Run: `npm test -- --runInBand`

Run: `npm run build`

Working directory for both npm commands: `frontend`

Expected: tests PASS and build exits 0.

- [ ] **Step 4: Document system ownership and boundaries**

Add a “Framed shelter construction” section to `docs/ARCHITECTURE.md` that names:

- `action_engine.py` as lifecycle owner;
- `construction_workflow.py` as package/dependency coordinator;
- `scenarios/framed_shelter.py` as scenario catalog;
- `persistent_world.py` as persistence and tick owner;
- the causal ledger as evidence owner;
- competency records as evidence-derived readiness;
- the frontend as a perspective-filtered projection only;
- generated artifacts as sandboxed concepts;
- CU claims as nonspendable projections.

- [ ] **Step 5: Verify scope and commit**

Run: `rg -n "bunker|powered utility|crypto|withdrawal|fiat redemption" backend/construction_workflow.py backend/scenarios/framed_shelter.py frontend/src/lib/constructionView.cjs`

Expected: no matches.

Run: `git diff --check HEAD~6..HEAD`

Expected: no output.

```powershell
git add backend/tests/test_framed_shelter.py backend/tests/test_persistent_world.py docs/ARCHITECTURE.md
git commit -m "test: prove framed shelter construction invariants"
```

The slice is releasable only when the complete suite passes from a clean checkout, restart preserves partial work, bounded catch-up cannot duplicate work or salvage, and the packaged client observes the same authoritative server state as the browser client.
