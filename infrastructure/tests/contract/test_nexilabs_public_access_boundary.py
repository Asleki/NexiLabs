from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[3]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_access_manifest_is_fail_closed_and_replaceable():
    manifest = json.loads(
        read("infrastructure/deployment/manifests/nexilabs-access-boundary-manifest.json")
    )
    assert manifest["milestoneId"] == "NEXILABS.PAB.1"
    assert manifest["defaultMode"] == "DEVELOPMENT_PRIVATE"
    assert manifest["allowedModes"] == ["DEVELOPMENT_PRIVATE", "PUBLIC"]
    assert manifest["denyByDefault"] is True
    assert manifest["publicModeExplicitOnly"] is True
    assert manifest["frontendAllowlistForbidden"] is True
    assert manifest["privateOfflineShellAllowed"] is False
    assert manifest["innerNexiLabsAuthenticationUnchanged"] is True


def test_private_caddy_requires_google_gateway_and_exact_private_worker():
    text = read(
        "infrastructure/deployment/config/"
        "Caddyfile.nexilabs.development-private.template"
    )
    assert "handle /oauth2/*" in text
    assert "reverse_proxy 127.0.0.1:4180" in text
    assert "forward_auth 127.0.0.1:4180" in text
    assert "uri /oauth2/auth" in text
    assert "@unauthorized status 401" in text
    assert "/oauth2/sign_in?rd=" in text
    assert "@private_worker path /sw.js" in text
    assert "/usr/share/nexa/nexilabs-access" in text
    assert 'X-NexiLabs-Access-Mode "DEVELOPMENT_PRIVATE"' in text


def test_public_caddy_removes_only_outer_access_gate():
    text = read(
        "infrastructure/deployment/config/Caddyfile.nexilabs.public.template"
    )
    assert 'X-NexiLabs-Access-Mode "PUBLIC"' in text
    assert "reverse_proxy __NEXILABS_PWA_UPSTREAM__" in text
    assert "forward_auth" not in text
    assert "/oauth2/" not in text
    assert "private-sw.js" not in text


def test_oauth2_proxy_is_loopback_and_uses_server_side_allowlist_only():
    env = read("infrastructure/deployment/config/nexilabs-access.env.example")
    service = read(
        "infrastructure/deployment/config/nexilabs-oauth2-proxy.service"
    )
    assert "OAUTH2_PROXY_PROVIDER=google" in env
    assert "OAUTH2_PROXY_HTTP_ADDRESS=127.0.0.1:4180" in env
    assert (
        "OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE="
        "/etc/nexa/nexilabs-access/allowed-emails"
    ) in env
    assert "OAUTH2_PROXY_EMAIL_DOMAINS=*" not in env
    assert "--email-domain=*" not in service
    assert "EnvironmentFile=/etc/nexa/nexilabs-access.env" in service
    assert "User=nexa-access" in service


def test_repository_templates_do_not_contain_real_allowlist_addresses():
    corpus = "\n".join(
        read(path)
        for path in (
            "infrastructure/deployment/config/nexilabs-access.env.example",
            "infrastructure/deployment/config/nexilabs-oauth2-proxy.service",
            "infrastructure/deployment/config/"
            "Caddyfile.nexilabs.development-private.template",
            "infrastructure/deployment/config/Caddyfile.nexilabs.public.template",
            "infrastructure/deployment/scripts/bootstrap-nexilabs-access.sh",
            "infrastructure/deployment/scripts/activate-nexilabs-access-mode.sh",
        )
    )
    assert "@gmail.com" not in corpus.lower()
    assert "__SET_ON_SERVER_ONLY__" in corpus
    assert "allowed-emails" in corpus


def test_private_worker_clears_nexilabs_caches_and_unregisters_without_fetch():
    worker = read(
        "infrastructure/deployment/config/nexilabs-private-sw.js"
    )
    assert 'addEventListener("install"' in worker
    assert 'addEventListener("activate"' in worker
    assert 'key.startsWith("nexilabs-")' in worker
    assert "self.registration.unregister()" in worker
    assert "client.navigate(client.url)" in worker
    assert 'addEventListener("fetch"' not in worker


def test_mode_renderer_has_no_public_default_and_restricts_upstream():
    script = read(
        "infrastructure/deployment/scripts/render-nexilabs-access-caddy.sh"
    )
    assert "DEVELOPMENT_PRIVATE)" in script
    assert "PUBLIC)" in script
    assert "invalid NEXILABS_ACCESS_MODE" in script
    assert re.search(r'UPSTREAM=.*NEXILABS_PWA_UPSTREAM', script)
    assert "127\\.0\\.0\\.1" in script
    assert "192\\.168" in script


def test_activation_validates_private_material_before_enabling_gateway():
    script = read(
        "infrastructure/deployment/scripts/activate-nexilabs-access-mode.sh"
    )
    assert "[[ -s \"$ALLOWLIST\" ]]" in script
    assert "OAUTH2_PROXY_CLIENT_ID" in script
    assert "OAUTH2_PROXY_CLIENT_SECRET" in script
    assert "OAUTH2_PROXY_COOKIE_SECRET" in script
    assert "systemctl enable --now nexa-nexilabs-oauth2-proxy" in script
    assert "systemctl disable --now nexa-nexilabs-oauth2-proxy" in script
    assert "caddy validate" in script
