# Owner Compute Sponsorship Settlement Design

Date: 2026-08-16
Status: Approved architecture; written specification awaiting user review

## Purpose

Verified work performed through EoV's shared action system will directly determine allocations from an owner-only development-compute pool. The pool exists solely to fund continued development of Echoes of a Virtual World for the configured owner account. It is not a player withdrawal system, a transferable currency, wages, a guaranteed payout, or a promise that CU has cash value.

The complete target flow is:

`verified EoV work -> public CU claim -> conversion quote -> funded compute allocation -> owner approval -> provider operation -> usage/cost reconciliation -> public settlement receipt`

CU, external money, provider credits, and consumed compute remain separate conserved quantities. A conversion quote links them without pretending they are the same asset.

## Scope

This increment adds the missing settlement domain between the existing provisional CU ledger and an external compute provider. It supports:

- one beneficiary class: `eov_owner_development`;
- versioned integer conversion policies;
- externally funded reserve receipts;
- allocations linked to verified public CU claims;
- human approval for every provider operation;
- idempotent provider submission and receipt recording;
- OpenAI usage and cost reconciliation;
- privacy-preserving public settlement projections;
- fail-closed compliance and provider-capability gates.

It does not add player redemption, transfers, cash withdrawal, cryptocurrency, speculative pricing, automatic provider purchasing, or participant-owned compute balances.

## Authoritative boundaries

### Provisional CU ledger

The shared-action ledger remains authoritative for work provenance. Only commissioned actions with independently verified causal evidence may create CU claims. Settlement never edits, deletes, or revalues the underlying work record.

### Funding reserve ledger

External funds use a separate append-only double-entry ledger denominated in integer minor units, initially US cents. A funding receipt credits the compute reserve only after an authorized operator records evidence of funds received from a lawful source. CU cannot credit this ledger.

### Settlement ledger

The settlement ledger links eligible CU claims, conversion policies, reserve holds, approvals, provider operations, receipts, and reconciled costs. Its records are immutable events interpreted through an explicit state machine.

### Provider record

The provider is authoritative for actual credits, invoices, and usage. EoV may observe provider data and reconcile it, but may not invent successful purchases or mark compute delivered without provider evidence.

## Beneficiary and authority

The only beneficiary is an owner subject configured server-side. Requests never supply or override the beneficiary identity. Operator permissions live outside the simulated social hierarchy and create no in-world supernatural identity.

Three capabilities are distinct:

- `settlement_proposer` may create an allocation proposal from eligible claims;
- `settlement_approver` may approve a specifically quoted and funded proposal;
- `settlement_reconciler` may attach provider evidence and reconcile cost.

For the initial owner-operated release, one authenticated owner may hold all three capabilities, but each action is separately authenticated, timestamped, and audited. No endpoint infers authority from a username, URL identifier, local storage, or in-world role.

## Conversion policy

A policy contains:

- immutable policy ID and version;
- effective start and optional end time;
- eligible action types and evidence requirements;
- integer CU-milli numerator and funding-minor-unit denominator;
- minimum and maximum allocation per claim;
- aggregate program budget and per-period cap;
- beneficiary class fixed to `eov_owner_development`;
- funding source class;
- jurisdiction/compliance manifest hash;
- authorizing owner subject and approval timestamp.

The calculation uses integer arithmetic and rounds down. For example, a policy expressed as `cu_milli_per_funding_minor` calculates:

`quoted_funding_minor = floor(eligible_cu_milli / cu_milli_per_funding_minor)`

No production default rate exists. A policy has three lifecycle states: `draft`, `allocation_active`, and `settlement_active`. `allocation_active` requires an explicit positive rate, funded program cap, compliance manifest, and owner signature; it permits quotes, holds, and approval while making the unavailable provider boundary visible. `settlement_active` additionally requires independently evidenced provider capability compatible with the requested operation. Changing a rate creates a new version and never changes historical quotes.

## Allocation state machine

An allocation progresses through only these states:

1. `proposed` — eligible unallocated public CU claims and a policy version create a quote.
2. `funding_held` — an atomic reserve hold covers the quoted maximum external cost.
3. `approved` — the authenticated owner approves the exact quote, claims, provider, and expiry.
4. `provider_pending` — one idempotent provider operation has been recorded.
5. `provider_confirmed` — official provider evidence confirms the operation or availability of compute.
6. `reconciling` — provider usage/cost records are matched to the allocation.
7. `reconciled` — actual cost is captured, unused reserve is released, and a public receipt is appended.

Terminal alternatives are `rejected`, `expired`, `cancelled`, and `failed`. Illegal transitions fail without mutation. A provider timeout remains `provider_pending`; it never implies failure or success until reconciled by the same idempotency key.

## Claim eligibility and conservation

An allocation may consume only claims that:

- appear in the valid public CU hash chain;
- correspond to commissioned shared actions;
- remain nonspendable and externally unsettled;
- satisfy the selected policy's action and evidence rules;
- have not already been allocated under another live or completed settlement.

Allocation marks claims as committed to a settlement reference without changing their CU amount. Cancelling before provider confirmation releases the commitment. Reconciled claims remain permanently linked to the receipt.

Every funding movement has equal-and-opposite postings:

- funding receipt: external source -> available compute reserve;
- allocation hold: available reserve -> held reserve;
- provider capture: held reserve -> provider expense;
- release: held reserve -> available reserve.

Balances may not become negative. Operation IDs and request hashes enforce exact replay and reject conflicting reuse.

## Provider adapters

Adapters implement a narrow capability contract:

- report supported operation types;
- submit an idempotent owner-approved operation when supported;
- retrieve authoritative operation status;
- retrieve usage and costs for reconciliation;
- normalize provider receipts without exposing secrets.

