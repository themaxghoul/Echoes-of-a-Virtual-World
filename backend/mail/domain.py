"""Pure address/domain rules; external DNS and email providers belong behind adapters."""

from __future__ import annotations

import re


USERNAME = re.compile(r"^[a-z0-9_]{3,32}$")
DOMAIN = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def internal_mailbox(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME.fullmatch(normalized):
        raise ValueError("username must be 3-32 letters, numbers, or underscores")
    return f"{normalized}@eov.local"


def normalize_custom_domain(domain: str) -> str:
    normalized = domain.strip().lower().rstrip(".")
    if normalized == "eov.local" or not DOMAIN.fullmatch(normalized):
        raise ValueError("custom domain must be a valid public DNS name")
    return normalized
