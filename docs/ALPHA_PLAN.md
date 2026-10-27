# Playable alpha implementation plan

**Goal:** Publish selectable browser clients and a deployable persistent shared sandbox.
**Execution:** Inline in the existing isolated fresh clone, feature branch `feat/playable-public-alpha`; user authorized edits, Git push and publication.
**Architecture:** See [ALPHA_DESIGN.md](ALPHA_DESIGN.md). Python/FastAPI + SQLite, native ES modules and canvas, GitHub Pages, Docker/Render.

## Global constraints
Retain legacy prototype and Unity work. No real-money operations. Never commit secrets or runtime databases. Document actual deployment status. Single runtime worker. Text mode must not fetch graphics modules.

## Tasks and interfaces
1. [ ] Kernel and ledger (`alpha/kernel.py`, `alpha/tests/test_kernel.py`): write and run failing persistence, membership growth, deterministic terrain, collision, resource/action, conversation, ledger conservation and replay tests. Implement `Kernel(path)`, `register(name,password)`, `authenticate(token)`, `join(player_id)`, `snapshot(player_id)`, `command(player_id,data)` and `step(dt)`. Run `python -m pytest alpha/tests/test_kernel.py` until green.
2. [ ] Network service (`alpha/app.py`, `alpha/tests/test_service.py`): exercise invalid credentials, protected commands, input bounds, chunk limits and two authenticated WebSockets before implementing. HTTP `/api/session`, `/api/login`, `/api/world`, `/api/chunk`, `/api/command`, `/api/ledger`; WebSocket `/ws` authenticates in its first message. Commands consume kernel API. Run full alpha tests.
3. [ ] Clients (`docs/play/`): shared connection/controller, independently imported story/isometric/first-person renderers, mode selection and Unity status. Explicit disconnect errors, login/resume, keyboard/touch movement, collapsible chat, gather/build/research controls. Test three modes and concurrent browsers against local runtime; verify story loads no graphics module.
4. [ ] Hosting and handoff (`Dockerfile`, `render.yaml`, `.github/workflows/pages.yml`, README, `docs/HANDOFF.md`): package runtime and Pages assets, documented persistent storage, backups and account steps. Run local HTTP and browser checks, independent code review, fix important findings, push reviewed commits and enable Pages if account access permits.

## Review focus
Reconnect must not duplicate membership or starter credit. Forged movement/balances must be rejected. Replayed and concurrent commands must not duplicate resources or transfers. Offline clients must not present a fake shared world. Unconfigured hosting must give actionable status. Tests use temporary local databases; legacy remote integration tests are not run against somebody else's deployed preview.

## Execution record
- Inspection complete at base `faa21f4`; no AGENTS.md in repository. No existing deploy setup or user hosting account. Python dependencies will be installed in a workspace virtual environment.
- Ruling: use the freshly cloned feature branch as isolation; no second checkout needed.
- Ruling: preserve prototype and introduce an explicitly labelled alpha slice because legacy unauthenticated financial/world endpoints must not become the public multiplayer service.
- Ruling: use SQLite persistent disk for alpha, avoiding a second paid MongoDB service; legacy MongoDB saves are not migrated.

## Free-tier execution update
Kernel, authenticated service, three lazy-loaded views and Cloudflare adaptation implemented. Paid hosting was rejected by the user; Workers Free is the selected public deployment. Tests: Python 13 passed, Cloudflare Node 8 passed. Review findings corrected: protected commons/home escape, stale socket detection, idle message suppression and position batch rollback retry. Deployment accepted; public verification and GitHub publication remain the final checks. HANDOFF.md is the current operational reference.
