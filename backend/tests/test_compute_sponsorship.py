import tempfile
import unittest
from pathlib import Path

from economy import (
    ComputeSponsorshipStore,
    SettlementIdempotencyConflict,
)


class ComputeSponsorshipFundingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ComputeSponsorshipStore(Path(self.temp.name) / "settlement.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

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


if __name__ == "__main__":
    unittest.main()
