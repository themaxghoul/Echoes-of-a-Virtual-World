# Owner Compute Sponsorship Settlement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert independently verified EoV work into owner-only development-compute allocations backed by separately receipted funds, owner approval, provider evidence, cost reconciliation, and privacy-preserving public receipts.

**Architecture:** Add one isolated SQLite-backed settlement domain beside the existing simulation ledger. It resolves eligible claims from the authoritative public CU projection, conserves external funding with double-entry postings, enforces an explicit allocation state machine, delegates provider behavior through narrow adapters, and exposes owner-authenticated mutations plus public chained projections through the persistent server. Existing 64×64 frontier routing, discovery, excavation, harvesting, building, and rendering remain authoritative and receive regression coverage rather than a parallel world model.

**Tech Stack:** Python 3.12 standard library, SQLite WAL transactions, FastAPI, existing signed-session owner policy, unittest, React 19, Playwright, pnpm 11.9.0.

## Global Constraints

- The sole external benefit class is `eov_owner_development`; beneficiary identity is derived from the signed owner session and never accepted from request data.
- CU remains `CU-placeholder`, nontransferable, nonspendable, and separately conserved from USD, provider credit, and consumed compute.
- Only commissioned shared actions with independently verified causal evidence may support an allocation.
- External funding uses integer minor units and must be backed by a receipt hash; CU can never fund the reserve.
- Conversion uses versioned integer arithmetic and rounds down.
- Every mutation is one SQLite transaction with an idempotency key and request hash.
- No environment flag may fabricate compliance approval, external funds, a provider capability, provider success, or delivered compute.
- The current Codex-plan adapter remains submission-disabled until a supported provider operation or commercial agreement exists.
- Public output is pseudonymous, balanced, deterministic, tamper-evident, and excludes credentials, account identifiers, private memories, and undiscovered world state.
- Free roaming in the isometric open world remains available through the existing server-authoritative route, discovery, and terrain systems.

---

### Task 1: Transactional Funding Reserve

**Files:**
- Create: `backend/economy/compute_sponsorship.py`
- Create: `backend/tests/test_compute_sponsorship.py`
- Modify: `backend/economy/__init__.py`

**Interfaces:**
- Produces `ComputeSponsorshipStore(database_path: Path | str)`.
- Produces `record_funding(operation_id: str, owner_subject: str, amount_minor: int, currency: str, source_class: str, evidence_hash: str, received_at_ms: int) -> dict`.
- Produces `funding_balance(account: str = "reserve:available", currency: str = "usd") -> int` and `audit_funding() -> dict`.
- Produces exceptions `SettlementError`, `SettlementIdempotencyConflict`, `SettlementInsufficientFunds`, and `SettlementTransitionError`.

- [ ] **Step 1: Write failing funding-conservation and idempotency tests**

```python
def test_receipted_external_funding_is_balanced_and_cu_cannot_fund_reserve(self):
    result = self.store.record_funding(
        "fund-1", "owner-uuid", 2_500, "usd", "owner_capital",
        "sha256:external-receipt-1", 1_000,
    )
    self.assertEqual(2_500, result["amount_minor"])
    self.assertEqual(2_500, self.store.funding_balance())
    self.assertTrue(self.store.audit_funding()["balanced"])
    with self.assertRaisesRegex(ValueError, "CU cannot fund"):
        self.store.record_funding("fund-cu", "owner-uuid", 10, "usd", "CU-placeholder", "sha256:cu", 1_001)

def test_funding_receipt_replay_is_exact_and_conflicting_reuse_fails(self):
    first = self.store.record_funding("fund-1", "owner-uuid", 500, "usd", "grant", "sha256:r1", 1_000)
    self.assertEqual(first, self.store.record_funding("fund-1", "owner-uuid", 500, "usd", "grant", "sha256:r1", 1_000))
    with self.assertRaises(SettlementIdempotencyConflict):
        self.store.record_funding("fund-1", "owner-uuid", 600, "usd", "grant", "sha256:r1", 1_000)
```

