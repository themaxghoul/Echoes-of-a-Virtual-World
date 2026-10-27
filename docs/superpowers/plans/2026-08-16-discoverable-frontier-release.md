# Discoverable Frontier Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a downloadable Windows client and persistent server where authenticated humans and autonomous residents explore, modify, and conserve materials across a deterministic 64×64 frontier.

**Architecture:** Add a dependency-free terrain kernel behind a world-grid interface, then adapt the persistent world store and canonical action engine to it. The desktop client renders only server observations, interpolates server-approved routes, and exposes finite extraction, deposit, and plot preparation without becoming authoritative.

**Tech Stack:** Python 3 standard library, SQLite persistent event store, FastAPI, React 19 canvas UI, Electron 37, Node test runner, pnpm.

## Global Constraints

- The authoritative server owns all terrain, discovery, routing, custody, and physical mutation.
- The first frontier is exactly 64×64 and deterministic for a stable seed.
- Authoritative state, recorded evidence, and subjective memory remain distinct.
- Humans and AI use identical consequential-action requirements.
- Extracted materials remain in actor custody until a canonical deposit transfer.
- CU is provisional, internal, balanced, and nonspendable.
- Sirix-1 creator authority is authenticated, world-scoped, out-of-world, and audited; embodied actions obey canonical physics.
- No credentials, private saves, databases, real-money activation, or production-readiness claims enter release artifacts.

---

### Task 1: Deterministic Frontier Kernel

**Files:**
- Create: `backend/terrain_engine.py`
- Create: `backend/tests/test_terrain_engine.py`

**Interfaces:**
- Produces: `FrontierGrid(seed: int, size: int = 64)`, `tile_at(x: int, y: int) -> TerrainTile`, `neighbors(position: tuple[int, int]) -> list[tuple[int, int]]`, and `find_route(start, goal, known, modifications) -> RouteResult`.
- `TerrainTile` exposes `terrain`, `elevation`, `travel_cost_milli`, `passable`, `surface`, and `substrate` without mutable global random state.

- [ ] **Step 1: Write deterministic-generation and routing tests**

```python
def test_same_seed_and_coordinate_produce_same_tile():
    assert FrontierGrid(1701).tile_at(22, 31) == FrontierGrid(1701).tile_at(22, 31)

def test_route_stays_in_bounds_and_avoids_impassable_tiles():
    grid = FrontierGrid(1701)
    result = grid.find_route((8, 9), (12, 12), known={(x, y) for x in range(6, 15) for y in range(6, 15)}, modifications={})
    assert result.reached
    assert all(0 <= x < 64 and 0 <= y < 64 and grid.tile_at(x, y).passable for x, y in result.path)
```

- [ ] **Step 2: Run `python backend/tests/test_terrain_engine.py` and confirm failure because `terrain_engine` does not exist**
- [ ] **Step 3: Implement immutable seeded tile derivation and deterministic A* routing with fixed neighbor ordering**
- [ ] **Step 4: Re-run the terrain tests and confirm they pass**
- [ ] **Step 5: Commit `backend/terrain_engine.py` and its tests**

### Task 2: Persistent Discovery, Routes, and Recovery

**Files:**
- Modify: `backend/persistent_world.py`
- Modify: `backend/persistent_world_app.py`
- Modify: `backend/tests/test_persistent_world.py`

**Interfaces:**
- Consumes: `FrontierGrid` from Task 1.
- Produces state keys `frontier`, `terrain_modifications`, `discoveries`, and actor `route`; actions `travel_route` and `observe_frontier`; filtered snapshot function `observed_snapshot(state, actor_id)`.

- [ ] **Step 1: Add failing tests for schema migration, private discovery, deterministic routed travel, stale revisions, idempotent retries, and reopen recovery**

