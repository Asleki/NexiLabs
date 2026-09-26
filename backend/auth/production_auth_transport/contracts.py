"""P006.UI.10.4 same-origin Production-auth transport contracts.

The locked P006.UI.10.3 authority continues to own authentication semantics.
This module only governs the successor browser-facing namespace and exact Origin
admission required by the deployed NexiLabs PWA.
"""
from __future__ import annotations

from urllib.parse import urlsplit

CANONICAL_ADMIN_ROUTES = {
    "/auth/admin/eligibility": "/admin/eligibility",
    "/auth/admin/elevate": "/admin/elevate",
    "/auth/admin/elevate/enigma": "/admin/elevate/enigma",
    "/auth/admin/elevation/logout": "/admin/elevation/logout",
}

DEFAULT_LOCAL_ORIGINS = (
    "http://127.0.0.1:8765",
    "http://localhost:8765",
)


def canonical_route_for_locked_authority(path: str) -> str:
    """Translate only the canonical Admin successor namespace.

    Developer/session routes already live under ``/auth/*`` in the locked
    authority and therefore pass through unchanged. Unknown paths also pass
    through so the locked handler remains the final not-found authority.
    """
    value = str(path or "")
    return CANONICAL_ADMIN_ROUTES.get(value, value)


def normalize_origin(origin: str) -> str:
    """Return a canonical exact web Origin or raise ``ValueError``.

    Wildcards, opaque origins, credentials, non-HTTP schemes and URL material
    outside the origin tuple are rejected. This prevents a configuration value
    from silently becoming a broad CORS policy.
    """
    value = str(origin or "").strip()
    if not value or value == "*" or value.lower() == "null":
        raise ValueError("origin must be an explicit http(s) origin")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("origin must use http or https and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("origin must not include credentials")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("origin must not include path, query or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("origin contains an invalid port") from exc
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    default_port = 443 if parsed.scheme == "https" else 80
    port_suffix = "" if port in {None, default_port} else f":{port}"
    return f"{parsed.scheme}://{host}{port_suffix}"


def parse_allowed_origins(raw: str | None) -> tuple[str, ...]:
    """Parse a comma-separated allowlist, defaulting only to bounded local PWA origins."""
    if raw is None or not str(raw).strip():
        return tuple(DEFAULT_LOCAL_ORIGINS)
    result: list[str] = []
    seen: set[str] = set()
    for item in str(raw).split(","):
        normalized = normalize_origin(item)
        if normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    if not result:
        raise ValueError("at least one allowed Origin is required")
    return tuple(result)


def origin_allowed(origin: str | None, allowed_origins: tuple[str, ...]) -> bool:
    """Admit non-browser requests or an exact configured browser Origin."""
    if origin is None or not str(origin).strip():
        return True
    try:
        normalized = normalize_origin(origin)
    except ValueError:
        return False
    return normalized in set(allowed_origins)