The initial `openai_codex_plan` adapter reports purchase/credit-transfer capability as unsupported because current official documentation does not expose a programmatic mechanism. It cannot be enabled by an environment variable.

The initial OpenAI reconciliation adapter may read organization usage and cost data with an administrative credential. It does not purchase credits. Until a supported provider operation or commercial agreement exists, allocations may reach `approved` but not `provider_pending` for a Codex-plan purchase.

A future manual official-billing adapter may record a human-completed billing operation only when it includes an official receipt, provider transaction reference, exact amount/currency, timestamp, and cryptographic evidence hash. Recording a receipt does not itself prove usage; cost reconciliation remains required.

## API surface

Public read-only routes:

- `GET /worlds/{world_id}/public-cu-ledger`
- `GET /compute-settlement/readiness`
- `GET /compute-settlement/public-allocations`
- `GET /compute-settlement/public-receipts`

Authenticated owner routes:

- `POST /compute-settlement/funding-receipts`
- `POST /compute-settlement/policies`
- `POST /compute-settlement/allocations`
- `POST /compute-settlement/allocations/{id}/hold`
- `POST /compute-settlement/allocations/{id}/approve`
- `POST /compute-settlement/allocations/{id}/submit`
- `POST /compute-settlement/allocations/{id}/provider-receipt`
- `POST /compute-settlement/allocations/{id}/reconcile`
- `POST /compute-settlement/allocations/{id}/cancel`

All mutations derive the owner subject from the signed session, require an idempotency key, perform one database transaction, and return the persisted event. Sensitive provider evidence is private; public routes expose stable pseudonymous references and hashes.

## Public transparency

The public settlement projection includes:

- allocation and receipt sequence numbers;
- stable public claim and action references;
- policy ID/version and conversion formula;
- total eligible CU-milli;
- quoted, held, captured, released, and reconciled funding minor units;
- provider and operation type;
- status and timestamps;
- approval, provider receipt, cost-data, and compliance-manifest hashes;
- previous and current chain hashes.

It excludes credentials, legal names, email addresses, private memories, exact account identifiers, invoices containing personal information, and undiscovered world state. The projection must verify independently and fail closed on imbalance, broken claim linkage, invalid transitions, or hash-chain alteration.

## Compliance posture

The owner-only pool minimizes but does not eliminate legal obligations. Before external settlement becomes active, the program must record:

- operating person or legal entity;
- launch and operating jurisdictions;
- source and ownership of external funds;
- participant relationship and compensation disclosures;
- tax characterization and record-retention policy;
- labor/classification review for directed human work;
- privacy and age rules;
- sanctions and prohibited-funding-source controls;
- money-transmission analysis confirming the owner-only, nontransferable structure;
- dispute, reversal, fraud, and incident procedures;
- applicable provider agreement and capability evidence.

CU remains nontransferable and offers participants no personal redemption under this design. The game must disclose that contributing work may support EoV development but does not create wages, ownership, provider credits, or a personal financial claim unless a separate lawful agreement says otherwise.

## Failure and recovery

- Insufficient reserve funds prevent a hold.
- Duplicate claims prevent a proposal.
- Expired quotes release holds atomically.
- Changed policy versions never alter existing proposals.
- Missing or failed compliance gates prevent approval.
- Unsupported provider capabilities prevent submission.
- Network ambiguity preserves `provider_pending` and retries with the same key.
- Conflicting provider receipts enter an operator exception queue.
- Provider costs above the approved cap prevent automatic capture and require a new approval.
- Provider costs below the hold capture the actual amount and release the remainder.
- Interrupted writes recover through database transactions and idempotent replay.
- Public projection failure does not corrupt private authoritative records; it raises an integrity alarm and stops new settlement.

## Testing invariants

The implementation must prove:

- only independently verified, commissioned, unallocated CU claims are eligible;
- CU never credits the external funding reserve;
- beneficiary identity is server-derived and always owner-only;
- conversion arithmetic is deterministic integer math;
- policy versions do not retroactively change quotes;
- reserve holds and captures balance exactly and never go negative;
- every mutation is atomic and idempotent;
- illegal state transitions fail without mutation;
- unsupported provider capabilities cannot be bypassed;
- provider timeout cannot create duplicate operations;
- receipt and Costs reconciliation capture actual cost and release excess holds;
- public projections are pseudonymous, balanced, deterministic, and tamper-evident;
- private evidence and credentials never enter public output;
- restart and replay produce the same settlement state;
- humans and AI receive identical CU claim eligibility for identical verified work, while only the configured owner receives the external development-compute benefit.

## Delivery sequence

1. Implement the settlement state machine and schemas in an isolated economy module.
2. Add the external funding reserve and atomic holds using the existing integer simulation-ledger patterns.
3. Link settlement eligibility to the public CU projection and authoritative shared-action records.
4. Add the owner-only capability boundary and authenticated mutation routes.
5. Add the read-only OpenAI usage/cost reconciliation adapter and unsupported Codex-plan purchase adapter.
6. Publish chained public allocations and receipts.
7. Add clean-checkout tests and CI coverage.
8. Keep provider submission disabled until the compliance manifest, external funding source, and supported provider capability are real and independently reviewed.

## Completion criteria

This increment is complete when a test world can produce verified work, publish its CU claim, create an owner-only conversion quote, place an atomic hold against a separately funded reserve, record owner approval, reject unsupported Codex-plan submission, ingest a simulated authoritative provider receipt/cost record through the adapter contract, reconcile actual cost, release unused funds, and publish a valid privacy-preserving settlement receipt after restart.

The broader objective is complete only when a real supported provider operation has been executed and reconciled using real external funds under the required legal and provider agreements. The simulation and adapter tests alone do not prove that final condition.
