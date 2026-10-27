# Economy and concurrency boundary

## Current release posture

EoV is simulation-only. CU and all USD-, crypto-, wallet-, earnings-, deposit-, conversion-, and withdrawal-shaped data are prototype or shadow accounting. They are not spendable, redeemable, withdrawable, or a promise of value.

The authentication API accepts only `EOV_ECONOMY_MODE=simulation` or `shadow`. Every request under `/api/payments`, `/api/earnings`, `/api/entity-earnings`, and `/api/ecosystem-support` returns `503 SIMULATION_ECONOMY_ONLY` before authentication, route logic, provider construction, or database mutation. Setting a production or real-value mode prevents server startup. High-risk trade, reward, job, marketplace, inventory, and building mutations remain behind the legacy mutation quarantine.

This is deliberately stronger than hiding UI controls. Provider-facing code remains historical prototype source, but it has no reachable production path in this alpha.

## New economic domain

New consequential accounting belongs in `backend/economy`, outside the central application module. `SimulationLedger` provides:

- signed integer units rather than floating-point money;
- two equal-and-opposite postings for every transfer;
- `BEGIN IMMEDIATE` serialization for writes;
- an atomic conditional debit that prevents negative balances except explicitly configured system accounts;
- an immutable operation identifier and request hash;
- exact replay returning the original result;
- conflicting reuse of an idempotency key failing closed;
- rollback of the entire operation after any failed debit;
- account, posting, and per-operation reconciliation audits;
- no payment provider, deposit, conversion, redemption, or withdrawal capability.

The persistent-world service separately owns world revisions, action idempotency, SQLite WAL commits, bounded catch-up, replayable events, and a renewable leader lease. Legacy request handlers do not inherit those guarantees and remain quarantined until moved behind explicit domain services and transactional state machines.

## Gates before real value

Real-value work remains prohibited until all of the following are independently implemented and reviewed:

1. Server-derived identity and capability authorization on every financial operation.
2. A production ledger using integer minor units, immutable postings, and database transactions.
3. Unique idempotency constraints across API commands, task rewards, provider events, and retries.
4. Cryptographic webhook signature verification using raw request bodies and timestamp tolerance.
5. Provider event state machines that reject illegal or repeated transitions.
6. Automated provider-to-ledger reconciliation and an operator exception queue.
7. Atomic holds, capture, cancellation, refunds, chargebacks, and withdrawal reservations.
8. Rate limits, fraud controls, account takeover protection, privileged MFA, and security logging.
9. KYC/AML, sanctions, tax, age, regional, custody, consumer-protection, and money-transmission review where applicable.
10. Key rotation, secret isolation, backup restoration exercises, incident response, penetration testing, and independent financial audit.

No environment flag alone may cross this boundary.

## Reproducible regression gate

From a clean checkout with Python 3.12, Node 22, and pnpm 11.9.0:

```powershell
pwsh -File scripts/verify_core.ps1
```

The same commands run in `.github/workflows/core-regression.yml`. The gate compiles the isolated Python domains, runs authentication, persistent-world, competency, causality, society, concurrency, replay, and ledger tests, installs the exact frontend lockfile, runs desktop persistence tests, and builds the client.
