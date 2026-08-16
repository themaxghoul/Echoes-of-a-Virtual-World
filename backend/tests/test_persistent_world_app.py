import unittest

from world_status import build_health_status


class PersistentWorldHealthTests(unittest.TestCase):
    def test_health_status_reports_world_tick_interval_and_process_uptime(self):
        snapshot = {
            "world_id": "founders-settlement",
            "revision": 17,
            "tick": 144,
            "state": {"clock": {"tick_seconds": 15}},
        }

        status = build_health_status(snapshot, writes_enabled=True, started_at_ms=1_000, now_ms=7_385_000)

        self.assertEqual(
            {
                "ok": True,
                "world_id": "founders-settlement",
                "revision": 17,
                "tick": 144,
                "tick_seconds": 15,
                "writes_enabled": True,
                "started_at_ms": 1_000,
                "uptime_seconds": 7_384,
            },
            status,
        )


if __name__ == "__main__":
    unittest.main()
