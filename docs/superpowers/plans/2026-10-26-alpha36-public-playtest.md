# Alpha 36 Public Playtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native inline execution in this task). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release a coherent Alpha 36 Windows client/server playtest with a dedicated support page and persistent, needs-aware Samaritan roaming.

**Architecture:** Keep the current Python persistent-world tick authoritative and reuse its passable route progression for Samaritan travel. A tagged GitHub Release builds the desktop app and self-hosted server bundle; GitHub Pages provides version-matched download links and project/support information.

**Tech Stack:** Python 3.12, FastAPI/SQLite, React 19, Electron 37, pnpm, Playwright, GitHub Actions Pages and Releases.

**Spec:** `docs/superpowers/specs/2026-10-26-alpha36-public-playtest-design.md`

## Global Constraints

- No client-side authority for NPC movement or world state.
- AI roaming must remain deterministic, knowledge-bounded, needs-aware, and subordinate to active commitments.
- No duplicate simulation kernel; retain the authenticated persistent-world service.
- Do not advertise hosted multiplayer or unfinished game modes.
- No spendable CU, real-money checkout, or automatic provider-credit claims.
- Preserve uncommitted user changes; do not stage `backend/economy/settlement_projection.py` or its test.
- No release or Pages-publication claim until live URLs and release assets are verified.

## Review Focus

- A route cannot pass through unknown or impassable terrain; test a blocked destination and a passable discovered path.
- NPCs with urgent survival needs or active shared-action commitments do not start leisure routes; test both cases.
- Retries/reloads preserve deterministic route identity and movement; test same-seed replay and persisted snapshot.
- Narrow viewports and keyboard focus remain usable; test sidebar and chat interactions at desktop/mobile widths.
- Release/page links cannot point to a mismatched/nonexistent asset or claim active donations; test filenames and page copy.

---

### Task 1: Needs-aware autonomous travel

**Files:**
- Modify: `backend/persistent_world.py`
- Test: `backend/tests/test_persistent_world.py`

**Interfaces:**
- Add `_process_autonomous_roaming(state, tick) -> list[dict]` and call from `reduce_world_tick` after need/initiative selection. Eligible residents receive persisted `route` entries consumed by `_advance_travel_routes`.

- [ ] Add backend tests for deterministic route selection, one-tile-per-tick travel, valid passability/discovery, and blocking by survival urgency or canonical commitments; run targeted tests to observe expected failures.
- [ ] Implement stable destination selection using only current-region discovered public places and `FrontierGrid.find_route`; persist route reason/target, reveal local terrain on each segment, emit route/memory evidence, and keep critical survival/work precedence.
- [ ] Re-run targeted backend tests and full persistent-world suite.

### Task 2: In-game HUD refinement

**Files:**
- Modify: `frontend/src/pages/IsometricSettlement.jsx`
- Modify: `frontend/src/pages/IsometricSettlement.css`
- Test: `frontend/e2e/playable.spec.js`

**Interfaces:**
- Presentation-only grouping/layout; all actions continue using existing world API and server snapshots.

- [ ] Extend E2E checks for readable world status, resident task/location visibility, and chat/camera controls on desktop and narrow viewport.
- [ ] Refine the isometric header/control overlays/sidebar hierarchy, responsive behavior, contrast, and focus states without adding fake or inert actions.
- [ ] Run frontend unit, Playwright, and production build checks.

### Task 3: Dedicated Support / Playtest Pages surface

**Files:**
- Create: `docs/support/index.html`
- Create: `.github/workflows/deploy-support-pages.yml`
- Create: `docs/support/README.md`
- Test: `frontend/src/lib/supportPage.test.cjs`

- [ ] Add content-contract tests for current build status, matching release filenames, server setup, feedback link, and absence of active donation claims.
- [ ] Build a responsive accessible EoV-themed landing page with playtest assets, transparent requirements/limits, contribution links, and no unsupported checkout.
- [ ] Configure Pages deployment from `docs/` via GitHub Actions and document the required repository Pages setting.

### Task 4: Reproducible Alpha 36 Release assets

**Files:**
- Modify: `frontend/package.json`, `frontend/src/buildInfo.json`, `frontend/electron/version-consistency.test.cjs`, `outputs/README-ALPHA35-PLAYTEST.txt`
- Create: `.github/workflows/release-playtest.yml`
- Create: `docs/support/PLAYTEST-README.txt`

- [ ] Add checks that the version watermark and package version agree and release asset names match the support page.
- [ ] Bump version to `0.3.0-alpha.36`; update all watermark displays and playtest notes.
- [ ] Add tagged-release automation that runs the frozen frontend install, test suites, production build, Windows package, and backend checks; attach `EoV-Alpha36-Windows-x64.zip` and `EoV-Alpha36-Persistent-Server.zip` to a GitHub Release.
- [ ] Build/verify assets locally, run full tests, and inspect the complete diff before pushing the authorized release branch/tag.

### Task 5: Publication verification

**Files:**
- No production-code files.

- [ ] Push the completed branch and the `eov-alpha36` tag only after all checks pass.
- [ ] Verify the Actions run, Pages deployment, public page URL, release URL, two asset links, and checksums; report failures honestly and leave no dead public download link.
