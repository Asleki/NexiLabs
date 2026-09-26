"""P006.7.11.15.10.1.3 — unified environmental composition and label-coupling lock qualification.

Additive maintenance proof. Historical .15.10/.15.10.1/.15.10.1.2 evidence is
preserved; no roadmap, backend, authority, publication or database contract is
introduced here.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy
import re

ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
LOCK = runpy.run_path(str(LOCK_PATH))

EXPECTED_PRODUCTION = {
    "frontend/src/map/cartography/unified-environmental-compositor.js": "b30be53cf63849a5737481166aadac66ce77674f332bad28e8da8b7ec78fad8e",
    "frontend/src/map/cartography/unified-frame-plan.js": "100dc0c386c0dce17c8f11c370cc81a37366b610f1a878913ea5855305238b81",
    "frontend/src/map/cartography/unified-frame-renderer.js": "66be2a1bdd48c52a4d41c805284cde485132c7e884f68db20e88a568f029bbd9",
    "frontend/src/map/cartography/presentation-coordinator.js": "25e412f4b6e4e659b8a5d7565b324fabb89cadee2271c6978f1d1e1a74910e15",
    "frontend/src/pwa/cache-policy.js": "baa55cbe2c227615084f9666568710d9c25259ec8feb673cf28fe4d990807d20",
    "frontend/sw.js": "1db4bdcac4ac719762f3e29e8647de2b6efe6eede3393f8573e36562ce28897c",
}

EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS = {
    "frontend/src/pwa/cache-policy.js": "2df032f691d551937fb9e0a34ff15b291c218abe14ed69ad99a7a36425e231e2",
    "frontend/sw.js": "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d",
}

EXPECTED_FRONTEND_TESTS = {
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-frame-plan.test.mjs": "05be097b0896a39e766e9a0fb691200891a8a797172164882a35301afd9f78ab",
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-frame-renderer.test.mjs": "7da061caee65a5a209581201dffe3fe4aabd722ec16f912626cfd083a9a5dc36",
    "frontend/tests/map/cartography/p006_7_11_15_10_presentation-coordinator.test.mjs": "70aac0b53eab19451ce3caf89cb64fefe7858ff11964890881b59b4f7bb32ff4",
    "frontend/tests/map/cartography/p006_7_11_15_10_1_3_unified-environmental-compositor.test.mjs": "f367ac70afc0c4bc4c383e4338d0177a83bc6b315be898609227716f052ebdff",
    "frontend/tests/pwa/p006_7_11_15_10_1_3_environmental-composition-refresh.test.mjs": "79d5827758448058fb72a3c82c86d51ba0a177381b7fcca53eb968f8aca3b4ca",
}

EXPECTED_15_10_1_2_R1_GOVERNANCE_QUALIFICATION_SHA256 = (
    "400d5127657a58c1d9716d2593119a267e24f7c1fdaffcd281c6179c08ad7a02"
)

EXPECTED_P006_UI_10_1_R2_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 = (
    "b363d3faebb4631ad0f785d0b8c2aed2167429892f0c9381c396bd29abf6a03b"
)

EXPECTED_P006_UI_10_3_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 = (
    "8d6e7e5361d120568d993219fe4c5320976f62e819f10c3394ef5a2655b5a0f0"
)

# NEXILABS.RI.2 compatibility maintenance: preserve the committed
# P006.UI.10.3 request-governance hash above as historical evidence while
# recognizing the exact reviewed RI.2 qualification successor.
EXPECTED_NEXILABS_RI_2_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 = (
    "9980eebec89303c4a5845e7311a6824b4a7b18a653d0fb0bf14ea77aacfd59a8"
)

# P006.UI.10.4 compatibility maintenance: preserve every earlier
# request-governance qualification hash above while recognizing the exact
# reviewed P006.UI.10.4 successor.
EXPECTED_P006_UI_10_4_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 = (
    "c05359f5d5243c1b5d5f7c1b78004652f9acaae0c92bf84099e46db59a0ff9fc"
)


EXPECTED_15_10_1_HISTORICAL_TEST_SUCCESSORS = {
    "frontend/tests/integration/p006_7_11_15_10_map-first-css-contract.test.mjs":
        "b757a4a5994cb9d0630a15534338b0d07a4816115ba5f59c07213975cde16278",
    "frontend/tests/map/cartography/p006_7_11_15_10_presentation-coordinator.test.mjs":
        "f316272fec007d6d284d2b8bb4a451887de0222564e58c14edfdb172797eb99d",
}


def test_15_10_1_3_exact_scope_is_frontend_pwa_only_and_roadmap_free():
    assert LOCK["P006_7_11_15_10_1_3_UNIFIED_ENVIRONMENTAL_PRODUCTION_SHA256"] == EXPECTED_PRODUCTION
    assert LOCK["P006_7_11_15_10_1_3_FRONTEND_TEST_SHA256"] == EXPECTED_FRONTEND_TESTS
    combined = set(EXPECTED_PRODUCTION) | set(EXPECTED_FRONTEND_TESTS)
    assert not any("roadmap" in path.lower() for path in combined)
    assert not any(path.startswith(("backend/", "infrastructure/", "database/")) for path in combined)
    assert "frontend/src/main.js" not in combined
    assert "frontend/src/app/shell/nexilabs-shell.js" not in combined
    assert "frontend/src/map/cartography/semantic-zoom-v2.js" not in combined
    assert not any(path.startswith("frontend/src/map/state/") for path in combined)
    assert not any(path.startswith("frontend/src/map/environment/") for path in combined)


def test_15_10_1_3_production_and_frontend_test_hashes_are_exactly_authorized():
    authorize_production = LOCK["_authorized_p006_7_11_15_10_1_3_unified_environmental_successor"]
    authorize_test = LOCK["_authorized_p006_7_11_15_10_1_3_frontend_test_successor"]
    authorize_ui_r2 = LOCK["_authorized_p006_ui_10_1_r2_installed_pwa_activation_successor"]
    for relative, expected in EXPECTED_PRODUCTION.items():
        path = ROOT / relative
        assert path.is_file(), relative
        current_expected = EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS.get(relative, expected)
        assert sha256(path.read_bytes()).hexdigest() == current_expected
        if relative in EXPECTED_P006_UI_10_1_R2_PWA_SUCCESSORS:
            assert not authorize_production(ROOT, relative)
            assert authorize_ui_r2(ROOT, relative)
        else:
            assert authorize_production(ROOT, relative)
    for relative, expected in EXPECTED_FRONTEND_TESTS.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert sha256(path.read_bytes()).hexdigest() == expected
        assert authorize_test(ROOT, relative)
    assert not authorize_production(ROOT, "roadmap_data.py")
    assert not authorize_production(ROOT, "infrastructure/api/routers/nngla_map.py")
    assert not authorize_test(ROOT, "roadmap_data.py")
    assert not authorize_ui_r2(ROOT, "roadmap_data.py")


def test_unified_environmental_compositor_reuses_locked_environment_authority_modules():
    text = (ROOT / "frontend/src/map/cartography/unified-environmental-compositor.js").read_text(encoding="utf-8")
    required = (
        'from "../terrain/catalog.js"',
        'from "../terrain/contracts.js"',
        'from "../landforms/catalog.js"',
        'from "../landforms/contracts.js"',
        'from "../vegetation/catalog.js"',
        'from "../vegetation/contracts.js"',
        'from "../hydrology/catalog.js"',
        'from "../hydrology/contracts.js"',
        'from "../climate/catalog.js"',
        'from "../climate/contracts.js"',
        'projectionMode: "UNIFIED"',
    )
    assert all(token in text for token in required)
    assert "fetch(" not in text
    assert "localStorage" not in text
    assert "riverName" not in text
    assert "lakeName" not in text
    assert "rainfallSystemName" not in text


def test_settlement_pair_coupling_is_present_without_changing_admin_symbol_policy():
    plan = (ROOT / "frontend/src/map/cartography/unified-frame-plan.js").read_text(encoding="utf-8")
    renderer = (ROOT / "frontend/src/map/cartography/unified-frame-renderer.js").read_text(encoding="utf-8")
    semantic = (ROOT / "frontend/src/map/cartography/semantic-zoom-v2.js").read_text(encoding="utf-8")
    assert "acceptedSymbols" in plan
    assert "settlement_label_rejected" in plan
    assert "settlement_label_unavailable" in plan
    assert "collision.acceptedSymbols" in renderer
    assert "settlementSymbolRejectedSubjectIds" in renderer
    assert "presentationTargets" in plan
    assert "interactionKind" in plan
    assert "settlementCapable" in plan
    assert "presentationTargetReceipts" in renderer
    assert "labelRendered" in renderer
    assert "symbolRendered" in renderer
    assert re.search(r"\[UnifiedLayerKey\.MUNICIPALITY\].*?symbolMin:\s*Infinity", semantic, re.S)
    assert re.search(r"\[UnifiedLayerKey\.CITY_DISTRICT\].*?symbolMin:\s*Infinity", semantic, re.S)


def test_existing_environment_controls_and_coordinates_reference_are_coupled_without_view_state_rewrite():
    coordinator = (ROOT / "frontend/src/map/cartography/presentation-coordinator.js").read_text(encoding="utf-8")
    for key in ("physicalLand", "biosphere", "hydrologyAtmosphere", "coordinates"):
        assert key in (ROOT / "frontend/src/map/cartography/unified-environmental-compositor.js").read_text(encoding="utf-8")
    assert "environmentalLayerVisibility" in coordinator
    assert "UnifiedEnvironmentalLayerKey.COORDINATES" in coordinator
    assert "UnifiedLayerKey.REFERENCE" in coordinator
    assert "frontend/src/map/state/" not in "\n".join(EXPECTED_PRODUCTION)




def test_future_selection_readiness_preserves_identity_without_adding_interaction_handlers():
    plan = (ROOT / "frontend/src/map/cartography/unified-frame-plan.js").read_text(encoding="utf-8")
    renderer = (ROOT / "frontend/src/map/cartography/unified-frame-renderer.js").read_text(encoding="utf-8")
    combined = plan + "\n" + renderer
    assert "presentationTargets" in plan
    assert "interactionKind" in plan
    assert "SETTLEMENT" in plan
    assert "ADMINISTRATIVE_LABEL" in plan
    assert "labelRendered" in renderer
    assert "symbolRendered" in renderer
    assert "addEventListener(\"click\"" not in combined
    assert "addEventListener(\"dblclick\"" not in combined
    assert "doubleclick" not in combined.lower()


def test_unified_coordinates_preserve_locked_predecessor_visual_constants():
    compositor = (ROOT / "frontend/src/map/cartography/unified-environmental-compositor.js").read_text(encoding="utf-8")
    assert 'const GRID_STROKE = "rgba(203, 213, 225, 0.24)"' in compositor
    assert 'const EQUATOR_STROKE = "#19d3e6"' in compositor
    assert "context.lineWidth = 1" in compositor
    assert "context.setLineDash([7, 5])" in compositor
    assert "context.lineWidth = 2" in compositor

def test_pwa_cache_abi_stays_v17_with_dedicated_same_generation_handoff():
    worker = (ROOT / "frontend/sw.js").read_text(encoding="utf-8")
    policy = (ROOT / "frontend/src/pwa/cache-policy.js").read_text(encoding="utf-8")
    asset = "./src/map/cartography/unified-environmental-compositor.js"
    assert 'CACHE_NAME = "nexilabs-shell-v17"' in worker
    assert 'PWA_CACHE_VERSION = "nexilabs-shell-v17"' in policy
    assert asset in worker and asset in policy
    assert "nexilabs-refresh-p006-7-11-15-10-1-3" in worker
    assert "UNIFIED_ENVIRONMENTAL_COMPOSITION_SAME_GENERATION_REFRESH_MARKER" in worker
    assert "nexilabs-refresh-p006-ui-10-1-r2" in worker
    assert "ACCOUNT_ENROLLMENT_ACTIVATION_SAME_GENERATION_REFRESH_MARKER" in worker
    assert "client.navigate(client.url)" in worker


def test_historical_successor_evidence_remains_present_and_distinct():
    assert LOCK["P006_7_11_15_10_PRESENTATION_SUCCESSOR_SHA256"]
    assert LOCK["P006_7_11_15_10_R2_PWA_SUCCESSOR_SHA256"]
    assert LOCK["P006_7_11_15_10_1_STYLING_ARCHITECTURE_SUCCESSOR_SHA256"]
    assert LOCK["P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_SUCCESSOR_SHA256"]
    assert LOCK["P006_7_11_15_10_1_TEST_SUCCESSOR_SHA256"] == EXPECTED_15_10_1_HISTORICAL_TEST_SUCCESSORS
    assert set(EXPECTED_PRODUCTION).isdisjoint(LOCK["P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_SUCCESSOR_SHA256"])

    predecessor_qualification = (
        ROOT / "tests/registries/nngla/test_p006_7_11_15_10_1_2_request_scoped_materialization_lock_qualification.py"
    )
    assert predecessor_qualification.is_file()
    assert EXPECTED_15_10_1_2_R1_GOVERNANCE_QUALIFICATION_SHA256 == (
        "400d5127657a58c1d9716d2593119a267e24f7c1fdaffcd281c6179c08ad7a02"
    )
    assert EXPECTED_P006_UI_10_1_R2_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 == (
        "b363d3faebb4631ad0f785d0b8c2aed2167429892f0c9381c396bd29abf6a03b"
    )
    assert EXPECTED_P006_UI_10_3_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 == (
        "8d6e7e5361d120568d993219fe4c5320976f62e819f10c3394ef5a2655b5a0f0"
    )
    assert EXPECTED_NEXILABS_RI_2_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 == (
        "9980eebec89303c4a5845e7311a6824b4a7b18a653d0fb0bf14ea77aacfd59a8"
    )
    assert EXPECTED_P006_UI_10_4_REQUEST_GOVERNANCE_QUALIFICATION_SHA256 == (
        "c05359f5d5243c1b5d5f7c1b78004652f9acaae0c92bf84099e46db59a0ff9fc"
    )
    assert sha256(predecessor_qualification.read_bytes()).hexdigest() == (
        EXPECTED_P006_UI_10_4_REQUEST_GOVERNANCE_QUALIFICATION_SHA256
    )
    predecessor_text = predecessor_qualification.read_text(encoding="utf-8")
    assert "EXPECTED_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "EXPECTED_15_10_1_3_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "EXPECTED_P006_UI_10_1_R1_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "EXPECTED_P006_UI_10_1_R2_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "EXPECTED_P006_UI_10_3_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "EXPECTED_NEXILABS_RI_2_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "EXPECTED_P006_UI_10_4_GOVERNANCE_SUCCESSORS" in predecessor_text
    assert "ccc7a1ea66eb7884eee3895a0bd5a93155ad26104f410c63481d2480817aed6b" in predecessor_text
    assert "76aeaa901f96fd87328615b61022fae293e1f7d8487e643294d84d1c44c4e1d4" in predecessor_text


def test_historical_operational_lock_no_reformatting_markers_are_still_verbatim():
    text = LOCK_PATH.read_text(encoding="utf-8")
    assert 'current["extensions"][:len(prior["extensions"])] == prior["extensions"]' in text
    assert 'if status == "??":' in text
    assert "Locked production or roadmap surfaces changed during later additive work." in text
