import json
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
        receipt = {
            "provider": "openai",
            "receipt_id": "official-receipt-1",
            "provider_transaction_id": "transaction-1",
            "provider_operation_id": "eov:allocation:" + ("a" * 32),
            "amount_minor": 25,
            "currency": "usd",
            "completed_at_ms": 2_400,
            "evidence_hash": self.RECEIPT_HASH,
            "human_completed": True,
        }
        normalized = RecordedOfficialBillingAdapter().normalize_receipt(receipt)
        self.assertRegex(normalized["receipt_id_commitment"], r"^sha256:[0-9a-f]{64}$")
        serialized = json.dumps(normalized, sort_keys=True)
        self.assertNotIn("official-receipt-1", serialized)
        self.assertNotIn("transaction-1", serialized)
        self.assertNotIn("api_key", serialized)
        with self.assertRaisesRegex(ValueError, "human-completed"):
            RecordedOfficialBillingAdapter().normalize_receipt({
                **receipt, "human_completed": False,
            })
        with self.assertRaisesRegex(ValueError, "secret"):
            RecordedOfficialBillingAdapter().normalize_receipt({
                **receipt, "api_key": "not-allowed",
            })
        with self.assertRaisesRegex(ValueError, "identifier"):
            RecordedOfficialBillingAdapter().normalize_receipt({
                "provider": "openai", "receipt_id": "sk-live-secret", "provider_transaction_id": "transaction-1",
                "provider_operation_id": "eov:allocation:" + ("a" * 32), "amount_minor": 25,
                "currency": "usd", "completed_at_ms": 2_400, "evidence_hash": self.RECEIPT_HASH,
                "human_completed": True,
            })

    def test_openai_costs_are_integer_minor_units_and_reject_wrong_or_ambiguous_amounts(self):
        payload = {"data": [{
            "object": "organization.costs.result",
            "amount": {"value": "0.06", "currency": "usd"},
            "start_time": 2,
            "end_time": 3,
            "id": "cost-record-1",
            "metadata": {"eov_provider_operation_id": "provider-op-1"},
        }]}
        normalized = OpenAICostsNormalizer.normalize(payload)
        self.assertEqual(6, normalized[0]["amount_minor"])
        self.assertEqual("provider-op-1", normalized[0]["provider_operation_id"])
        self.assertRegex(normalized[0]["record_commitment"], r"^sha256:[0-9a-f]{64}$")
        with self.assertRaisesRegex(ValueError, "currency"):
            OpenAICostsNormalizer.normalize({"data": [{**payload["data"][0], "amount": {"value": "0.06", "currency": "eur"}}]})
        with self.assertRaisesRegex(ValueError, "decimal string"):
            OpenAICostsNormalizer.normalize({"data": [{**payload["data"][0], "amount": {"value": 0.06, "currency": "usd"}}]})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            OpenAICostsNormalizer.normalize({"data": [payload["data"][0], payload["data"][0]]})


if __name__ == "__main__":
    unittest.main()
