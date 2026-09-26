"""P006.UI.10.4 Production authentication transport boundary."""

from .contracts import (
    CANONICAL_ADMIN_ROUTES,
    DEFAULT_LOCAL_ORIGINS,
    canonical_route_for_locked_authority,
    normalize_origin,
    origin_allowed,
    parse_allowed_origins,
)

__all__ = [
    "CANONICAL_ADMIN_ROUTES",
    "DEFAULT_LOCAL_ORIGINS",
    "canonical_route_for_locked_authority",
    "normalize_origin",
    "origin_allowed",
    "parse_allowed_origins",
]
