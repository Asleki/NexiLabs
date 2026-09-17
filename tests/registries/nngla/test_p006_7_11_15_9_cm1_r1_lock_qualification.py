"""P006.7.11.15.9 CM1_R1 — exact lock qualification for the CM1 seam.

This is additive regression proof.  It does not replace the historical
P006.7.11.7.20 lock tests; it verifies the narrow compatibility-successor
contract appended to that existing test module.

P006.7.11.15.10 R2 compatibility maintenance preserves the historical CM1
constants while allowing the current service-worker path to advance only to
the exact reviewed R2 PWA successor.  The CM1 authorizer itself remains exact
and does not absorb the later R2 bytes.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
LOCK = runpy.run_path(str(LOCK_PATH))

EXPECTED_CM1 = {
    "frontend/src/main.js": "811de1d1ae59778a2f6109a640b748b93ffb5acaeebb9aa199ddf5c604a19483",
    "frontend/sw.js": "65994c75cb10f5e048311d34d010633ff2b29e77adb7451d66161f4dc6fed6a9",
    "infrastructure/api/app/live_composition.py": "10c805ba28aafd04105dc2deecb124c03ce4911d0155ceac8be2f247ab8db052",
}

EXPECTED_R2_PWA_SUCCESSORS = {
    "frontend/sw.js": "e3271948407449bde5d4da9124d339b7bc61196b82fdcc26fb5b447dd6f30091",
}

# P006.7.11.15.10.1 compatibility maintenance: preserve the CM1 and R2
# evidence above while recognizing only the exact later reviewed SW successor.
EXPECTED_15_10_1_PWA_SUCCESSORS = {
    "frontend/sw.js": "92afa24059fdfd3a20dda67e78c99cf114d3e3d015463d4d7839bdf63a14277d",
}

# P006.7.11.15.10.1.3 compatibility maintenance: append one further exact
# service-worker successor without broadening the CM1-specific authorizer.
EXPECTED_15_10_1_3_PWA_SUCCESSORS = {
    "frontend/sw.js": "1db4bdcac4ac719762f3e29e8647de2b6efe6eede3393f8573e36562ce28897c",
}

# P006.UI.10.1.R1 compatibility maintenance: preserve historical CM1
# main.js evidence while recognizing only the exact reviewed later account
# enrollment composition successor.
EXPECTED_P006_UI_10_1_MAIN_SUCCESSORS = {
    "frontend/src/main.js": "77523c35b98d6c1485850979312dd03bd8a2e32ec74371f380724a4c425bb60f",
}

EXPECTED_P006_UI_10_3_MAIN_SUCCESSORS = {
    "frontend/src/main.js": "f2fdb27c6cb2ee2ec436a6b1e06ee78e0eb64d36c1fafb46635cb473452481dd",
}


# P006.UI.10.1.R2 compatibility maintenance: append the exact installed-PWA
# activation successor for the shared service-worker path without broadening CM1.
EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS = {
    "frontend/sw.js": "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d",
}


def _digest(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), relative
    return sha256(path.read_bytes()).hexdigest()


def _assert_current_cm1_or_reviewed_successor(relative: str, expected_cm1: str) -> None:
    actual = _digest(relative)
    if actual == expected_cm1:
        return

    expected_account = EXPECTED_P006_UI_10_1_MAIN_SUCCESSORS.get(relative)
    if expected_account is not None and actual == expected_account:
        successor_hashes = LOCK[
            "P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_SUCCESSOR_SHA256"
        ]
        assert successor_hashes.get(relative) == expected_account
        successor_authorize = LOCK[
            "_authorized_p006_ui_10_1_account_enrollment_composition_successor"
        ]
        assert successor_authorize(ROOT, relative)
        return

    expected_admin = EXPECTED_P006_UI_10_3_MAIN_SUCCESSORS.get(relative)
    if expected_admin is not None and actual == expected_admin:
        successor_hashes = LOCK[
            "P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_SUCCESSOR_SHA256"
        ]
        assert successor_hashes.get(relative) == expected_admin
        successor_authorize = LOCK[
            "_authorized_p006_ui_10_3_layered_admin_composition_successor"
        ]
        assert successor_authorize(ROOT, relative)
        return

    expected_account_activation = EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS.get(relative)
    if expected_account_activation is not None and actual == expected_account_activation:
        successor_hashes = LOCK[
            "P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_SUCCESSOR_SHA256"
        ]
        assert successor_hashes.get(relative) == expected_account_activation
        successor_authorize = LOCK[
            "_authorized_p006_ui_10_1_r2_installed_pwa_activation_successor"
        ]
        assert successor_authorize(ROOT, relative)
        return

    expected_15_10_1_3 = EXPECTED_15_10_1_3_PWA_SUCCESSORS.get(relative)
    if expected_15_10_1_3 is not None and actual == expected_15_10_1_3:
        successor_hashes = LOCK[
            "P006_7_11_15_10_1_3_UNIFIED_ENVIRONMENTAL_PRODUCTION_SHA256"
        ]
        assert successor_hashes.get(relative) == expected_15_10_1_3
        successor_authorize = LOCK[
            "_authorized_p006_7_11_15_10_1_3_unified_environmental_successor"
        ]
        assert successor_authorize(ROOT, relative)
        return

    expected_15_10_1 = EXPECTED_15_10_1_PWA_SUCCESSORS.get(relative)
    if expected_15_10_1 is not None and actual == expected_15_10_1:
        successor_hashes = LOCK[
            "P006_7_11_15_10_1_STYLING_ARCHITECTURE_SUCCESSOR_SHA256"
        ]
        assert successor_hashes.get(relative) == expected_15_10_1
        successor_authorize = LOCK[
            "_authorized_p006_7_11_15_10_1_styling_architecture_successor"
        ]
        assert successor_authorize(ROOT, relative)
        return

    expected_r2 = EXPECTED_R2_PWA_SUCCESSORS.get(relative)
    assert expected_r2 is not None, (
        f"{relative} advanced beyond CM1 without an explicitly reviewed successor"
    )
    assert actual == expected_r2

    r2_hashes = LOCK["P006_7_11_15_10_R2_PWA_SUCCESSOR_SHA256"]
    assert r2_hashes.get(relative) == expected_r2
    r2_authorize = LOCK["_authorized_p006_7_11_15_10_r2_pwa_successor"]
    assert r2_authorize(ROOT, relative)


def test_cm1_r1_successor_hashes_match_the_already_delivered_cm1_bytes():
    # The historical CM1 contract remains immutable even when a later reviewed
    # successor is the current working-tree byte sequence.
    assert LOCK["P006_7_11_15_9_CM1_COMPOSITION_SUCCESSOR_SHA256"] == EXPECTED_CM1
    for relative, expected in EXPECTED_CM1.items():
        _assert_current_cm1_or_reviewed_successor(relative, expected)


def test_cm1_r1_requires_the_predecessor_cm1_proof_files():
    proofs = tuple(LOCK["P006_7_11_15_9_CM1_PROOF_FILES"])
    assert proofs == (
        "tests/infrastructure/api/test_p006_7_11_15_9_compat_map_extension_seam.py",
        "tests/infrastructure/api/test_p006_7_11_15_9_compat_live_composition_source.py",
        "frontend/tests/app/features/p006_7_11_15_9_compat_map-extension-loader.test.mjs",
        "frontend/tests/app/features/p006_7_11_15_9_compat_main-source.test.mjs",
        "frontend/tests/pwa/p006_7_11_15_9_compat_extension-seam-refresh.test.mjs",
    )
    assert all((ROOT / relative).is_file() for relative in proofs)


def test_cm1_r1_authorization_is_exact_path_and_does_not_expand_the_lock():
    cm1_authorize = LOCK["_authorized_p006_7_11_15_9_cm1_composition_successor"]
    historical_authorize = LOCK["_authorized_p006_7_11_15_7_composition_successor"]
    r2_authorize = LOCK["_authorized_p006_7_11_15_10_r2_pwa_successor"]
    account_authorize = LOCK["_authorized_p006_ui_10_1_account_enrollment_composition_successor"]
    admin_authorize = LOCK["_authorized_p006_ui_10_3_layered_admin_composition_successor"]
    account_activation_authorize = LOCK["_authorized_p006_ui_10_1_r2_installed_pwa_activation_successor"]

    for relative, expected_cm1 in EXPECTED_CM1.items():
        actual = _digest(relative)
        if actual == expected_cm1:
            assert cm1_authorize(ROOT, relative)
        else:
            expected_account = EXPECTED_P006_UI_10_1_MAIN_SUCCESSORS.get(relative)
            if expected_account is not None and actual == expected_account:
                assert not cm1_authorize(ROOT, relative)
                assert not r2_authorize(ROOT, relative)
                assert account_authorize(ROOT, relative)
                assert historical_authorize(ROOT, relative)
                continue

            expected_admin = EXPECTED_P006_UI_10_3_MAIN_SUCCESSORS.get(relative)
            if expected_admin is not None and actual == expected_admin:
                assert not cm1_authorize(ROOT, relative)
                assert not r2_authorize(ROOT, relative)
                assert not account_authorize(ROOT, relative)
                assert admin_authorize(ROOT, relative)
                assert historical_authorize(ROOT, relative)
                continue

            expected_account_activation = EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS.get(relative)
            if expected_account_activation is not None and actual == expected_account_activation:
                assert not cm1_authorize(ROOT, relative)
                assert r2_authorize(ROOT, relative)
                assert account_activation_authorize(ROOT, relative)
                assert historical_authorize(ROOT, relative)
                continue

            expected_15_10_1_3 = EXPECTED_15_10_1_3_PWA_SUCCESSORS.get(relative)
            if expected_15_10_1_3 is not None and actual == expected_15_10_1_3:
                assert not cm1_authorize(ROOT, relative)
                successor_authorize = LOCK[
                    "_authorized_p006_7_11_15_10_1_3_unified_environmental_successor"
                ]
                assert successor_authorize(ROOT, relative)
                assert r2_authorize(ROOT, relative)
                assert historical_authorize(ROOT, relative)
                continue

            expected_15_10_1 = EXPECTED_15_10_1_PWA_SUCCESSORS.get(relative)
            if expected_15_10_1 is not None and actual == expected_15_10_1:
                assert not cm1_authorize(ROOT, relative)
                successor_authorize = LOCK[
                    "_authorized_p006_7_11_15_10_1_styling_architecture_successor"
                ]
                assert successor_authorize(ROOT, relative)
                assert r2_authorize(ROOT, relative)
                assert historical_authorize(ROOT, relative)
                continue

            # A later R2 successor must not broaden the CM1-specific authorizer.
            assert relative in EXPECTED_R2_PWA_SUCCESSORS
            assert actual == EXPECTED_R2_PWA_SUCCESSORS[relative]
            assert not cm1_authorize(ROOT, relative)
            assert r2_authorize(ROOT, relative)

        # The historical composition seam may recognize either its exact CM1
        # byte sequence or the exact later reviewed successor chain.
        assert historical_authorize(ROOT, relative)

    assert not cm1_authorize(ROOT, "frontend/src/pwa/cache-policy.js")
    assert not cm1_authorize(ROOT, "frontend/src/app/application.js")
    assert not cm1_authorize(ROOT, "roadmap_data.py")

    assert not r2_authorize(ROOT, "frontend/src/main.js")
    assert not r2_authorize(ROOT, "infrastructure/api/app/live_composition.py")
    assert not r2_authorize(ROOT, "roadmap_data.py")

    assert not account_authorize(ROOT, "frontend/src/main.js")
    assert admin_authorize(ROOT, "frontend/src/main.js")
    assert not account_authorize(ROOT, "frontend/sw.js")
    assert not account_authorize(ROOT, "frontend/src/pwa/cache-policy.js")
    assert not account_authorize(ROOT, "roadmap_data.py")
    assert not admin_authorize(ROOT, "frontend/sw.js")
    assert not admin_authorize(ROOT, "frontend/src/pwa/cache-policy.js")
    assert not admin_authorize(ROOT, "roadmap_data.py")


    assert account_activation_authorize(ROOT, "frontend/sw.js")
    assert account_activation_authorize(ROOT, "frontend/src/pwa/cache-policy.js")
    assert not account_activation_authorize(ROOT, "frontend/src/main.js")
    assert not account_activation_authorize(ROOT, "roadmap_data.py")


def test_cm1_r1_preserves_the_historical_15_7_scope_and_cache_policy_lock():
    historical = LOCK["P006_7_11_15_7_COMPOSITION_SUCCESSOR_SHA256"]
    assert set(historical) == {
        "frontend/src/main.js",
        "frontend/src/pwa/cache-policy.js",
        "frontend/sw.js",
        "infrastructure/api/app/live_composition.py",
    }
    assert historical["frontend/src/pwa/cache-policy.js"] == (
        "59354982093f52ab11a1c76c55bdc987350b3d25d81e5ccf8ee3649bf66d373b"
    )


def test_cm1_r1_preserves_exact_sw_successor_chain_through_p006_ui_10_1_r2():
    assert EXPECTED_CM1["frontend/sw.js"] == (
        "65994c75cb10f5e048311d34d010633ff2b29e77adb7451d66161f4dc6fed6a9"
    )
    assert EXPECTED_R2_PWA_SUCCESSORS["frontend/sw.js"] == (
        "e3271948407449bde5d4da9124d339b7bc61196b82fdcc26fb5b447dd6f30091"
    )
    assert EXPECTED_15_10_1_PWA_SUCCESSORS["frontend/sw.js"] == (
        "92afa24059fdfd3a20dda67e78c99cf114d3e3d015463d4d7839bdf63a14277d"
    )
    assert EXPECTED_15_10_1_3_PWA_SUCCESSORS["frontend/sw.js"] == (
        "1db4bdcac4ac719762f3e29e8647de2b6efe6eede3393f8573e36562ce28897c"
    )
    assert EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS["frontend/sw.js"] == (
        "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d"
    )
    assert _digest("frontend/sw.js") == EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS["frontend/sw.js"]
    cm1_authorize = LOCK["_authorized_p006_7_11_15_9_cm1_composition_successor"]
    historical_authorize = LOCK["_authorized_p006_7_11_15_7_composition_successor"]
    r2_authorize = LOCK["_authorized_p006_7_11_15_10_r2_pwa_successor"]
    environmental_authorize = LOCK["_authorized_p006_7_11_15_10_1_3_unified_environmental_successor"]
    activation_authorize = LOCK["_authorized_p006_ui_10_1_r2_installed_pwa_activation_successor"]
    assert not cm1_authorize(ROOT, "frontend/sw.js")
    assert historical_authorize(ROOT, "frontend/sw.js")
    assert r2_authorize(ROOT, "frontend/sw.js")
    assert not environmental_authorize(ROOT, "frontend/sw.js")
    assert activation_authorize(ROOT, "frontend/sw.js")
    assert not activation_authorize(ROOT, "frontend/src/main.js")
    assert not activation_authorize(ROOT, "infrastructure/api/app/live_composition.py")
    assert not activation_authorize(ROOT, "roadmap_data.py")
