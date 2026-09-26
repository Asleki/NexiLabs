from __future__ import annotations

import pytest

from backend.auth.production_auth_transport.contracts import (
    CANONICAL_ADMIN_ROUTES,
    DEFAULT_LOCAL_ORIGINS,
    canonical_route_for_locked_authority,
    normalize_origin,
    origin_allowed,
    parse_allowed_origins,
)


def test_canonical_admin_namespace_maps_to_locked_authority_without_changing_developer_routes():
    assert canonical_route_for_locked_authority("/auth/admin/eligibility") == "/admin/eligibility"
    assert canonical_route_for_locked_authority("/auth/admin/elevate/enigma") == "/admin/elevate/enigma"
    assert canonical_route_for_locked_authority("/auth/developer/start") == "/auth/developer/start"
    assert set(CANONICAL_ADMIN_ROUTES) == {
        "/auth/admin/eligibility",
        "/auth/admin/elevate",
        "/auth/admin/elevate/enigma",
        "/auth/admin/elevation/logout",
    }


def test_origin_normalization_is_exact_and_removes_only_default_port_or_root_slash():
    assert normalize_origin("https://NEXILABS.NEXAECOSYSTEM.COM/") == "https://nexilabs.nexaecosystem.com"
    assert normalize_origin("https://example.test:443") == "https://example.test"
    assert normalize_origin("http://127.0.0.1:8765") == "http://127.0.0.1:8765"


@pytest.mark.parametrize("value", [
    "*",
    "null",
    "file:///tmp/a",
    "https://user:pass@example.test",
    "https://example.test/path",
    "https://example.test?x=1",
    "https://example.test/#fragment",
])
def test_origin_normalization_rejects_broad_or_non_origin_values(value):
    with pytest.raises(ValueError):
        normalize_origin(value)


def test_allowed_origin_parser_deduplicates_and_default_is_local_only():
    assert parse_allowed_origins(None) == DEFAULT_LOCAL_ORIGINS
    assert parse_allowed_origins("https://nexilabs.nexaecosystem.com, https://NEXILABS.NEXAECOSYSTEM.COM/") == (
        "https://nexilabs.nexaecosystem.com",
    )
    assert all("nexaecosystem.com" not in origin for origin in DEFAULT_LOCAL_ORIGINS)


def test_origin_admission_accepts_no_origin_and_exact_match_only():
    allowed = parse_allowed_origins("https://nexilabs.nexaecosystem.com,http://127.0.0.1:8765")
    assert origin_allowed(None, allowed) is True
    assert origin_allowed("https://nexilabs.nexaecosystem.com", allowed) is True
    assert origin_allowed("https://evil.nexaecosystem.com", allowed) is False
    assert origin_allowed("http://nexilabs.nexaecosystem.com", allowed) is False