```python
def test_one_players_discovery_does_not_reveal_hidden_tiles_to_another(self):
    joined = self._join_two_players()
    moved = self.store.apply_action(self.world_id, "route-a", "alice", {"type": "travel_route", "destination": [16, 16]}, joined["revision"], 1_001_000)
    alice = self.store.observed_snapshot(self.world_id, "alice")
    bob = self.store.observed_snapshot(self.world_id, "bob")
    self.assertGreater(len(alice["state"]["observed_tiles"]), len(bob["state"]["observed_tiles"]))
    self.assertNotIn("substrate", next(iter(bob["state"]["observed_tiles"].values())))
```

- [ ] **Step 2: Run the named tests and verify failures identify missing frontier state/actions**
- [ ] **Step 3: Migrate schema 30 to 31 with seed, 64×64 bounds, initial settlement discovery, sparse modifications, and per-entity evidence levels**
- [ ] **Step 4: Implement route proposal/commitment, deterministic tick advancement, discovery expansion, filtered snapshots, and authenticated API endpoints**
- [ ] **Step 5: Run the persistent-world suite and confirm existing world-clock and commitment tests remain green**
- [ ] **Step 6: Commit the persistent frontier integration**

### Task 3: Excavation, Deposit, and Plot Preparation Through Canonical Actions

**Files:**
- Modify: `backend/action_engine.py`
- Modify: `backend/persistent_world.py`
- Modify: `backend/tests/test_action_engine.py`
- Modify: `backend/tests/test_persistent_world.py`
- Modify: `docs/CANONICAL_ACTION_MIGRATION.md`

**Interfaces:**
- Produces action definitions `excavate_frontier_tile`, `deposit_carried_material`, and `prepare_frontier_plot`.
- Terrain mutation records contain `tile`, `before`, `after`, `removed_material`, `custody`, `inspector`, and causal parent IDs.

- [ ] **Step 1: Write failing pure-engine tests proving finite conservation, actor custody, independent verification, and equal human/AI blockers**

```python
def test_excavation_conserves_finite_stratum_and_places_output_in_actor_custody():
    before = world.resource_sites["tile:20,20"]["stock"]
    commissioned = run_verified_action(actor=human, action=excavate_frontier_tile("stone", 2), world=world)
    assert world.resource_sites["tile:20,20"]["stock"] == before - 2
    assert world.inventories[human.actor_id]["stone"] == 2
    assert commissioned.valuation_spendable is False
```

- [ ] **Step 2: Run the tests and confirm the new definitions/actions fail as absent**
- [ ] **Step 3: Implement the minimal action definitions, custody sources, reservations, deterministic samples, verification rules, and ledger outputs**
- [ ] **Step 4: Add failing persistent tests for excavation depth/passability, concurrent depletion, deposit transfer, and surveyed plot preparation**
- [ ] **Step 5: Integrate sparse tile mutations and communal-store deposits; remove the legacy direct regional-procurement path for these materials**
- [ ] **Step 6: Run action and persistent suites, then update the schema 31 migration note**
- [ ] **Step 7: Commit the canonical terrain actions**

### Task 4: World-Scoped Creator Control Plane

**Files:**
- Modify: `backend/owner_policy.py`
- Modify: `backend/persistent_world.py`
- Modify: `backend/persistent_world_app.py`
- Modify: `backend/tests/test_owner_policy.py`
- Modify: `backend/tests/test_persistent_world.py`

**Interfaces:**
- Produces `authorize_world_capability(claims, bound_user_id, world_id, capability) -> bool` and append-only `operator_audit` records.
- Observed snapshots return null-read privileged Sirix-1 fields and never return creator capability metadata.

- [ ] **Step 1: Write failing tests that a username alone grants nothing, a signed subject is bound to one world, ordinary snapshots hide privileges, embodied actions retain normal blockers, and operator amendments are separately audited**
- [ ] **Step 2: Run owner and persistent tests and confirm the expected authorization/privacy failures**
- [ ] **Step 3: Implement capability checks, explicit confirmation fields, protected audit records, reversible amendment metadata, and snapshot redaction**
- [ ] **Step 4: Run all security, owner-policy, and persistent tests**
- [ ] **Step 5: Commit the creator control-plane boundary**