- [ ] **Step 2: Run `python -m unittest tests.test_compute_sponsorship` from `backend` and verify failure because `economy.compute_sponsorship` is absent**
- [ ] **Step 3: Implement WAL/FULL SQLite setup with `settlement_operations`, `settlement_accounts`, `settlement_postings`, and `funding_receipts`; use `BEGIN IMMEDIATE`, integer checks, request hashes, exact replay, and rollback**
- [ ] **Step 4: Implement funding ingress as equal-and-opposite postings from `external-receipts:{currency}` to `reserve:available:{currency}`; permit negative balance only on the external-receipts contra account**
- [ ] **Step 5: Run the new tests and verify they pass, then run `tests.test_simulation_ledger` to prove the existing provisional ledger is unchanged**
- [ ] **Step 6: Commit `compute_sponsorship.py`, its exports, and funding tests with `feat: add receipted compute funding reserve`**

### Task 2: Versioned Conversion Policies and Authoritative Claim Resolution

**Files:**
- Modify: `backend/economy/compute_sponsorship.py`
- Create: `backend/economy/settlement_service.py`
- Modify: `backend/tests/test_compute_sponsorship.py`
- Create: `backend/tests/test_settlement_service.py`

**Interfaces:**
- Produces `create_policy(operation_id: str, owner_subject: str, policy: dict, approved_at_ms: int) -> dict`.
- Produces `activate_policy(operation_id: str, owner_subject: str, policy_id: str, target_state: str, evidence: dict, activated_at_ms: int) -> dict` where `target_state` is `allocation_active` or `settlement_active`.
- Produces `SettlementService(store, world_store, provider_registry, owner_subject)`.
- Produces `SettlementService.propose_allocation(operation_id: str, world_id: str, policy_id: str, public_claim_ids: list[str], now_ms: int) -> dict`.

- [ ] **Step 1: Write failing policy arithmetic and immutability tests**

```python
def test_policy_quotes_with_integer_round_down_and_never_revalues_history(self):
    first = self._create_allocation_policy("policy-1", version=1, cu_milli_per_funding_minor=1_000)
    self.store.activate_policy("activate-1", "owner-uuid", first["policy_id"], "allocation_active", self.valid_allocation_evidence, 2_000)
    quote = self.service.propose_allocation("quote-1", self.world_id, first["policy_id"], [self.claim_id], 2_100)
    self.assertEqual(2, quote["quoted_funding_minor"])
    self._create_allocation_policy("policy-2", version=2, cu_milli_per_funding_minor=500)
    self.assertEqual(2, self.store.get_allocation(quote["allocation_id"])["quoted_funding_minor"])
```

- [ ] **Step 2: Write failing claim-eligibility tests using a real `PersistentWorldStore` calibration claim**

```python
def test_proposal_resolves_claims_server_side_and_rejects_unverified_or_reused_claims(self):
    claim_id = self._run_world_until_verified_calibration_claim()
    allocation = self.service.propose_allocation("quote-1", self.world_id, self.policy_id, [claim_id], 2_100)
    self.assertEqual("proposed", allocation["state"])
    self.assertEqual("eov_owner_development", allocation["beneficiary_class"])
    with self.assertRaisesRegex(SettlementError, "already committed"):
        self.service.propose_allocation("quote-2", self.world_id, self.policy_id, [claim_id], 2_101)
```

- [ ] **Step 3: Run both test modules and confirm expected failures for missing policy tables, service, and claim commitment**
- [ ] **Step 4: Implement immutable `settlement_policies`, `settlement_claim_commitments`, and `settlement_allocations` tables; store policy snapshots and integer quote results on each allocation**
- [ ] **Step 5: Implement `SettlementService` so it calls `project_public_cu_ledger(world_store.snapshot(world_id))`, validates `verify_public_chain`, resolves only requested public entry IDs, and never accepts amounts, actor IDs, beneficiary IDs, or evidence hashes from the caller**
- [ ] **Step 6: Implement policy lifecycles: `draft -> allocation_active -> settlement_active`; require positive rate, funded program cap, compliance-manifest hash, and owner signature for allocation activation; additionally require provider capability evidence for settlement activation**
- [ ] **Step 7: Run the new tests plus `tests.test_public_ledger` and `tests.test_persistent_world`; verify all pass**
- [ ] **Step 8: Commit with `feat: quote owner compute from verified CU claims`**

### Task 3: Holds, Owner Approval, Cancellation, and Expiry

**Files:**
- Modify: `backend/economy/compute_sponsorship.py`
- Modify: `backend/economy/settlement_service.py`
- Modify: `backend/tests/test_compute_sponsorship.py`
- Modify: `backend/tests/test_settlement_service.py`

