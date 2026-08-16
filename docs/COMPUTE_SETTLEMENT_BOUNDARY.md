# EoV Compute Settlement Boundary

## Current conclusion

Verified EoV work may create a public, evidence-linked provisional CU record. It does not currently create money, OpenAI credit, Codex-plan capacity, or proof that an external bill can be paid.

As of August 16, 2026, the official OpenAI documentation describes adding API credits through the billing dashboard and exposes Usage and Costs APIs for observing consumption and invoice-aligned cost. It does not document an endpoint through which EoV can mint, transfer, or programmatically purchase Codex professional-plan credits. OpenAI also offers credits through specific programs, such as Codex for Students, but that is not a general conversion mechanism. This is a documentation finding, not a representation that no private commercial agreement could ever be negotiated.

Official references:

- [OpenAI API quickstart and billing](https://platform.openai.com/docs/quickstart/make-your-first-api-request)
- [OpenAI Usage and Costs API](https://platform.openai.com/docs/api-reference/usage/audio_transcriptions_object)
- [OpenAI developer community programs](https://developers.openai.com/community)

## Implemented boundary

The persistent server publishes `/worlds/{world_id}/public-cu-ledger`. The projection contains only commissioned, independently verified provisional claims. It:

- replaces private actor, verifier, action, and world identifiers with stable public references;
- excludes memories, conversations, exact private evidence, credentials, hidden terrain, and undiscovered state;
- publishes evidence and commission hashes;
- includes equal-and-opposite treasury and contributor postings;
- chains entries so alteration or reordering is detectable;
- labels every entry `CU-placeholder`, nonspendable, and externally unsettled;
- fails closed if a claim is spendable, unverified, unmatched, nonpositive, or lacks hashed commission evidence.

The server also publishes `/compute-settlement/readiness`. No environment variable can activate settlement. Readiness requires all of the following evidence:

1. A provider-supported purchase or settlement capability.
2. A federal legal review.
3. A legal review for every participating state or other jurisdiction.
4. Tax, labor-classification, privacy, and money-transmission reviews.
5. A receipt proving external funds exist independently of CU.
6. A human approval for the specific external spend.

CU never satisfies the external-funding requirement. A high CU valuation cannot pay a provider invoice unless a separate lawful revenue, grant, sponsor, or capital source supplies real funds.

## Federal review triggers

The precise legal result depends on facts and jurisdiction; this document is an engineering gate, not legal advice.

- FinCEN states that administrators or exchangers of convertible virtual currency may be money transmitters, subject to limitations and exemptions. Making CU redeemable or transferable for external value therefore requires specialist Bank Secrecy Act and state money-transmission review. See [FinCEN FIN-2013-G001](https://www.fincen.gov/resources/statutes-regulations/guidance/application-fincens-regulations-persons-administering).
- The IRS requires reporting of digital-asset income and describes tax consequences when digital assets are exchanged for services. Any redeemable CU or compute benefit requires tax characterization, valuation, records, and reporting analysis. See [IRS digital asset guidance](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions).
- The Department of Labor applies an economic-reality analysis to employee versus independent-contractor status. Paying people for repeated directed work can create wage, overtime, and classification obligations regardless of what the compensation unit is called. See [DOL worker-classification guidance](https://www.dol.gov/agencies/whd/flsa/misclassification/rulemaking/faqs).
- The FTC requires material incentives and connections affecting endorsements to be clearly disclosed. CU or compute incentives cannot be conditioned on positive public reviews, and relevant incentives must be disclosed. See [FTC endorsement guidance](https://www.ftc.gov/business-guidance/resources/advertising-faqs-guide-small-business).

State review cannot be completed until the operating entity, participant locations, eligible ages, custody model, transferability, and launch jurisdictions are declared. The application must remain blocked rather than infer a state from an IP address or device timezone.

## Lawful target flow

The intended future path is:

1. A negotiated work order reserves provisional CU from a disclosed treasury program.
2. Shared physical-action rules produce the result and causal evidence.
3. An independent reviewer verifies the outcome.
4. Commissioning appends a balanced claim to the private authoritative ledger.
5. The pseudonymous public ledger publishes the verified claim and its hash chain.
6. Governance may use verified claims to allocate a separately funded compute-sponsorship budget.
7. A human approves the expenditure after all provider and compliance gates pass.
8. An official provider mechanism receives externally funded payment.
9. Provider Costs data reconciles actual usage to the approved budget and public sponsorship record.

Steps 6–9 are not active. The current OpenAI/Codex professional-plan mechanism does not provide the programmatic settlement capability required for direct conversion.

## Information still required

Before legal review can be commissioned, the project must identify:

- the operating person or legal entity;
- launch state and every permitted participant jurisdiction;
- whether participants are consumers, contractors, employees, researchers, or volunteers;
- minimum age and guardian rules;
- whether CU is transferable between people;
- whether benefits are redeemable, expiring, refundable, or forfeitable;
- the external funding source and insolvency treatment;
- dispute, reversal, fraud, sanctions, and tax-reporting processes;
- the exact OpenAI or other compute-provider commercial agreement.
