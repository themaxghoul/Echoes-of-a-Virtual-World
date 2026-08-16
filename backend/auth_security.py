"""Small HS256 session-token implementation with strict claim validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict


class SessionTokenError(ValueError):
    pass


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def validate_secret(secret: str) -> None:
    if len(secret.encode("utf-8")) < 32:
        raise SessionTokenError("EOV_SESSION_SECRET must contain at least 32 bytes")


def issue_session_token(user_id: str, token_version: int, secret: str, ttl_seconds: int = 3600, now: int | None = None) -> tuple[str, Dict[str, Any]]:
    validate_secret(secret)
    now = int(time.time()) if now is None else now
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {"iss": "eov-api", "aud": "eov-client", "sub": user_id, "sid": str(uuid.uuid4()), "ver": int(token_version), "iat": now, "nbf": now, "exp": now + ttl_seconds}
    encoded = f"{_b64encode(json.dumps(header, separators=(',', ':')).encode())}.{_b64encode(json.dumps(claims, separators=(',', ':')).encode())}"
    signature = _b64encode(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}", claims


def verify_session_token(token: str, secret: str, now: int | None = None) -> Dict[str, Any]:
    validate_secret(secret)
    try:
        header_part, claims_part, signature = token.split(".")
        encoded = f"{header_part}.{claims_part}"
        expected = _b64encode(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise SessionTokenError("invalid token signature")
        header = json.loads(_b64decode(header_part))
        claims = json.loads(_b64decode(claims_part))
    except SessionTokenError:
        raise
    except Exception as exc:
        raise SessionTokenError("malformed session token") from exc
    if header != {"alg": "HS256", "typ": "JWT"}:
        raise SessionTokenError("unsupported token header")
    current = int(time.time()) if now is None else now
    if claims.get("iss") != "eov-api" or claims.get("aud") != "eov-client" or not claims.get("sub") or not claims.get("sid"):
        raise SessionTokenError("invalid token claims")
    if not isinstance(claims.get("exp"), int) or current >= claims["exp"]:
        raise SessionTokenError("session token expired")
    if not isinstance(claims.get("nbf"), int) or current < claims["nbf"]:
        raise SessionTokenError("session token not active")
    return claims
