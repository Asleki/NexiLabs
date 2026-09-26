from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[3]
HISTORICAL_FRONTEND_SW_SHA256 = (
    "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d"
)
PTB11_EDGE_SW_SHA256 = (
    "25b5d67499bcd1a9ddef13492788348e8dbedc13c4cdd0d231fb543f46334a4e"
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def digest(relative: str) -> str:
    return sha256((ROOT / relative).read_bytes()).hexdigest()


def test_ptb11_manifest_locks_offline_capability_and_live_authority():
    manifest = json.loads(
        read(
            "infrastructure/deployment/manifests/"
            "nexilabs-offline-live-authority-boundary-manifest.json"
        )
    )
    assert manifest["milestoneId"] == "PTB.11"
    assert manifest["sourceLockCommit"] == "082b7e2016f9cc35188a54c7a413ae399f69a7b6"
    assert manifest["predecessorMilestone"] == "NEXILABS.PAB.1"
    assert manifest["maintenanceClassification"] == (
        "SECURITY_COMPATIBILITY_MAINTENANCE_EXCEPTION"
    )
    assert manifest["offlineCapability"]["applicationShellAllowed"] is True
    assert manifest["offlineCapability"]["simulationAllowed"] is True
    assert manifest["offlineCapability"]["genericLiveAuthorityCachingAllowed"] is False
    assert manifest["liveAuthority"]["pathPrefixes"] == ["/oauth2", "/auth", "/api/v1"]
    assert manifest["liveAuthority"]["serviceWorkerCacheReadsAllowed"] is False
    assert manifest["liveAuthority"]["serviceWorkerCacheWritesAllowed"] is False
    assert manifest["liveAuthority"]["offlineFallbackAllowed"] is False
    assert manifest["serviceWorker"]["historicalFrontendWorkerImmutable"] is True
    assert manifest["edge"]["serviceWorkerServedFromPwaUpstream"] is False
    assert manifest["edge"]["serviceWorkerServedFromGovernedEdgeAsset"] is True
    assert manifest["databaseChanges"] is False
    assert manifest["apiContractChanges"] is False
    assert manifest["roadmapMutationAllowed"] is False


def test_ptb11_preserves_frontend_worker_and_adds_exact_edge_worker():
    assert digest("frontend/sw.js") == HISTORICAL_FRONTEND_SW_SHA256
    assert digest("infrastructure/deployment/config/nexilabs-ptb11-sw.js") == PTB11_EDGE_SW_SHA256
    historical = read("frontend/sw.js")
    successor = read("infrastructure/deployment/config/nexilabs-ptb11-sw.js")
    assert "LIVE_AUTHORITY_PATH_PREFIXES" not in historical
    assert "LIVE_AUTHORITY_PATH_PREFIXES" in successor
    assert 'CACHE_NAME = "nexilabs-shell-v17"' in historical
    assert 'CACHE_NAME = "nexilabs-shell-v17"' in successor
    assert "nexilabs-refresh-p006-ui-10-4-r2" in successor
    assert "FRONTEND_ACCESS_INTEGRATION_PATHS" in successor


def test_private_ptb11_template_preserves_google_gate_and_serves_governed_worker():
    text = read(
        "infrastructure/deployment/config/"
        "Caddyfile.nexilabs.development-private.ptb11.template"
    )
    assert "handle /oauth2/*" in text
    assert "reverse_proxy 127.0.0.1:4180" in text
    assert "forward_auth 127.0.0.1:4180" in text
    assert "uri /oauth2/auth" in text
    assert "@unauthorized status 401" in text
    assert "/oauth2/sign_in?rd=" in text
    assert 'X-NexiLabs-Access-Mode "DEVELOPMENT_PRIVATE"' in text
    assert "handle /sw.js" in text
    assert "root * /usr/share/nexa/nexilabs-access" in text
    assert "rewrite * /ptb11-sw.js" in text
    assert 'header Cache-Control "no-cache, max-age=0"' in text
    assert 'header Service-Worker-Allowed "/"' in text
    assert "file_server" in text
    assert "private-sw.js" not in text


def test_private_ptb11_template_routes_live_authority_network_only():
    text = read(
        "infrastructure/deployment/config/"
        "Caddyfile.nexilabs.development-private.ptb11.template"
    )
    assert "handle /api/v1/*" in text
    assert "reverse_proxy __NEXILABS_INFRASTRUCTURE_API_UPSTREAM__" in text
    assert "handle /auth/*" in text
    assert "reverse_proxy __NEXILABS_PRODUCTION_AUTH_UPSTREAM__" in text
    assert text.count('header Cache-Control "no-store"') >= 3
    assert "reverse_proxy __NEXILABS_PWA_UPSTREAM__" in text


def test_public_ptb11_template_keeps_inner_authorities_and_serves_governed_worker():
    text = read(
        "infrastructure/deployment/config/Caddyfile.nexilabs.public.ptb11.template"
    )
    assert 'X-NexiLabs-Access-Mode "PUBLIC"' in text
    assert "forward_auth" not in text
    assert "127.0.0.1:4180" not in text
    assert "handle /oauth2/*" in text
    assert 'respond "Not Found" 404' in text
    assert "handle /api/v1/*" in text
    assert "handle /auth/*" in text
    assert "handle /sw.js" in text
    assert "root * /usr/share/nexa/nexilabs-access" in text
    assert "rewrite * /ptb11-sw.js" in text
    assert "file_server" in text


def test_ptb11_renderer_and_worker_installer_fail_closed():
    renderer = read(
        "infrastructure/deployment/scripts/render-nexilabs-ptb11-caddy.sh"
    )
    installer = read(
        "infrastructure/deployment/scripts/install-nexilabs-ptb11-worker.sh"
    )
    assert "DEVELOPMENT_PRIVATE)" in renderer
    assert "PUBLIC)" in renderer
    assert "invalid NEXILABS_ACCESS_MODE" in renderer
    assert "NEXILABS_PWA_UPSTREAM" in renderer
    assert "NEXILABS_INFRASTRUCTURE_API_UPSTREAM" in renderer
    assert "NEXILABS_PRODUCTION_AUTH_UPSTREAM" in renderer
    assert "validate_private_upstream" in renderer
    assert "EXPECTED_SHA256" in installer
    assert PTB11_EDGE_SW_SHA256 in installer
    assert "/usr/share/nexa/nexilabs-access/ptb11-sw.js" in installer
    assert "install -D -m 0644" in installer


def test_historical_pab1_cleanup_worker_is_preserved_but_not_operationally_referenced():
    worker = read("infrastructure/deployment/config/nexilabs-private-sw.js")
    private_template = read(
        "infrastructure/deployment/config/"
        "Caddyfile.nexilabs.development-private.ptb11.template"
    )
    public_template = read(
        "infrastructure/deployment/config/Caddyfile.nexilabs.public.ptb11.template"
    )
    assert 'key.startsWith("nexilabs-")' in worker
    assert "self.registration.unregister()" in worker
    assert "private-sw.js" not in private_template
    assert "private-sw.js" not in public_template


def test_ptb11_templates_manifest_and_worker_contain_no_private_credentials_or_allowlist():
    corpus = "\n".join(
        read(path)
        for path in (
            "infrastructure/deployment/manifests/"
            "nexilabs-offline-live-authority-boundary-manifest.json",
            "infrastructure/deployment/config/"
            "Caddyfile.nexilabs.development-private.ptb11.template",
            "infrastructure/deployment/config/Caddyfile.nexilabs.public.ptb11.template",
            "infrastructure/deployment/config/nexilabs-ptb11-sw.js",
            "infrastructure/deployment/scripts/render-nexilabs-ptb11-caddy.sh",
            "infrastructure/deployment/scripts/install-nexilabs-ptb11-worker.sh",
        )
    )
    assert "@gmail.com" not in corpus.lower()
    assert "CLIENT_SECRET" not in corpus
    assert "COOKIE_SECRET" not in corpus
    assert "PGPASSWORD" not in corpus
    assert "development/auth/private" not in corpus


def test_ptb11_renderer_contains_only_expected_placeholders():
    templates = "\n".join(
        [
            read(
                "infrastructure/deployment/config/"
                "Caddyfile.nexilabs.development-private.ptb11.template"
            ),
            read(
                "infrastructure/deployment/config/"
                "Caddyfile.nexilabs.public.ptb11.template"
            ),
        ]
    )
    placeholders = sorted(set(re.findall(r"__NEXILABS_[A-Z_]+__", templates)))
    assert placeholders == sorted(
        [
            "__NEXILABS_PUBLIC_HOSTNAME__",
            "__NEXILABS_PWA_UPSTREAM__",
            "__NEXILABS_INFRASTRUCTURE_API_UPSTREAM__",
            "__NEXILABS_PRODUCTION_AUTH_UPSTREAM__",
        ]
    )
