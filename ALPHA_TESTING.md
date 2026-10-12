# EoV 0.2.0-alpha.1 testing notes

This slice makes the 2.5D isometric settlement the primary `/play` client while preserving the earlier first-person prototype at `/play-3d`.

## Test loop

1. Open the isometric settlement from mode selection.
2. Move with WASD or the arrow keys.
3. Select residents and construction projects.
4. Place a workshop, laboratory, or storehouse blueprint.
5. Advance verified construction stages and reload to confirm local persistence.
6. Chat with the private Jarvis panel, inspect scored memories, then pin or forget them.

## Alpha boundaries

- Settlement and Jarvis memory are browser-local in this slice.
- Jarvis responses are a UI and memory-scoring scaffold, not a connected model.
- Production Jarvis access must be enforced by a server-side owner role; usernames or client-side flags are not authorization.
- Durable memory requires encryption, an audit log, retention controls, and explicit deletion.
- Work-order verification and CU accounting are not yet server-authoritative.