**Interfaces:**
- Produces `hold_allocation(operation_id, allocation_id, owner_subject, now_ms) -> dict`.
- Produces `approve_allocation(operation_id, allocation_id, owner_subject, approval_hash, expires_at_ms, now_ms) -> dict`.
- Produces `cancel_allocation(operation_id, allocation_id, owner_subject, reason, now_ms) -> dict`.
- Produces `expire_due(operation_id, now_ms) -> list[dict]`.

- [ ] **Step 1: Write failing lifecycle and funding-conservation tests**

```python
def test_hold_approval_and_cancel_are_atomic_owner_only_and_release_funds(self):
    allocation = self._proposed_allocation(quoted_funding_minor=200)
    with self.assertRaises(SettlementInsufficientFunds):
        self.store.hold_allocation("hold-0", allocation["allocation_id"], "owner-uuid", 2_200)
    self._fund(500)
    held = self.store.hold_allocation("hold-1", allocation["allocation_id"], "owner-uuid", 2_200)
    self.assertEqual("funding_held", held["state"])
    self.assertEqual(300, self.store.funding_balance("reserve:available"))
    approved = self.store.approve_allocation("approve-1", held["allocation_id"], "owner-uuid", "sha256:approval", 9_000, 2_300)
    cancelled = self.store.cancel_allocation("cancel-1", approved["allocation_id"], "owner-uuid", "provider unavailable", 2_400)
    self.assertEqual("cancelled", cancelled["state"])
    self.assertEqual(500, self.store.funding_balance("reserve:available"))
    self.assertTrue(self.store.audit_funding()["balanced"])
```

- [ ] **Step 2: Add failing tests for illegal transitions, conflicting idempotency, non-owner subjects, concurrent holds, expiry, and claim commitment release**
- [ ] **Step 3: Run the focused tests and verify failures correspond to absent lifecycle operations**
- [ ] **Step 4: Implement the transition table and append-only `settlement_events`; perform state validation, postings, allocation update, and claim commitment changes in one `BEGIN IMMEDIATE` transaction**
- [ ] **Step 5: Derive the beneficiary from the store's configured owner subject; reject any mismatched subject before mutation**
- [ ] **Step 6: Implement deterministic expiry that releases held funds and claim commitments only before provider confirmation**
- [ ] **Step 7: Run focused and concurrent tests repeatedly, then commit with `feat: enforce compute allocation approvals and holds`**

### Task 4: Provider Capability and OpenAI Cost Reconciliation Adapters

**Files:**
- Create: `backend/economy/provider_adapters.py`
- Create: `backend/tests/test_provider_adapters.py`
- Modify: `backend/economy/settlement_service.py`
- Modify: `backend/economy/compute_sponsorship.py`
- Modify: `backend/tests/test_settlement_service.py`

**Interfaces:**
- Produces immutable `ProviderCapabilities(provider: str, purchase: bool, credit_transfer: bool, usage_read: bool, cost_read: bool)`.
- Produces `UnsupportedCodexPlanAdapter` with all mutating capabilities false and no environment-driven override.
- Produces `RecordedOfficialBillingAdapter` that accepts a previously completed human billing receipt only through `normalize_receipt(payload: dict) -> dict`.
- Produces `OpenAICostsNormalizer.normalize(payload: dict) -> list[dict]` for official `/v1/organization/costs` responses.
- Produces service methods `submit_allocation`, `record_provider_receipt`, and `reconcile_allocation`.

- [ ] **Step 1: Write failing adapter tests**

```python
def test_codex_plan_adapter_cannot_submit_even_when_environment_claims_enabled(self):
    adapter = UnsupportedCodexPlanAdapter(environment={"EOV_ENABLE_CODEX_SETTLEMENT": "true"})
    self.assertFalse(adapter.capabilities().purchase)
    with self.assertRaises(ProviderCapabilityError):
        adapter.submit({"allocation_id": "allocation-1"}, "provider-op-1")

def test_openai_costs_are_integer_minor_units_and_reject_wrong_currency(self):
    normalized = OpenAICostsNormalizer.normalize(self.official_cost_fixture)
    self.assertEqual(6, normalized[0]["amount_minor"])
    with self.assertRaisesRegex(ValueError, "currency"):
        OpenAICostsNormalizer.normalize(self.non_usd_cost_fixture)
```

