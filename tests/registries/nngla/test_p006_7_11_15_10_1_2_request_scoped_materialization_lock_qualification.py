"""P006.7.11.15.10.1.2 — request-scoped read materialization qualification.

Additive proof only. Predecessor tests and predecessor hash evidence remain in
place and are not replaced by this qualification.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
LOCK = runpy.run_path(str(LOCK_PATH))

EXPECTED_EXISTING_PRODUCTION_SUCCESSORS = {
    "infrastructure/database/runtime/pool.py":
        "65aca27bed69fc12483265df826ebea8a9dd43e2d3d2e6ec32606ac9b28b9a33",
    "infrastructure/database/read/nngla_region_public_map.py":
        "9cbd1bb6247b764da26eb2bbce5c051b0f920324d1fd70a975dd9e0bb67b58da",
    "infrastructure/database/read/nngla_city_public_map.py":
        "e654110f5796d6d79d3b07cd14369233d272ca5b513468610cd338dafc19ca4b",
    "infrastructure/database/read/nngla_municipality_public_map.py":
        "380e76f6545b0a3ecc6e5957615f96bc714e3788d44395da9df3f75af4989d25",
    "infrastructure/database/read/nngla_city_district_public_map.py":
        "2ad72a7f8558aadb30de87187bc39a1c5b1ea1bc6d1f5d3e970f3cca5f4c73c4",
    "infrastructure/database/read/nngla_town_public_map.py":
        "50667edaa50382742e5daf266d474b46853f914bf0427dd4575b95490f54e098",
}
EXPECTED_NEW_PRODUCTION = {
    "infrastructure/database/runtime/read_materialization.py":
        "004c81f47a7489d534a1982983ada9b338713b74b1c34d481f282c7478618d36",
}
EXPECTED_GOVERNANCE_SUCCESSORS = {
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py":
        "ccc7a1ea66eb7884eee3895a0bd5a93155ad26104f410c63481d2480817aed6b",
    "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py":
        "76aeaa901f96fd87328615b61022fae293e1f7d8487e643294d84d1c44c4e1d4",
}
EXPECTED_15_10_1_3_GOVERNANCE_SUCCESSORS = {
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py":
        "118a8ab783653c83b21d87f0d2f9a1d553f21fd3cbf2d9353abeaad2ef417225",
    "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py":
        "9e1092e6e90a0063cdb9e89479c38012a5cf6dc6c363858cb9ac34248b1e5022",
}

# P006.UI.10.1.R1 compatibility maintenance: the account-enrollment milestone
# legitimately advances only the centralized operational governance lock. Keep
# both earlier governance generations above as historical evidence; this map is
# intentionally one-path-only and does not absorb the unchanged styling lock.
EXPECTED_P006_UI_10_1_R1_GOVERNANCE_SUCCESSORS = {
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py":
        "7fb0d77971d014918379a1d95ae52eaec93c7025ae1af74d73da967bb95fc34c",
}

# P006.UI.10.1.R2 compatibility maintenance: the installed-PWA activation
# correction legitimately advances the centralized lock and the styling
# qualification that historically tracks the current PWA successor chain.
EXPECTED_P006_UI_10_1_R2_GOVERNANCE_SUCCESSORS = {
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py":
        "77e2706e92d454f9cf2203e7e62275a46e5f1dcce100b825efd17056b9eab8fb",
    "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py":
        "70f744e609c4012d4070fdfbdddd22f5a6bf4494ec063a1a42b528a53d39bf8d",
}

# P006.UI.10.3 compatibility maintenance: layered Admin authentication
# legitimately advances only the centralized operational governance lock.
# Earlier governance generations remain immutable evidence above.
EXPECTED_P006_UI_10_3_GOVERNANCE_SUCCESSORS = {
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py":
        "3ec98aedf6580f69f6b31924765c1f1c49e636b7cd71f52b908a2ff4ec473cde",
}
HISTORICAL_15_10_1_POOL_SHA256 = (
    "b478ca0808871c9bc4572f119d1f75ef83edaa241668653b77a2eb33fd72879b"
)


def test_request_materialization_successor_scope_is_exact_and_roadmap_free():
    actual = LOCK["P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_SUCCESSOR_SHA256"]
    assert actual == EXPECTED_EXISTING_PRODUCTION_SUCCESSORS
    assert set(EXPECTED_NEW_PRODUCTION) == {
        "infrastructure/database/runtime/read_materialization.py"
    }
    all_paths = set(actual) | set(EXPECTED_NEW_PRODUCTION)
    assert not any("roadmap" in path.lower() for path in all_paths)
    assert not any(path.startswith("database/migrations/") for path in all_paths)
    assert not any(path.startswith("frontend/") for path in all_paths)
    assert "infrastructure/api/routers/nngla_map.py" not in all_paths
    assert "infrastructure/api/app/live_composition.py" not in all_paths


def test_existing_production_successor_hashes_and_authorization_are_exact():
    authorize = LOCK[
        "_authorized_p006_7_11_15_10_1_2_request_materialization_successor"
    ]
    for relative, expected in EXPECTED_EXISTING_PRODUCTION_SUCCESSORS.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert sha256(path.read_bytes()).hexdigest() == expected
        assert authorize(ROOT, relative)

    assert not authorize(ROOT, "infrastructure/api/routers/nngla_map.py")
    assert not authorize(ROOT, "frontend/sw.js")
    assert not authorize(ROOT, "roadmap_data.py")


def test_new_request_materialization_module_is_exact_ephemeral_and_non_authoritative():
    for relative, expected in EXPECTED_NEW_PRODUCTION.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert sha256(path.read_bytes()).hexdigest() == expected
        text = path.read_text(encoding="utf-8")
        assert "RequestReadMaterialization" in text
        assert "complete_mapping" in text
        assert "current_request_read_materialization" in text
        assert "PostgreSQL" in text
        assert "unavailable outside an active" in text
        assert "persist" not in text.lower().replace("non-persistent", "")


def test_predecessor_pool_hash_and_no_reformatting_source_markers_remain_present():
    assert (
        LOCK["P006_7_11_15_10_1_STYLING_ARCHITECTURE_SUCCESSOR_SHA256"]
        ["infrastructure/database/runtime/pool.py"]
        == HISTORICAL_15_10_1_POOL_SHA256
    )
    text = LOCK_PATH.read_text(encoding="utf-8")
    assert 'current["extensions"][:len(prior["extensions"])] == prior["extensions"]' in text
    assert 'if status == "??":' in text
    assert "P006_7_11_15_10_1_TEST_SUCCESSOR_SHA256" in text



def test_governance_successors_are_exact_and_preserve_predecessor_evidence():
    assert set(EXPECTED_15_10_1_3_GOVERNANCE_SUCCESSORS) == set(
        EXPECTED_GOVERNANCE_SUCCESSORS
    )
    assert set(EXPECTED_P006_UI_10_1_R1_GOVERNANCE_SUCCESSORS) == {
        "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
    }
    assert set(EXPECTED_P006_UI_10_1_R2_GOVERNANCE_SUCCESSORS) == set(EXPECTED_GOVERNANCE_SUCCESSORS)
    assert set(EXPECTED_P006_UI_10_3_GOVERNANCE_SUCCESSORS) == {
        "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py"
    }
    for relative, expected in EXPECTED_GOVERNANCE_SUCCESSORS.items():
        path = ROOT / relative
        assert path.is_file(), relative
        actual = sha256(path.read_bytes()).hexdigest()
        if actual == expected:
            continue
        if actual == EXPECTED_15_10_1_3_GOVERNANCE_SUCCESSORS[relative]:
            continue
        r1_expected = EXPECTED_P006_UI_10_1_R1_GOVERNANCE_SUCCESSORS.get(relative)
        if r1_expected is not None and actual == r1_expected:
            continue
        ui_10_3_expected = EXPECTED_P006_UI_10_3_GOVERNANCE_SUCCESSORS.get(relative)
        if ui_10_3_expected is not None and actual == ui_10_3_expected:
            continue
        r2_expected = EXPECTED_P006_UI_10_1_R2_GOVERNANCE_SUCCESSORS.get(relative)
        assert r2_expected is not None, (
            f"{relative} advanced beyond the reviewed P006.UI.10.1.R1 governance successor "
            "without an explicit P006.UI.10.1.R2 or P006.UI.10.3 successor"
        )
        assert actual == r2_expected
    styling_text = (
        ROOT / "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py"
    ).read_text(encoding="utf-8")
    assert HISTORICAL_15_10_1_POOL_SHA256 in styling_text
    assert "EXPECTED_15_10_1_2_SUCCESSORS" in styling_text


def test_public_authority_queries_and_validation_contracts_remain_in_place():
    expected_markers = {
        "infrastructure/database/read/nngla_region_public_map.py": (
            "geography.nngla_region_public_read_v1",
            "qualification_status='QUALIFIED'",
            "publication_status='PUBLISHED'",
        ),
        "infrastructure/database/read/nngla_city_public_map.py": (
            "geography.nngla_city_public_read_v1",
            "qualification_status='QUALIFIED'",
            "publication_status='PUBLISHED'",
        ),
        "infrastructure/database/read/nngla_municipality_public_map.py": (
            "geography.nngla_municipality_public_read_v2",
            "governed MUNICIPALITY identity set must contain exactly 24 unique IDs",
            "publication_status='PUBLISHED'",
        ),
        "infrastructure/database/read/nngla_city_district_public_map.py": (
            "geography.nngla_city_district_public_read_v2",
            "parent.administrative_type_code='CITY'",
            "publication_status='PUBLISHED'",
        ),
        "infrastructure/database/read/nngla_town_public_map.py": (
            "geography.nngla_town_public_read_v2",
            "upper(place_type_code)='TOWN'",
            "publication_status='PUBLISHED'",
        ),
    }
    for relative, markers in expected_markers.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text, (relative, marker)
