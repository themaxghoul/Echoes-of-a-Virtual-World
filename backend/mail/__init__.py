"""Provider-independent in-world mail domain."""

from .domain import internal_mailbox, normalize_custom_domain

__all__ = ["internal_mailbox", "normalize_custom_domain"]
