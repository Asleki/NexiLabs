"""P006.UI.10.1.R1 — exact account-enrollment main.js successor qualification."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
LOCK = runpy.run_path(str(LOCK_PATH))

EXPECTED = {
    "frontend/src/main.js": "77523c35b98d6c1485850979312dd03bd8a2e32ec74371f380724a4c425bb60f",
}
P006_UI_10_3_MAIN_SHA256 = "f2fdb27c6cb2ee2ec436a6b1e06ee78e0eb64d36c1fafb46635cb473452481dd"

PREDECESSOR_ACCOUNT_PROOFS = (
    "frontend/tests/account/account-enrollment-experience.test.mjs",
    "frontend/tests/account/account-enrollment-security.test.mjs",
)


def test_p006_ui_10_1_r1_successor_scope_is_exactly_main():
    assert LOCK["P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_SUCCESSOR_SHA256"] == EXPECTED
    assert set(EXPECTED) == {"frontend/src/main.js"}
    assert not any(path.startswith("database/") for path in EXPECTED)
    assert not any(path.startswith("infrastructure/") for path in EXPECTED)
    assert not any("roadmap" in path.lower() for path in EXPECTED)


def test_p006_ui_10_1_r1_current_main_matches_the_predate_delivery():
    main = ROOT / "frontend/src/main.js"
    assert main.is_file()
    actual = sha256(main.read_bytes()).hexdigest()
    if actual != EXPECTED["frontend/src/main.js"]:
        assert actual == P006_UI_10_3_MAIN_SHA256
        successor = LOCK["P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_SUCCESSOR_SHA256"]
        assert successor == {"frontend/src/main.js": P006_UI_10_3_MAIN_SHA256}
        authorize = LOCK["_authorized_p006_ui_10_3_layered_admin_composition_successor"]
        assert authorize(ROOT, "frontend/src/main.js")
    source = main.read_text(encoding="utf-8")
    assert "./app/account/account-enrollment-experience.js" in source
    assert "./app/auth/authentication-experience.js" in source
    assert source.index("./app/account/account-enrollment-experience.js") < source.index(
        "./app/auth/authentication-experience.js"
    )


def test_p006_ui_10_1_r1_authorizer_is_exact_path_hash_and_proof_scoped():
    authorize = LOCK["_authorized_p006_ui_10_1_account_enrollment_composition_successor"]
    admin_authorize = LOCK["_authorized_p006_ui_10_3_layered_admin_composition_successor"]
    assert not authorize(ROOT, "frontend/src/main.js")
    assert admin_authorize(ROOT, "frontend/src/main.js")
    assert not authorize(ROOT, "frontend/sw.js")
    assert not authorize(ROOT, "frontend/src/pwa/cache-policy.js")
    assert not authorize(ROOT, "frontend/src/app/application.js")
    assert not authorize(ROOT, "infrastructure/api/app/live_composition.py")
    assert not authorize(ROOT, "database/migrations/migration_manifest.json")
    assert not authorize(ROOT, "roadmap_data.py")


def test_p006_ui_10_1_r1_requires_predate_account_proof_files_without_replacing_them():
    proofs = tuple(LOCK["P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_PROOF_FILES"])
    assert proofs[:2] == PREDECESSOR_ACCOUNT_PROOFS
    assert proofs[-1] == (
        "tests/registries/nngla/"
        "test_p006_ui_10_1_r1_account_enrollment_composition_successor.py"
    )
    assert all((ROOT / relative).is_file() for relative in proofs)


def test_p006_ui_10_1_r1_preserves_historical_hashes_and_separate_ownership():
    historical_cm1 = LOCK["P006_7_11_15_9_CM1_COMPOSITION_SUCCESSOR_SHA256"]
    historical_city = LOCK["P006_7_11_15_7_COMPOSITION_SUCCESSOR_SHA256"]
    assert historical_cm1["frontend/src/main.js"] == (
        "811de1d1ae59778a2f6109a640b748b93ffb5acaeebb9aa199ddf5c604a19483"
    )
    assert historical_city["frontend/src/main.js"] == (
        "809fd354f0f9d55c319aa3eac66fd0869847b27ef570a766d7e04b36e64aead0"
    )

    cm1_authorize = LOCK["_authorized_p006_7_11_15_9_cm1_composition_successor"]
    r2_authorize = LOCK["_authorized_p006_7_11_15_10_r2_pwa_successor"]
    account_authorize = LOCK["_authorized_p006_ui_10_1_account_enrollment_composition_successor"]
    admin_authorize = LOCK["_authorized_p006_ui_10_3_layered_admin_composition_successor"]
    historical_authorize = LOCK["_authorized_p006_7_11_15_7_composition_successor"]

    assert not cm1_authorize(ROOT, "frontend/src/main.js")
    assert not r2_authorize(ROOT, "frontend/src/main.js")
    assert not account_authorize(ROOT, "frontend/src/main.js")
    assert admin_authorize(ROOT, "frontend/src/main.js")
    assert historical_authorize(ROOT, "frontend/src/main.js")