- [ ] **Step 2: Write failing end-to-end tests for `approved -> provider_pending -> provider_confirmed -> reconciling -> reconciled`, duplicate provider events, timeout replay, cost below hold, and cost above cap**
- [ ] **Step 3: Run tests and verify the adapters and lifecycle methods are absent**
- [ ] **Step 4: Implement dependency-free adapter contracts, strict receipt fields, decimal-string-to-cents conversion using `Decimal`, provider operation uniqueness, and secret-free normalized evidence**
- [ ] **Step 5: Implement provider transitions; require `settlement_active` policy and supported capability before submission; preserve `provider_pending` on ambiguous timeout and reuse the same provider idempotency key**
- [ ] **Step 6: Implement reconciliation so actual cost captures `reserve:held:{allocation_id}` to `expense:provider:{provider}` and atomically releases the remainder; costs above the approved hold create an exception without capture**
- [ ] **Step 7: Run all economy tests and commit with `feat: reconcile owner compute provider costs`**

### Task 5: Privacy-Preserving Public Allocations and Receipts

**Files:**
- Create: `backend/economy/settlement_projection.py`
- Create: `backend/tests/test_settlement_projection.py`
- Modify: `backend/economy/compute_sponsorship.py`

**Interfaces:**
- Produces `project_public_settlement(store: ComputeSponsorshipStore) -> dict`.
- Produces `verify_public_settlement_chain(projection: dict) -> bool`.
- Public schema is `eov-public-compute-sponsorship/v1`.

- [ ] **Step 1: Write failing public-projection tests**

```python
def test_public_projection_links_claim_policy_funding_and_receipt_without_private_identity(self):
    projection = project_public_settlement(self.reconciled_store)
    self.assertTrue(verify_public_settlement_chain(projection))
    self.assertEqual(0, projection["totals"]["posting_balance_minor"])
    serialized = json.dumps(projection, sort_keys=True)
    self.assertNotIn("owner-uuid", serialized)
    self.assertNotIn("openai-admin-key", serialized)
    self.assertIn("sha256:provider-receipt", serialized)
```

- [ ] **Step 2: Add failing tamper, reorder, broken-claim-link, imbalance, and private-field leakage tests**
- [ ] **Step 3: Run the module and confirm failure because the projection is absent**
- [ ] **Step 4: Implement a stable pseudonymous projection with sequence, public claim refs, policy version/formula, CU-milli, funding postings, state timestamps, evidence hashes, prior hash, and chain hash**
- [ ] **Step 5: Make projection fail closed on invalid transitions, missing claim commitment, unbalanced postings, unsupported currency, or missing provider/cost evidence for reconciled records**
- [ ] **Step 6: Run projection, public-CU, and deterministic-replay tests; commit with `feat: publish compute sponsorship receipts`**

### Task 6: Owner-Authenticated Settlement API

**Files:**
- Modify: `backend/persistent_world_app.py`
- Modify: `backend/tests/test_persistent_world_app.py`
- Modify: `backend/economy/compute_settlement.py`

**Interfaces:**
- Public routes: `GET /compute-settlement/public-allocations` and `GET /compute-settlement/public-receipts`.
- Owner routes match the approved design under `/compute-settlement/*` and require `Depends(authorize_owner)` plus `Idempotency-Key`.
- Request bodies never include `owner_subject`, `beneficiary_id`, claim amount, funding balance, or provider capability.

- [ ] **Step 1: Write failing route tests with `FastAPI TestClient` for public reads, missing tokens, non-owner tokens, valid owner requests, missing idempotency keys, client-supplied identity rejection, replay, and restart recovery**
- [ ] **Step 2: Run the route tests and verify 404/422 failures for missing routes and schemas**
- [ ] **Step 3: Construct one `ComputeSponsorshipStore` on `EOV_SETTLEMENT_DATABASE` defaulting to the persistent-world database path; construct `SettlementService` with the existing world store and server-derived `OWNER_USER_ID`**
- [ ] **Step 4: Add bounded Pydantic bodies and map domain errors to stable 400, 403, 409, 422, and 503 responses; never echo provider secrets or private receipt payloads**
- [ ] **Step 5: Update `/compute-settlement/readiness` to report policy, reserve, compliance, provider, approval, and reconciliation gates from persisted evidence rather than a hard-coded manifest**
- [ ] **Step 6: Run security, owner-policy, app, settlement, and restart tests; commit with `feat: expose owner compute settlement API`**

### Task 7: Public Compute Status UI Without Breaking Open-World Free Roam

