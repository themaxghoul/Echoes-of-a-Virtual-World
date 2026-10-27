# EoV 0.2.0-alpha.1 testing notes

This slice makes the 2.5D isometric settlement the primary `/play` client while preserving the earlier first-person prototype at `/play-3d`.

## Test loop

1. Open the isometric settlement from mode selection.
2. Move with WASD or the arrow keys.
3. Select residents and construction projects.
4. Place a workshop, laboratory, or storehouse blueprint.
5. Advance verified construction stages and reload to confirm local persistence.
6. While authenticated as the configured owner, chat with the private Jarvis panel, inspect account-scoped memories, then pin or forget them. When connected to the persistent server, propose a measurable public priority and observe its later council review.

## Alpha boundaries

- Browser fallback memory remains local to that browser profile. In the desktop build, the main process scopes Jarvis storage from the signed active owner session and rejects non-owner access.
- Jarvis responses are a UI and memory-scoring scaffold, not a connected model.
- Persistent-world directives are enforced by the server-bound owner UUID. Renderer flags only control presentation and are never sufficient authorization.
- Durable memory requires encryption, an audit log, retention controls, and explicit deletion.
- Work-order verification and CU accounting are not yet server-authoritative.
