# Alpha 36 Playable Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the supported Alpha 35 isometric client more comfortable to play and provide a downloadable desktop test build without advertising unfinished systems.

**Architecture:** Keep the current persistent-world service and canonical action model authoritative. Add only a presentation-level chat toggle; its messages continue through existing authenticated server commands. Treat the Cloudflare public-alpha and Unity repositories as references, not merge targets.

**Tech Stack:** React 19, React Router, Electron, Node's built-in test runner, Playwright, pnpm.

**Spec:** `docs/superpowers/specs/2026-10-26-alpha36-playable-controls-design.md`

## Global Constraints

- Isometric play remains the only promoted graphical mode.
- `T` must not intercept text entry or editable controls.
- Client presentation must never become authoritative world state.
- CU remains nonspendable and nonredeemable; no payment/provider settlement is added.
- Preserve all existing user changes; do not stage unrelated settlement-projection edits.
- Do not claim a public Pages release until the configured deployment and download URL are verified.

## Review Focus

- Pressing `T` while the chat input is focused must enter the letter rather than hide chat.
- Pressing `T` with a button or editable element focused must not steal that control's keyboard behavior.
- The drawer must remain usable on narrow screens without hiding the map permanently.
- Opening/closing chat must not disconnect, duplicate, or fabricate server conversation history.
- The package must be labeled as a playtest artifact rather than a public-production release.

---

### Task 1: Chat shortcut behavior

**Files:**
- Create: `frontend/src/lib/gameShortcuts.cjs`
- Create: `frontend/src/lib/gameShortcuts.test.cjs`
- Modify: `frontend/src/pages/IsometricSettlement.jsx`
- Modify: `frontend/src/pages/IsometricSettlement.css`
- Test: `frontend/src/lib/gameShortcuts.test.cjs`
- Test: `frontend/e2e/playable.spec.js`

**Interfaces:**
- `shouldToggleChat(event) -> boolean` returns true only for an unmodified `T` press outside inputs, textareas, selects, buttons, and content-editable targets.

- [ ] Add unit cases for game-focus T, input-focus T, button-focus T, and modifier-key T; run `node --test src/lib/gameShortcuts.test.cjs` from `frontend/` to observe the expected missing-module failure.
- [ ] Implement the helper and verify all unit cases pass.
- [ ] Add `chatOpen` state and an accessible `Chat · T` button; render the existing conversation panel as a drawer over the map and bind `T` to toggle it without altering message submission.
- [ ] Add a Playwright check that opens/closes the drawer with `T` and types `t` into its input without closing it.
- [ ] Run `pnpm run test:desktop-store` and `pnpm run test:e2e`; fix only regressions caused by this task.

### Task 2: Desktop playtest artifact

**Files:**
- Modify only if required: `frontend/package.json`, `frontend/src/buildInfo.json`, `DESKTOP_ALPHA.md`
- Create: `outputs/EoV-Alpha35-Playtest.zip`

- [ ] Build the current client with `pnpm run build`.
- [ ] Package with the existing `pnpm run desktop:package` workflow.
- [ ] Create a portable zip of the generated Electron app and include a concise playtest README naming setup, current limits, server requirements, and the tested build version.
- [ ] Confirm the executable, zip, and README exist; do not publish them to GitHub Pages until a Pages-target branch/deployment is established.

### Task 3: Follow-up implementation queue

- [ ] First-person remains hidden until camera input, collision, entity models and authenticated movement are all usable.
- [ ] Implement shared action adapters for item pickup/use and moving-while-crafting before adding an item hotbar.
- [ ] Add combat only after server-authoritative attack/dodge/block/skills actions, target rules, costs, failure, persistence and equal Samaritan/player requirements exist.
- [ ] Add vertical traversal only after terrain elevation and movement/collision share a persisted coordinate model.
- [ ] Keep CU as provisional accounting; evaluate a separate in-world spendable unit only through a versioned, auditable, nonredeemable ledger design.
- [ ] Build the public support page only after a verified owner-controlled checkout destination exists; disclose that donations do not automatically convert into OpenAI or Codex credits.

