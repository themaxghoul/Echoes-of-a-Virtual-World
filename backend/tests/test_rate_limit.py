import asyncio
from threading import Lock
import unittest

from security import DuplicateKeyError, RateLimitExceeded, consume_rate_limit, rate_limit_key


class AtomicFakeCollection:
    def __init__(self):
        self.records = {}
        self.lock = Lock()

    async def find_one_and_update(self, query, update, upsert, return_document):
        del upsert, return_document
        key = query["key"]
        limit = query["count"]["$lt"]
        with self.lock:
            record = self.records.get(key)
            if record is not None and record["count"] >= limit:
                raise DuplicateKeyError("unique key already exists")
            if record is None:
                record = dict(update["$setOnInsert"], count=0)
                self.records[key] = record
            record["count"] += update["$inc"]["count"]
            return dict(record)


class RateLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_limit_is_atomic_under_concurrency(self):
        collection = AtomicFakeCollection()

        async def consume():
            try:
                await consume_rate_limit(
                    collection, scope="login", identity="ip:user", limit=10,
                    window_seconds=300, now_epoch=1000,
                )
                return True
            except RateLimitExceeded:
                return False

        outcomes = await asyncio.gather(*(consume() for _ in range(50)))
        self.assertEqual(10, sum(outcomes))

    async def test_new_window_gets_new_allowance(self):
        collection = AtomicFakeCollection()
        for now in (10, 11):
            await consume_rate_limit(collection, scope="mail", identity="actor", limit=2, window_seconds=60, now_epoch=now)
        with self.assertRaises(RateLimitExceeded) as denied:
            await consume_rate_limit(collection, scope="mail", identity="actor", limit=2, window_seconds=60, now_epoch=12)
        self.assertEqual(48, denied.exception.retry_after)
        remaining = await consume_rate_limit(collection, scope="mail", identity="actor", limit=2, window_seconds=60, now_epoch=60)
        self.assertEqual(1, remaining)

    def test_stored_key_does_not_expose_identity(self):
        key = rate_limit_key("login", "203.0.113.7:someone@example.test", 900)
        self.assertEqual(64, len(key))
        self.assertNotIn("someone", key)


if __name__ == "__main__":
    unittest.main()
