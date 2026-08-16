import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from economy import EconomyPolicy, IdempotencyConflict, InsufficientFunds, SimulationLedger


class SimulationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = SimulationLedger(Path(self.temp.name) / "ledger.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_double_entry_transfer_is_integer_balanced_and_non_spendable(self):
        result = self.ledger.transfer("fund-alice", "treasury", "alice", 1250, "verified-work:survey-1")
        self.assertFalse(result["spendable"])
        self.assertEqual(self.ledger.balance("alice"), 1250)
        self.assertEqual(self.ledger.balance("treasury"), -1250)
        self.assertTrue(self.ledger.audit()["balanced"])

    def test_exact_replay_returns_prior_result_without_duplicate_postings(self):
        first = self.ledger.transfer("reward-1", "treasury", "ada", 600, "inspection:evidence-1")
        replay = self.ledger.transfer("reward-1", "treasury", "ada", 600, "inspection:evidence-1")
        self.assertEqual(first, replay)
        self.assertEqual(self.ledger.balance("ada"), 600)
        self.assertTrue(self.ledger.audit()["balanced"])

    def test_idempotency_key_cannot_be_reused_for_different_intent(self):
        self.ledger.transfer("reward-1", "treasury", "ada", 600, "inspection:evidence-1")
        with self.assertRaises(IdempotencyConflict):
            self.ledger.transfer("reward-1", "treasury", "orin", 600, "inspection:evidence-1")

    def test_concurrent_debits_cannot_double_spend(self):
        self.ledger.transfer("fund-source", "treasury", "source", 10, "test-fixture:funding")

        def attempt(index):
            try:
                self.ledger.transfer(f"spend-{index}", "source", "receiver", 1, f"concurrent-order:{index}")
                return True
            except InsufficientFunds:
                return False

        with ThreadPoolExecutor(max_workers=12) as executor:
            outcomes = list(executor.map(attempt, range(40)))
        self.assertEqual(sum(outcomes), 10)
        self.assertEqual(self.ledger.balance("source"), 0)
        self.assertEqual(self.ledger.balance("receiver"), 10)
        self.assertTrue(self.ledger.audit()["balanced"])

    def test_failed_debit_leaves_no_partial_credit_or_operation(self):
        self.ledger.open_account("empty")
        with self.assertRaises(InsufficientFunds):
            self.ledger.transfer("bad-spend", "empty", "receiver", 1, "should-rollback")
        self.assertEqual(self.ledger.balance("empty"), 0)
        self.assertEqual(self.ledger.balance("receiver"), 0)
        self.assertTrue(self.ledger.audit()["balanced"])


class EconomyPolicyTests(unittest.TestCase):
    def test_real_value_routes_are_blocked_in_simulation(self):
        policy = EconomyPolicy("simulation")
        for path in ("/api/payments/deposit/checkout", "/api/earnings/withdraw", "/api/entity-earnings/wallet/player/1", "/api/ecosystem-support/contribute"):
            self.assertTrue(policy.blocks_path(path))
        self.assertFalse(policy.blocks_path("/api/economy/status"))
        self.assertFalse(policy.status("user-1")["real_value_enabled"])

    def test_configuration_cannot_enable_real_value_mode(self):
        with self.assertRaises(RuntimeError):
            EconomyPolicy("production")


if __name__ == "__main__":
    unittest.main()
