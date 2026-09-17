"""P006.UI.10.1.R2 — installed-PWA account-enrollment activation successor qualification.

Verified-defect maintenance only. The .10.1 account presentation and .10.1.R1
main.js composition remain predecessors; R2 advances only the locked v17 PWA
worker/cache-policy pair required to activate those already-delivered bytes in
an existing installed client.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
LOCK = runpy.run_path(str(LOCK_PATH))

EXPECTED_PRODUCTION = {
    "frontend/sw.js": "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d",
    "frontend/src/pwa/cache-policy.js": "2df032f691d551937fb9e0a34ff15b291c218abe14ed69ad99a7a36425e231e2",
}
EXPECTED_R1_MAIN = {
    "frontend/src/main.js": "77523c35b98d6c1485850979312dd03bd8a2e32ec74371f380724a4c425bb60f",
}
EXPECTED_FRONTEND_PROOF = {
    "frontend/tests/pwa/p006_ui_10_1_r2_account-enrollment-activation-refresh.test.mjs":
        "7ec373c0b9d92152872ed625d44bd7f1cca651223d25b3d4c5a072f80946b63f",
}
ACCOUNT_SHELL_ASSETS = (
    "./styles/account-enrollment-v1.css",
    "./src/app/account/account-enrollment-route.js",
    "./src/app/account/account-enrollment-experience.js",
    "./src/ui/pages/account-enrollment-gateway.js",
    "./src/ui/pages/guest-account-enrollment.js",
    "./src/ui/pages/developer-account-enrollment.js",
)


def _digest(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), relative
    return sha256(path.read_bytes()).hexdigest()


def test_p006_ui_10_1_r2_scope_is_exact_pwa_activation_and_roadmap_free():
    assert LOCK["P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_SUCCESSOR_SHA256"] == EXPECTED_PRODUCTION
    assert set(EXPECTED_PRODUCTION) == {"frontend/sw.js", "frontend/src/pwa/cache-policy.js"}
    assert "frontend/src/main.js" not in EXPECTED_PRODUCTION
    assert not any(path.startswith(("backend/", "infrastructure/", "database/")) for path in EXPECTED_PRODUCTION)
    assert not any("roadmap" in path.lower() for path in EXPECTED_PRODUCTION)


def test_p006_ui_10_1_r2_current_pwa_bytes_and_authorization_are_exact():
    authorize = LOCK["_authorized_p006_ui_10_1_r2_installed_pwa_activation_successor"]
    for relative, expected in EXPECTED_PRODUCTION.items():
        assert _digest(relative) == expected
        assert authorize(ROOT, relative)
    assert not authorize(ROOT, "frontend/src/main.js")
    assert not authorize(ROOT, "frontend/src/app/account/account-enrollment-experience.js")
    assert not authorize(ROOT, "infrastructure/api/app/live_composition.py")
    assert not authorize(ROOT, "database/migrations/migration_manifest.json")
    assert not authorize(ROOT, "roadmap_data.py")


def test_p006_ui_10_1_r2_preserves_r1_main_composition_exactly():
    assert LOCK["P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_SUCCESSOR_SHA256"] == EXPECTED_R1_MAIN
    authorize_r1 = LOCK["_authorized_p006_ui_10_1_account_enrollment_composition_successor"]
    current = _digest("frontend/src/main.js")
    if current == EXPECTED_R1_MAIN["frontend/src/main.js"]:
        assert authorize_r1(ROOT, "frontend/src/main.js")
    else:
        expected = LOCK["P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_SUCCESSOR_SHA256"]
        assert current == expected["frontend/src/main.js"]
        assert not authorize_r1(ROOT, "frontend/src/main.js")
        authorize_admin = LOCK["_authorized_p006_ui_10_3_layered_admin_composition_successor"]
        assert authorize_admin(ROOT, "frontend/src/main.js")


def test_p006_ui_10_1_r2_frontend_activation_proof_is_exact_and_present():
    proofs = tuple(LOCK["P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_PROOF_FILES"])
    assert proofs == (
        "frontend/tests/pwa/p006_ui_10_1_r2_account-enrollment-activation-refresh.test.mjs",
        "tests/registries/nngla/test_p006_ui_10_1_r2_installed_pwa_account_enrollment_activation_successor.py",
    )
    assert all((ROOT / relative).is_file() for relative in proofs)
    for relative, expected in EXPECTED_FRONTEND_PROOF.items():
        assert _digest(relative) == expected


def test_p006_ui_10_1_r2_preserves_v17_and_closes_account_shell_graph():
    worker = (ROOT / "frontend/sw.js").read_text(encoding="utf-8")
    policy = (ROOT / "frontend/src/pwa/cache-policy.js").read_text(encoding="utf-8")
    assert 'CACHE_NAME = "nexilabs-shell-v17"' in worker
    assert 'PWA_CACHE_VERSION = "nexilabs-shell-v17"' in policy
    assert "nexilabs-refresh-p006-7-11-15-10-1-3" in worker
    assert "nexilabs-refresh-p006-ui-10-1-r2" in worker
    assert "ACCOUNT_ENROLLMENT_ACTIVATION_SAME_GENERATION_REFRESH_MARKER" in worker
    assert "client.navigate(client.url)" in worker
    assert '"./src/main.js"' in worker and '"./src/main.js"' in policy
    for asset in ACCOUNT_SHELL_ASSETS:
        token = f'"{asset}"'
        assert token in worker, asset
        assert token in policy, asset


def test_p006_ui_10_1_r2_does_not_publish_private_authentication_fixtures():
    combined = (
        (ROOT / "frontend/sw.js").read_text(encoding="utf-8")
        + "\n"
        + (ROOT / "frontend/src/pwa/cache-policy.js").read_text(encoding="utf-8")
    )
    for forbidden in (
        "development/auth/private",
        "guests.local.json",
        "developers.local.json",
        "enigma_words_3.csv",
        "enigma_words_4.csv",
        "enigma_words_5.csv",
    ):
        assert forbidden not in combined


def test_p006_ui_10_1_r2_preserves_historical_pwa_hash_evidence():
    environmental = LOCK["P006_7_11_15_10_1_3_UNIFIED_ENVIRONMENTAL_PRODUCTION_SHA256"]
    assert environmental["frontend/sw.js"] == (
        "1db4bdcac4ac719762f3e29e8647de2b6efe6eede3393f8573e36562ce28897c"
    )
    assert environmental["frontend/src/pwa/cache-policy.js"] == (
        "baa55cbe2c227615084f9666568710d9c25259ec8feb673cf28fe4d990807d20"
    )
