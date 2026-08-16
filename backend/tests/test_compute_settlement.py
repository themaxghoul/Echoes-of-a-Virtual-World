import unittest

from economy.compute_settlement import SettlementUnavailable, evaluate_compute_settlement, require_compute_settlement


class ComputeSettlementBoundaryTests(unittest.TestCase):
    def test_openai_plan_credit_is_blocked_without_supported_purchase_capability_and_reviews(self):
        status = evaluate_compute_settlement({"provider": "openai-codex-plan"})

        self.assertEqual("blocked", status["status"])
        self.assertFalse(status["cu_spendable"])
        self.assertIn("provider_purchase_capability", status["blockers"])
        self.assertIn("federal_legal_review", status["blockers"])
        self.assertIn("state_legal_reviews", status["blockers"])
        self.assertIn("tax_review", status["blockers"])
        self.assertIn("labor_review", status["blockers"])
        self.assertIn("privacy_review", status["blockers"])
        self.assertIn("money_transmission_review", status["blockers"])
        self.assertIn("external_funding_receipt", status["blockers"])
        self.assertIn("human_spend_approval", status["blockers"])

    def test_compliance_documents_cannot_substitute_for_provider_capability(self):
        manifest = {
            "provider": "openai-codex-plan",
            "provider_purchase_capability": False,
            "federal_legal_review": "counsel:federal:2026-01",
            "state_legal_reviews": {"US-IL": "counsel:illinois:2026-01"},
            "tax_review": "cpa:tax:2026-01",
            "labor_review": "counsel:labor:2026-01",
            "privacy_review": "counsel:privacy:2026-01",
            "money_transmission_review": "counsel:bsa:2026-01",
            "external_funding_receipt": "bank-receipt:123",
            "human_spend_approval": "owner-approval:456",
        }

        status = evaluate_compute_settlement(manifest)

        self.assertEqual(["provider_purchase_capability"], status["blockers"])
        with self.assertRaisesRegex(SettlementUnavailable, "provider_purchase_capability"):
            require_compute_settlement(manifest)

    def test_cu_value_never_counts_as_external_funding(self):
        status = evaluate_compute_settlement({
            "provider": "future-provider",
            "provider_purchase_capability": True,
            "provisional_cu_milli": 10_000_000,
        })

        self.assertIn("external_funding_receipt", status["blockers"])
        self.assertFalse(status["cu_spendable"])


if __name__ == "__main__":
    unittest.main()