### Task 5: Server-Observed Isometric Frontier

**Files:**
- Create: `frontend/src/lib/frontierView.cjs`
- Create: `frontend/electron/frontier-view.test.cjs`
- Modify: `frontend/src/pages/IsometricSettlement.jsx`
- Modify: `frontend/src/pages/IsometricSettlement.css`
- Modify: `frontend/src/lib/worldServer.js`
- Modify: `frontend/electron/authoritative-world-view.test.cjs`
- Modify: `frontend/package.json`

**Interfaces:**
- `projectObservedFrontier(snapshot, actorId) -> {tiles, route, actors, selections, status}` contains no hidden substrate.
- `submitTravelRoute(destination, expectedRevision)` sends intention only; client interpolation consumes authoritative route progress.

- [ ] **Step 1: Write a failing Node test that projects fog, terrain, elevation, excavation, route, and resources while rejecting hidden fields**

```javascript
test('frontier projection never exposes hidden substrate', () => {
  const view = projectObservedFrontier(snapshot, 'alice');
  assert.equal(view.tiles['20,20'].visibility, 'surface');
  assert.equal(Object.hasOwn(view.tiles['20,20'], 'substrate'), false);
});
```

- [ ] **Step 2: Run `pnpm test:desktop-store` and confirm the missing projection fails**
- [ ] **Step 3: Implement the pure projection and add it to the desktop test command**
- [ ] **Step 4: Replace fixed `MAP_SIZE` painting and local resource authority with a camera-centered observed-tile renderer, fog, elevation cues, resource silhouettes, pits, foundations, and route preview**
- [ ] **Step 5: Connect click-to-route, smooth interpolation, visible movement failures, extraction/deposit/prepare controls, and disconnected-server state**
- [ ] **Step 6: Run Node tests, production build, and a desktop smoke test; retain existing accessibility settings**
- [ ] **Step 7: Commit the isometric frontier client**

### Task 6: Reproducible Client and Server Download

**Files:**
- Modify: `frontend/package.json`
- Create: `scripts/package_frontier_release.ps1`
- Create: `docs/ALPHA33_RELEASE_NOTES.md`
- Create: `outputs/README-ALPHA33.txt`

**Interfaces:**
- Script produces `outputs/EoV-Alpha33-Windows-x64.zip`, `outputs/EoV-Alpha33-Persistent-Server.zip`, and `outputs/EoV-Alpha33-SHA256.txt` from tracked source plus generated builds.

- [ ] **Step 1: Add a failing package-manifest verification mode asserting required client/server files and forbidden secret/database patterns**
- [ ] **Step 1a: Add a failing version-consistency test that discovers user-visible version surfaces and rejects Alpha 32, `v0.1.0`, or any identifier not derived from `0.3.0-alpha.33`**
- [ ] **Step 2: Run verification and confirm failure because Alpha 33 artifacts do not exist**
- [ ] **Step 3: Set the single canonical version to `0.3.0-alpha.33`, update every watermarked display from that source, document implemented/simulated/deferred behavior, and implement deterministic staging, archive creation, and checksums**
- [ ] **Step 4: Run Python action, competency, security, society, and persistent suites; run Node tests and the production build**
- [ ] **Step 5: Package the Windows client and persistent server, verify each archive from a clean extraction, and launch the server health check**
- [ ] **Step 6: Inspect archive manifests for secrets, credentials, saves, databases, payment activation, and stale binaries**
- [ ] **Step 7: Commit release metadata and provide clickable local download files; publish only after verifying GitHub authentication and exact release scope**

## Plan Self-Review

- Every approved design requirement maps to a task.
- The authoritative kernel precedes persistence, physical actions, and UI.
- No task creates a parallel AI or local simulation authority.
- Function names, schema version 31, release Alpha 33, and custody semantics are consistent across tasks.
- The first deliverable remains bounded to the approved vertical slice.
