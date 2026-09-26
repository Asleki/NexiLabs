from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_LOCK = "7f312b1f9f86031e07664f6a126d88cabab2b11b"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_manifest_locks_additive_runtime_boundary_without_migration_or_worker_change():
    payload = json.loads(read("infrastructure/deployment/manifests/nexilabs-production-auth-p006-ui-10-4.json"))
    assert payload["sourceLockCommit"] == SOURCE_LOCK
    assert payload["privateListener"] == "127.0.0.1:8767"
    assert payload["publicBrowserNamespace"] == "/auth/*"
    assert payload["canonicalAdminNamespace"] == "/auth/admin/*"
    assert payload["databaseMigrationRequired"] is False
    assert payload["serviceWorkerChanged"] is False
    assert payload["roadmapChanged"] is False
    assert payload["privateCredentialMaterialPackaged"] is False


def test_systemd_service_is_loopback_only_and_uses_private_environment_file():
    unit = read("infrastructure/deployment/config/nexilabs-production-auth.service")
    assert "--host 127.0.0.1 --port 8767" in unit
    assert "EnvironmentFile=/etc/nexa/nexilabs-production-auth.env" in unit
    assert "User=nexa-auth" in unit
    assert "0.0.0.0" not in unit


def test_environment_template_has_exact_public_origin_and_no_real_secret():
    env = read("infrastructure/deployment/config/nexilabs-production-auth.env.example")
    assert "NEXILABS_PRODUCTION_AUTH_ALLOWED_ORIGINS=https://nexilabs.nexaecosystem.com" in env
    assert "NEXILABS_PRIVATE_ENIGMA_DIR=/etc/nexa/nexilabs-auth-private/enigma" in env
    assert "PGPASSWORD=__SET_ON_SERVER_ONLY__" in env
    assert "*" not in next(line for line in env.splitlines() if line.startswith("NEXILABS_PRODUCTION_AUTH_ALLOWED_ORIGINS="))


def test_deployment_never_copies_private_development_auth_boundary():
    deploy = read("infrastructure/deployment/scripts/deploy-nexilabs-production-auth.sh")
    assert 'cp -a "$REPO_ROOT/backend"' in deploy
    assert 'cp -a "$REPO_ROOT/development"' not in deploy
    assert "development/auth/private" in deploy  # explicit exclusion documentation
    assert "systemctl enable nexa-nexilabs-production-auth" in deploy
    assert "systemctl restart nexa-nexilabs-production-auth" in deploy


def test_deployment_enforces_exact_source_lock_before_release_mutation():
    deploy = read("infrastructure/deployment/scripts/deploy-nexilabs-production-auth.sh")
    assert f"EXPECTED_HEAD={SOURCE_LOCK}" in deploy
    assert 'git -C "$REPO_ROOT" rev-parse HEAD' in deploy
    assert '"$(git -C "$REPO_ROOT" rev-parse HEAD)" == "$EXPECTED_HEAD"' in deploy
    assert "repository HEAD does not match P006.UI.10.4 source lock" in deploy
    assert deploy.index("rev-parse HEAD") < deploy.index('rm -rf "$RELEASE"')


def test_transport_server_has_no_bootstrap_route_and_rejects_non_loopback_bind():
    server = read("backend/auth/production_auth_transport/server.py")
    assert '_LOOPBACK_HOSTS = {"127.0.0.1", "::1"}' in server
    assert "canonical_route_for_locked_authority" in server
    assert '"/bootstrap-admin"' not in server
    assert "build_service" in server


def test_successor_browser_client_is_same_origin_on_real_host_and_keeps_auth_no_store():
    client = read("frontend/src/app/auth/production-auth-client-p006-ui-10-4.js")
    assert 'return "";' in client
    assert 'request("/auth/developer/start"' in client
    assert '`/auth/admin/${suffix}`' in client
    assert 'cache: "no-store"' in client
    assert 'credentials: "same-origin"' in client


def test_no_migration_roadmap_or_service_worker_files_are_part_of_declared_runtime_manifest():
    manifest = read("infrastructure/deployment/manifests/nexilabs-production-auth-p006-ui-10-4.json")
    for forbidden in ("ROADMAP.md", "PWA_ROADMAP.md", "migration_manifest.json", "frontend/sw.js", "nexilabs-ptb11-sw.js"):
        assert forbidden not in manifest


def test_existing_frontend_seams_consume_successor_modules_without_rewriting_locked_clients_or_pages():
    runtime_client = read("frontend/src/app/auth/runtime-auth-client.js")
    admin_experience = read("frontend/src/app/auth/admin-authentication-experience.js")
    account_experience = read("frontend/src/app/account/account-enrollment-experience.js")
    assert 'from "./production-auth-client-p006-ui-10-4.js"' in runtime_client
    assert 'from "./production-auth-client-p006-ui-10-4.js"' in admin_experience
    assert 'adminWorkspaceMarkup' in admin_experience
    assert 'developer-account-enrollment-p006-ui-10-4.js' in account_experience
