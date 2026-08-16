import os
import unittest

from economy.provider_adapters import (
    OpenAICostsNormalizer,
    ProviderCapabilityError,
    RecordedOfficialBillingAdapter,
    UnsupportedCodexPlanAdapter,
)


class ProviderAdapterTests(unittest.TestCase):
    RECEIPT_HASH = "sha256:" + ("a" * 64)

    def test_codex_plan_adapter_cannot_submit_even_when_environment_claims_enabled(self):
        adapter = UnsupportedCodexPlanAdapter(environment={"EOV_ENABLE_CODEX_SETTLEMENT": "true"})
        self.assertFalse(adapter.capabilities().purchase)
        self.assertFalse(adapter.capabilities().credit_transfer)
        with self.assertRaises(ProviderCapabilityError):
            adapter.submit({"allocation_id": "allocation-1"}, "provider-op-1")

    def test_recorded_receipt_accepts_completed_human_billing_evidence_and_strips_no_secrets(self):
        normalized = RecordedOfficialBillingAdapter().normalize_receipt({
            "provider": "openai",
            "receipt_id": "official-receipt-1",
            "provider_transaction_id": "transaction-1",
            "amount_minor": 25,
            "currency": "usd",
            "completed_at_ms": 2_400,
            "evidence_hash": self.RECEIPT_HASH,
            "human_completed": True,
        })
        self.assertEqual("official-receipt-1", normalized["receipt_id"])
        self.assertNotIn("api_key", normalized)
        with self.assertRaisesRegex(ValueError, "human-completed"):
            RecordedOfficialBillingAdapter().normalize_receipt({
                **normalized, "human_completed": False,
            })
        with self.assertRaisesRegex(ValueError, "secret"):
            RecordedOfficialBillingAdapter().normalize_receipt({
                **normalized, "api_key": "not-allowed",
            })

    def test_openai_costs_are_integer_minor_units_and_reject_wrong_or_ambiguous_amounts(self):
        payload = {"data": [{
            "object": "organization.costs.result",
            "amount": {"value": "0.06", "currency": "usd"},
            "start_time": 2,
            "end_time": 3,
            "metadata": {"eov_provider_operation_id": "provider-op-1"},
        }]}
        normalized = OpenAICostsNormalizer.normalize(payload)
        self.assertEqual(6, normalized[0]["amount_minor"])
        self.assertEqual("provider-op-1", normalized[0]["provider_operation_id"])
        with self.assertRaisesRegex(ValueError, "currency"):
            OpenAICostsNormalizer.normalize({"data": [{**payload["data"][0], "amount": {"value": "0.06", "currency": "eur"}}]})
        with self.assertRaisesRegex(ValueError, "decimal string"):
            OpenAICostsNormalizer.normalize({"data": [{**payload["data"][0], "amount": {"value": 0.06, "currency": "usd"}}]})


if __name__ == "__main__":
    unittest.main()
