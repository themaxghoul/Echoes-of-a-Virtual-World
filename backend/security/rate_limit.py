"""Atomic fixed-window limits for security-sensitive API ingress."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any

try:
    from pymongo import ReturnDocument
    from pymongo.errors import DuplicateKeyError
except ImportError:  # Keeps the pure domain testable without the server extras.
    class ReturnDocument:
        AFTER = True

    class DuplicateKeyError(Exception):
        pass


@dataclass(frozen=True)
class RateLimitExceeded(Exception):
    retry_after: int


def rate_limit_key(scope: str, identity: str, bucket_start: int) -> str:
    normalized = f"{scope.strip().lower()}\x00{identity.strip().lower()}\x00{bucket_start}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def consume_rate_limit(
    collection: Any,
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
    now_epoch: int,
) -> int:
    """Consume one allowance atomically and return the remaining allowance.

    A unique index on ``key`` makes a failed conditional update race resolve as
    a duplicate insert, which is treated as a denied request. ``expires_at`` is
    suitable for a Mongo TTL index and deliberately outlives the active bucket.
    """
    if limit < 1 or window_seconds < 1:
        raise ValueError("Rate limit and window must be positive")
    bucket_start = now_epoch - (now_epoch % window_seconds)
    retry_after = max(1, bucket_start + window_seconds - now_epoch)
    key = rate_limit_key(scope, identity, bucket_start)
    try:
        record = await collection.find_one_and_update(
            {"key": key, "count": {"$lt": limit}},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {
                    "key": key,
                    "scope": scope,
                    "bucket_start": bucket_start,
                    "expires_at": datetime.fromtimestamp(
                        bucket_start + (window_seconds * 2), timezone.utc
                    ),
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as exc:
        raise RateLimitExceeded(retry_after) from exc
    if not record:
        raise RateLimitExceeded(retry_after)
    return max(0, limit - int(record["count"]))
