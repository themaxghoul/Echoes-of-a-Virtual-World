# EoV Alpha Capability Matrix

This file describes demonstrable behavior. It deliberately avoids using
"production ready" for alpha systems.

| Capability | State | Evidence and limits |
| --- | --- | --- |
| Windows desktop client | Implemented alpha | Portable Electron build; local saves use revisioned snapshots and recovery. |
| Desktop registration and login | Implemented alpha | Durable PBKDF2 password records, signed main-process sessions, account-scoped saves/routes, explicit logout revocation, and restart-safe Continue Journey. Desktop identity remains local and is not a multiplayer authorization token. |
| Server registration and sessions | Implemented alpha | Signed, expiring sessions; actor identity is derived from the session. Requires MongoDB and a strong server secret. |
| WebSocket authentication | Implemented alpha | Short-lived, single-use session-derived tickets in the persistent-world service. Multi-node coordination remains planned. |
| Legacy mutation safety | Quarantined | Mutating legacy endpoints are blocked unless explicitly migrated to actor-derived authorization. |
| Sensitive-operation rate limits | Implemented single-node/server alpha | Atomic Mongo buckets protect login, registration, WebSocket-ticket issuance, in-world mail, and domain claims. Distributed edge throttling and adaptive abuse detection remain planned. |
| Isometric exploration | Implemented alpha | Persistent world renders and responds in browser and desktop builds. A Playwright regression test guards against the Alpha.17 black-screen failure. |
| World clock and autonomous work | Implemented single-node alpha | Durable ticks, bounded offline catch-up, leases, causal events, NPC needs and work-order progression. Distributed leader election is planned. |
| Causal projection and reaction | Implemented single-node alpha | Committed player events are projected exactly once into perceptions and durable pending reactions; later ticks execute those reactions into NPC movement, memory, council knowledge, and consequence records. |
| Owner identity and creator directives | Implemented alpha | Luciferous is bound to an immutable account UUID. Owner-only Jarvis memory is session-scoped; server directives enter NPC perception, council review, evidence-gated public work, physical consequences, and later pressure decisions instead of directly editing reality. |
| Adventure and material discovery | Implemented server alpha | Settlement-boundary expeditions discover adjacent finite-stock regions; gathering changes regional stocks and player inventory with tool gates and extraction history. Region-specific visual tiles and hazards remain planned. |
| Embodied isometric resources | Implemented server-authoritative alpha | Visible trees, mineral seams, reed beds, staged wells, farm plots, cattle, and a staffed tool counter are persisted by region with coordinates, proximity, tool, energy, stock, growth-time, care, evidence, and history requirements. The desktop model remains an offline fallback. |
| Proximity conversation | Implemented alpha | Nearby residents persist replies and conversation memories; autonomous speech is generated from current needs and intentions. Server views filter speech by audibility. LLM-enhanced dialogue remains optional rather than required for a response. |
| Material scarcity feedback | Implemented server alpha | Finite regional extraction changes auditable provisional values; settlement shortages generate verified NPC procurement, evidence, council knowledge, provisional claims, and limited renewable-stock regeneration. |
| Reproducible player engineering | Implemented first vertical slice | Dimensioned SI lever-pump designs undergo peer review, material-consuming prototype assembly, measured testing, and independent reproduction. An installed unit wears with use, loses output, creates a persistent maintenance order, can fail, and can be restored by a supplied player or autonomous Ada under Dev and Mira's institutional record. Additional design archetypes and hazards remain planned. |
| Verified public water | Implemented first vertical slice | Player or autonomously collected raw water retains source custody, undergoes delayed independent lab testing, may be rejected because of worn equipment, receives provisional value only after acceptance, and is consumed by the residents with greatest hydration need. A shortage makes Emil physically collect and deliver a batch; rejection can trigger maintenance and a safer autonomous retry. Broader treatment, disease, sanitation, and distribution infrastructure remain planned. |
| Resident survival behavior | Implemented first vertical slice | Hunger and fatigue now produce spatial meal-seeking and rest actions. Meals are finite and evidenced; depletion becomes council food pressure. Interrupted public work preserves its phase and resumes after worker recovery. Dietary diversity, illness, sleep quality, households, and long-term health remain planned. |
| Autonomous communal cooking | Implemented first vertical slice | Meal shortages commission supplied cooking orders. Lena moves, consumes reserved finite ingredients and preparation time; Imani independently inspects before portions, recipe history, and provisional value enter the world. Accepted batches age, are consumed by earliest expiry, and become evidenced waste if neglected. Accumulated waste can validate drying, changing later material inputs and shelf life. Interactive technique and varied recipes remain planned. |
| Internal EoV mailbox | Implemented server alpha | Authenticated internal delivery and sender-derived identity. This is not Internet email. |
| Custom email domains | Prototype | Domain claims and DNS challenge generation exist. DNS verification, inbound/outbound SMTP, abuse handling, and provider adapters are not implemented. |
| CU valuation | Simulated | Verified contributions can receive provisional valuation. CU is non-spendable and remains a placeholder for the eventual Virtuconomy. |
| Real-money payments | Disabled | Deposit, withdrawal, earnings, conversion, wallet, and provider routes are blocked by startup policy and middleware. |
| Economic ledger | Verified isolated component | Integer, append-only, double-entry simulation ledger with atomic debit, idempotency, rollback, and reconciliation tests. It is not a regulated payment ledger. |
| AI dialogue/autonomy | Prototype, externally dependent | Core calls still depend on an environment-specific LLM integration. Provider adapters, deterministic fallbacks, and cost controls remain planned. |
| Clean-checkout verification | Implemented alpha | Pinned package manager lock, Mongo container, environment templates, one start script, core regression script, and CI workflow. |
| Automated regression gate | Implemented core alpha | Python domain tests, desktop Node tests, isometric Playwright smoke test, and frontend production build run in GitHub Actions. Legacy page coverage remains incomplete. |
| Data governance | Documented foundation | Active collection ownership and indexes are documented; legacy collection sprawl remains quarantined pending migrations and retention rules. |
| Unity / first-person / VR | Planned | No supported gameplay client. The current product focus is dependable 2.5D isometric play. |

## Release boundary

Alpha.23 is suitable for local and trusted pre-alpha testing. It is not suitable
for real-money custody, public untrusted hosting, or claims of a production-ready
autonomous society. Promotion requires distributed simulation ownership, broader
authorization review, provider isolation, migration tooling, operational
monitoring, abuse controls, and adversarial security testing.
