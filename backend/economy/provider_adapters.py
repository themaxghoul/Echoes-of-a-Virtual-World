"""Fail-closed provider evidence adapters for owner compute settlement.

These contracts intentionally contain no network client.  The currently known
Codex-plan path has no programmatic credit purchase or transfer capability;
it remains disabled regardless of environment configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any


class ProviderCapabilityError(RuntimeError):
    """The trusted provider registry does not permit this operation."""


_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_FIELD = re.compile(r"(?:api[_-]?key|secret|token|authorization|credential|password)", re.I)


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: str
    purchase: bool
    credit_transfer: bool
    usage_read: bool
    cost_read: bool

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider is required")
        for name in ("purchase", "credit_transfer", "usage_read", "cost_read"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")

    def evidence_hash(self) -> str:
        body = json.dumps({
            "provider": self.provider.strip(), "purchase": self.purchase,
            "credit_transfer": self.credit_transfer, "usage_read": self.usage_read,
            "cost_read": self.cost_read,
        }, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


class UnsupportedCodexPlanAdapter:
    """The explicit non-purchasing boundary for current Codex plans."""

    def __init__(self, environment: dict[str, str] | None = None):
        # Kept only for a backwards-compatible construction shape.  It is never
        # read: environment flags are not provider capability evidence.
        self._ignored_environment = dict(environment or {})

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities("openai_codex_plan", False, False, False, False)

    def submit(self, allocation: dict, provider_operation_id: str) -> dict:
        raise ProviderCapabilityError("Codex plan purchase and credit transfer are unsupported")


class RecordedOfficialBillingAdapter:
    """Normalize immutable evidence of a human-completed billing action only."""

    _FIELDS = frozenset({
        "provider", "receipt_id", "provider_transaction_id", "amount_minor",
        "currency", "completed_at_ms", "evidence_hash", "human_completed",
    })

    def normalize_receipt(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("receipt payload must be an object")
        unknown = set(payload) - self._FIELDS
        if unknown:
            if any(_SECRET_FIELD.search(str(key)) for key in unknown):
                raise ValueError("receipt payload contains a secret field")
            raise ValueError("receipt payload has unsupported fields")
        if set(payload) != self._FIELDS:
            raise ValueError("receipt payload is incomplete")
        if payload["human_completed"] is not True:
            raise ValueError("receipt must evidence a human-completed billing action")
        normalized = {}
        for key in ("provider", "receipt_id", "provider_transaction_id"):
            value = payload[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} is required")
            normalized[key] = value.strip()
        amount = payload["amount_minor"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("amount_minor must be a positive integer")
        currency = payload["currency"]
        if not isinstance(currency, str) or currency.lower() != "usd":
            raise ValueError("receipt currency must be usd")
        completed = payload["completed_at_ms"]
        if isinstance(completed, bool) or not isinstance(completed, int) or completed < 0:
            raise ValueError("completed_at_ms must be a non-negative integer")
        evidence = payload["evidence_hash"]
        if not isinstance(evidence, str) or not _HASH.fullmatch(evidence):
            raise ValueError("evidence_hash must be sha256 followed by 64 lowercase hexadecimal characters")
        normalized.update({
            "amount_minor": amount, "currency": "usd", "completed_at_ms": completed,
            "evidence_hash": evidence, "human_completed": True,
        })
        return normalized


class OpenAICostsNormalizer:
    """Parse official organization-cost response records without float money."""

    @classmethod
    def normalize(cls, payload: dict) -> list[dict]:
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("official costs payload must contain data")
        records: list[dict] = []
        for bucket in payload["data"]:
            if not isinstance(bucket, dict):
                raise ValueError("cost record must be an object")
            children = bucket.get("results") if isinstance(bucket.get("results"), list) else [bucket]
            for item in children:
                if not isinstance(item, dict):
                    raise ValueError("cost result must be an object")
                start = item.get("start_time", bucket.get("start_time"))
                end = item.get("end_time", bucket.get("end_time"))
                metadata = item.get("metadata", bucket.get("metadata"))
                if not isinstance(metadata, dict):
                    raise ValueError("cost record cannot be attributed to an operation")
                operation_id = metadata.get("eov_provider_operation_id")
                if not isinstance(operation_id, str) or not operation_id.strip():
                    raise ValueError("cost record cannot be attributed to an operation")
                start_ms, end_ms = cls._timestamps(start, end)
                amount = item.get("amount")
                if not isinstance(amount, dict):
                    raise ValueError("cost amount is required")
                currency = amount.get("currency")
                if not isinstance(currency, str) or currency.lower() != "usd":
                    raise ValueError("cost currency must be usd")
                records.append({
                    "provider_operation_id": operation_id.strip(),
                    "amount_minor": cls._minor_units(amount.get("value")),
                    "currency": "usd", "start_time_ms": start_ms, "end_time_ms": end_ms,
                    "line_item": item.get("line_item") if isinstance(item.get("line_item"), str) else None,
                })
        if not records:
            raise ValueError("official costs payload contains no cost records")
        return records

    @staticmethod
    def _timestamps(start: Any, end: Any) -> tuple[int, int]:
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise ValueError("cost start_time must be a non-negative integer")
        if isinstance(end, bool) or not isinstance(end, int) or end < start:
            raise ValueError("cost end_time must be a non-negative integer after start_time")
        # The official endpoint uses Unix seconds.  Preserve them as precise ms.
        return start * 1000, end * 1000

    @staticmethod
    def _minor_units(value: Any) -> int:
        if not isinstance(value, str):
            raise ValueError("cost amount must be a decimal string")
        try:
            decimal = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("cost amount must be a decimal string") from error
        if not decimal.is_finite() or decimal < 0:
            raise ValueError("cost amount must be non-negative")
        cents = decimal * Decimal(100)
        if cents != cents.to_integral_value():
            raise ValueError("cost amount cannot be represented in integer minor units")
        return int(cents)
