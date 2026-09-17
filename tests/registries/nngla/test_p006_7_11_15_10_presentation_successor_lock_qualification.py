"""P006.7.11.15.10 — exact lock qualification for map-first presentation successors."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
LOCK = runpy.run_path(str(LOCK_PATH))

EXPECTED = {
    "frontend/src/app/shell/nexilabs-shell.js": "ecc624b5538c77053c1b21d9a9e4d16745b8a5689b8accef957d32ea8dddb577",
    "frontend/src/app/features/novegeo-cartographic-styling-experience.js": "4254255aec4a57f70fb4f8fb7c20c24d1dbb2b65a714664f8dadd3c5cdd7f3ca",
    "frontend/src/app/features/novegeo-region-map-experience.js": "7910557641478ede66d553848facf662d14b693dc33838db2835cc4a6e04b7ef",
    "frontend/src/app/features/novegeo-city-map-experience.js": "78c5b6f7cce0a96d587615230ea0b8cbd9057ad2b842be49200636cb6017b112",
    "frontend/src/app/features/novegeo-municipality-map-experience.js": "e665c475fe35d789857a4d5015caa07d14da1218ebd9334d4fd606123f677744",
    "frontend/src/app/features/novegeo-city-district-map-experience.js": "bc214c662187069bf29cfdc2bab4809f51f378130512dd3a9b066ed7d763fa0a",
    "frontend/src/app/features/novegeo-town-map-experience.js": "6537600e26e2abd6e3dae0c845891ba9fa7192845e0ecce45df8c1c9d77bb737",
}

CM1_MAIN_SHA256 = "811de1d1ae59778a2f6109a640b748b93ffb5acaeebb9aa199ddf5c604a19483"
P006_UI_10_1_MAIN_SHA256 = "77523c35b98d6c1485850979312dd03bd8a2e32ec74371f380724a4c425bb60f"
P006_UI_10_3_MAIN_SHA256 = "f2fdb27c6cb2ee2ec436a6b1e06ee78e0eb64d36c1fafb46635cb473452481dd"


def test_p006_7_11_15_10_successor_scope_is_exact_and_does_not_rewrite_main():
    assert LOCK["P006_7_11_15_10_PRESENTATION_SUCCESSOR_SHA256"] == EXPECTED
    assert "frontend/src/main.js" not in EXPECTED
    assert "frontend/src/app/features/novegeo-live-authority-runtime.js" not in EXPECTED
    assert "frontend/src/app/features/novegeo-feature-runtime.js" not in EXPECTED
    assert "frontend/src/app/features/novegeo-map-extension-loader.js" not in EXPECTED
    assert not any(path.startswith("database/") for path in EXPECTED)
    assert not any(path.startswith("infrastructure/") for path in EXPECTED)
    assert not any("roadmap" in path.lower() for path in EXPECTED)
    # P006.7.11.15.10 still did not own main.js. A later reviewed account
    # composition successor may now be the current working-tree byte sequence.
    actual_main = sha256((ROOT / "frontend/src/main.js").read_bytes()).hexdigest()
    if actual_main != CM1_MAIN_SHA256:
        if actual_main == P006_UI_10_1_MAIN_SHA256:
            successor_hashes = LOCK["P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_SUCCESSOR_SHA256"]
            assert successor_hashes == {"frontend/src/main.js": P006_UI_10_1_MAIN_SHA256}
            successor_authorize = LOCK["_authorized_p006_ui_10_1_account_enrollment_composition_successor"]
            assert successor_authorize(ROOT, "frontend/src/main.js")
        else:
            assert actual_main == P006_UI_10_3_MAIN_SHA256
            successor_hashes = LOCK["P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_SUCCESSOR_SHA256"]
            assert successor_hashes == {"frontend/src/main.js": P006_UI_10_3_MAIN_SHA256}
            successor_authorize = LOCK["_authorized_p006_ui_10_3_layered_admin_composition_successor"]
            assert successor_authorize(ROOT, "frontend/src/main.js")


def test_p006_7_11_15_10_successor_hashes_and_authorization_are_exact():
    authorize = LOCK["_authorized_p006_7_11_15_10_presentation_successor"]
    for relative, expected in EXPECTED.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert sha256(path.read_bytes()).hexdigest() == expected
        assert authorize(ROOT, relative)

    assert not authorize(ROOT, "frontend/src/main.js")
    assert not authorize(ROOT, "frontend/src/app/application.js")
    assert not authorize(ROOT, "roadmap_data.py")


def test_p006_7_11_15_10_proof_files_are_additive_and_present():
    proofs = tuple(LOCK["P006_7_11_15_10_PRESENTATION_PROOF_FILES"])
    assert proofs
    assert all((ROOT / relative).is_file() for relative in proofs)
    assert all(
        relative.startswith("frontend/tests/") or relative.startswith("tests/")
        for relative in proofs
    )