**Files:**
- Create: `frontend/src/pages/ComputeSponsorship.jsx`
- Modify: `frontend/src/App.js`
- Modify: `frontend/src/components/GameNavigation.jsx`
- Modify: `frontend/src/lib/worldServer.js`
- Create: `frontend/e2e/compute-sponsorship.spec.js`
- Modify: `frontend/e2e/isometric-frontier.spec.js`

**Interfaces:**
- Produces `fetchPublicComputeSponsorship() -> Promise<object>` and `fetchComputeReadiness() -> Promise<object>`.
- Adds a read-only `/compute-sponsorship` route showing claim totals, allocation states, reserve/cost totals, provider capability, blockers, and public receipt hashes.
- Does not expose funding mutation or approval controls to ordinary players.

- [ ] **Step 1: Write a failing Playwright test that renders mocked public allocation/receipt data, shows `Owner development pool`, `CU is not player-redeemable`, and no withdrawal/purchase controls**
- [ ] **Step 2: Extend the isometric frontier test to route from `[8,9]` to a distant observed tile, advance authoritative ticks, confirm smooth client interpolation, and assert the compute status route did not replace or shrink the 64×64 world**
- [ ] **Step 3: Run both specs and verify failure for the missing compute page while recording the frontier baseline**
- [ ] **Step 4: Implement the read-only page, navigation entry, server fetch methods, disconnected state, integrity warning, and accessible ledger table**
- [ ] **Step 5: Run all Playwright tests, desktop-store tests, and the production build; verify free roaming, fog, discovery, route progress, excavation, and story chat remain available**
- [ ] **Step 6: Commit with `feat: show public compute sponsorship status`**

### Task 8: Reproducible Verification, Migration Note, and Inactive-Provider Proof

**Files:**
- Modify: `scripts/verify_core.ps1`
- Modify: `.github/workflows/core-regression.yml`
- Modify: `docs/COMPUTE_SETTLEMENT_BOUNDARY.md`
- Create: `docs/OWNER_COMPUTE_SPONSORSHIP_MIGRATION.md`
- Modify: `docs/FEATURE_MATRIX.md`

**Interfaces:**
- The regression gate compiles and tests every new settlement module.
- The migration note classifies legacy earnings/withdrawal code as quarantined, the provisional CU ledger as retained, the new sponsorship store as authoritative for owner compute allocation, and Codex-plan submission as disabled.

- [ ] **Step 1: Add all new economy, API, projection, and frontend tests to the local and CI gates; run the gate once and record any pre-existing unrelated failures separately**
- [ ] **Step 2: Update the boundary documentation with the owner-only decision, policy lifecycle, public routes, funding source requirements, official OpenAI Costs endpoint, and explicit statement that no supported Codex-plan purchase API is currently documented**
- [ ] **Step 3: Write the migration matrix with columns `legacy system`, `status`, `replacement`, `data migration`, and `removal gate`; include `EarningsHub`, VE$/USD claims, wallets, withdrawals, Stripe deposits, CU valuation, and public CU projection**
- [ ] **Step 4: Run `python -m unittest` for the explicit clean regression module list, `pnpm run test:desktop-store`, `pnpm run test:e2e`, and `pnpm run build`**
- [ ] **Step 5: Run a temporary-world end-to-end proof: create world, complete calibration, project CU, record funding, quote, hold, approve, reject unsupported Codex submission, reconcile a recorded test-provider cost, restart, and verify the public receipt chain**
- [ ] **Step 6: Inspect diffs for credentials, private identifiers, payment activation, client-authoritative beneficiary fields, and regressions to open-world movement**
- [ ] **Step 7: Commit documentation and regression updates with `docs: define owner compute sponsorship boundary`**

## Plan Self-Review

- Every approved design section maps to at least one task: funding, policy, claims, lifecycle, provider adapters, reconciliation, public transparency, APIs, compliance gates, failure recovery, tests, and migration.
- The settlement domain is cohesive; frontend visibility and regression integration are delivery surfaces rather than parallel financial systems.
- Exact interfaces use `ComputeSponsorshipStore`, `SettlementService`, adapter capability objects, and one public projection schema consistently across tasks.
- The plan contains no default conversion rate, fake provider success, automatic purchasing, participant redemption, or environment-controlled capability bypass.
- The existing shared-action/public-CU pipeline remains authoritative for work, and the existing frontier remains authoritative for open-world movement and physical state.
- The broader objective is not considered complete until real externally funded provider settlement is supported, executed, legally cleared, and reconciled.
