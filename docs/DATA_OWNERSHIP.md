# Data ownership and migration posture

The legacy Python source currently references 88 MongoDB collection names. That breadth is not treated as 88 stable schemas. Most belong to prototype routers and remain unaudited and mutation-quarantined.

## Audited active collections

| Collection | Owning domain | Identity/uniqueness | Required indexes | Retention |
|---|---|---|---|---|
| `user_profiles` | identity | `id`, unique normalized `username`, optional unique normalized `email`, unique `mailbox_address` | unique username/email/mailbox | account lifetime; deletion workflow pending |
| `user_sessions` | identity | unique signed `sid`, bound `user_id` and token version | TTL `expires_at` | automatic expiry; logout revokes immediately |
| `websocket_tickets` | identity/realtime | SHA-256 ticket hash, user, location | TTL `expires_at` | one use or 60 seconds |
| `mail_messages` | in-world mail | UUID `id`; unique sender/idempotency key | recipient/time; sender/idempotency unique | alpha retains messages; user deletion/export pending |
| `security_rate_limits` | identity/security | opaque SHA-256 bucket key; atomic conditional count | unique `key`; TTL `expires_at` | automatic expiry after the active window |
| `mail_domains` | in-world mail | unique normalized public DNS domain | unique domain | pending claims are non-operational; expiry job pending |

Password hashes, session secrets, raw WebSocket tickets, and domain verification secrets are never returned from normal read routes. Authentication email and in-world mailbox address are separate fields.

## Persistent-world database

The authoritative world uses SQLite rather than MongoDB and owns `worlds`, `world_events`, `processed_actions`, `causal_projections`, and `runclock_lease`. World state currently migrates through explicit schema versions 1-17. WAL, full synchronous commits, foreign keys, idempotency keys, monotonic revisions, replay cursors, and a renewable runclock lease define its invariants.

The simulation-only economic domain owns `simulation_accounts`, `simulation_operations`, and `simulation_postings`. Operations are immutable, integer-valued, idempotent, transactional, and double-entry balanced.

## Legacy collection quarantine

All other discovered collection names are legacy/prototype data until a domain owner supplies:

- a versioned schema and migration;
- identity and ownership fields;
- unique, lookup, and TTL indexes;
- allowed state transitions;
- transactional boundaries and idempotency behavior;
- retention, export, erasure, and archival rules;
- privacy classification and read projection;
- recovery and reconciliation tests.

No new route may make a legacy collection consequential merely because a similarly named document already exists. The first extraction order is identity, economy, combat, and world state; provider integrations must sit behind ports/adapters rather than being imported into domain logic.
