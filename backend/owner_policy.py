"""Small, dependency-free owner authorization policy shared by server paths."""

from typing import Any, Mapping, Optional


OWNER_ROLE = "sirix_1"
OWNER_ABILITIES = (
    "all",
    "owner_console",
    "jarvis_private",
    "audit_world",
    "create_world_content",
)


def is_bound_owner(actor: Mapping[str, Any], bound_user_id: Optional[str]) -> bool:
    """Require all owner claims to agree with the persisted immutable identity."""
    return bool(
        bound_user_id
        and actor.get("id") == bound_user_id
        and actor.get("is_owner") is True
        and actor.get("permission_level") == OWNER_ROLE
    )


def is_owner_session_subject(claims: Mapping[str, Any], bound_user_id: Optional[str]) -> bool:
    """Authorize a signed cross-service session against the immutable owner UUID."""
    return bool(bound_user_id and claims.get("sub") == bound_user_id)


def authorize_world_capability(claims: Mapping[str, Any], bound_user_id: Optional[str], world_id: str, capability: str) -> bool:
    """Bind operator authority to a signed subject, one world, and one capability."""
    if not is_owner_session_subject(claims, bound_user_id):
        return False
    scoped = claims.get("world_capabilities", {})
    if not isinstance(scoped, Mapping):
        return False
    capabilities = scoped.get(world_id, ())
    return isinstance(capabilities, (list, tuple, set)) and capability in capabilities
