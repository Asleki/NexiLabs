"""P006.7.11.7.20 — NNGLA operational backend lock qualification.

These are additive qualification tests. They deliberately do not replace or edit
any earlier Bundle 17A-17O test. Bundle 17P introduces no production feature.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import ast
import json
import subprocess

BUNDLE_17N_CONTRACTS = (
    "novegeo_runtime_command_catalogue_v001.csv",
    "novegeo_runtime_command_authorization_matrix_v001.csv",
    "novegeo_runtime_bulk_operation_policy_v001.csv",
    "novegeo_runtime_idempotency_policy_v001.csv",
    "novegeo_runtime_command_validation_rules_v001.csv",
)
BUNDLE_17O_CONTRACTS = (
    "novegeo_spatial_query_catalogue_v001.csv",
    "novegeo_spatial_query_result_contracts_v001.csv",
    "novegeo_read_model_definition_catalogue_v001.csv",
    "novegeo_geocoding_normalization_rules_v001.csv",
    "novegeo_cross_registry_spatial_reference_contracts_v001.csv",
)
DAY_ZERO_REGISTERS = (
    "address_reference_candidates.csv",
    "parcel_bootstrap.csv",
    "title_bootstrap.csv",
    "state_land_bootstrap.csv",
    "survey_control_point_candidates.csv",
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "roadmap_data.py").is_file() and (candidate / "tests").is_dir():
            return candidate
        if (candidate / "registries" / "nngla").is_dir() and (candidate / "data" / "novegeo" / "nngla").is_dir():
            return candidate
    return Path.cwd().resolve()


def _find_data_file(root: Path, filename: str) -> list[Path]:
    base = root / "data" / "novegeo" / "nngla"
    if not base.is_dir():
        return []
    return sorted(path for path in base.rglob(filename) if path.is_file())


def _corpus(root: Path) -> str:
    suffixes = {".py", ".sql", ".json", ".csv", ".md", ".txt"}
    chunks: list[str] = []
    for base in (root / "registries" / "nngla", root / "services", root / "backend", root / "database"):
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            try:
                data = path.read_bytes()[:2_000_000]
            except OSError:
                continue
            chunks.append(data.decode("utf-8", errors="ignore").lower())
    return "\n".join(chunks)


def _head_text(root: Path, path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return proc.stdout if proc.returncode == 0 else None


def _only_python_function_changed(prior: str, current: str, function_name: str) -> bool:
    if prior == current:
        return True
    try:
        prior_tree = ast.parse(prior)
        current_tree = ast.parse(current)
    except SyntaxError:
        return False
    prior_node = next((node for node in prior_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name), None)
    current_node = next((node for node in current_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name), None)
    if prior_node is None or current_node is None or prior_node.end_lineno is None or current_node.end_lineno is None:
        return False
    prior_lines = prior.splitlines(keepends=True)
    current_lines = current.splitlines(keepends=True)
    reconstructed = prior_lines[:prior_node.lineno - 1] + current_lines[current_node.lineno - 1:current_node.end_lineno] + prior_lines[prior_node.end_lineno:]
    return "".join(reconstructed) == current


def _authorized_d3_lysora_maintenance(root: Path) -> bool:
    path = "registries/nngla/spatial_realization/face_polygonization.py"
    prior = _head_text(root, path)
    if prior is None:
        return False
    current = (root / path).read_text(encoding="utf-8")
    if not _only_python_function_changed(prior, current, "_adjacency"):
        return False
    if prior == current:
        return True
    return all(token in current for token in (
        "polygon_parts = _polygon_parts(component)",
        "inspection_boundary = unary_union(boundaries)",
        "if inspection_boundary is None or inspection_boundary.is_empty",
        "intersection = inspection_boundary.intersection(sibling_boundary)",
    ))


P006_7_11_15_7_COMPOSITION_SUCCESSOR_SHA256 = {
    "frontend/src/main.js": "809fd354f0f9d55c319aa3eac66fd0869847b27ef570a766d7e04b36e64aead0",
    "frontend/src/pwa/cache-policy.js": "59354982093f52ab11a1c76c55bdc987350b3d25d81e5ccf8ee3649bf66d373b",
    "frontend/sw.js": "bd7341d5e81cda12ab5ff4721193dbde6555185036074f5063d5ca50ccee11d7",
    "infrastructure/api/app/live_composition.py": "ab06157237b5bb6eb16684e8b7d52f73a154bf061b0c248ac238f61f3e4c460b",
}
P006_7_11_15_9_CM1_COMPOSITION_SUCCESSOR_SHA256 = {
    "frontend/src/main.js": "811de1d1ae59778a2f6109a640b748b93ffb5acaeebb9aa199ddf5c604a19483",
    "frontend/sw.js": "65994c75cb10f5e048311d34d010633ff2b29e77adb7451d66161f4dc6fed6a9",
    "infrastructure/api/app/live_composition.py": "10c805ba28aafd04105dc2deecb124c03ce4911d0155ceac8be2f247ab8db052",
}
P006_7_11_15_9_CM1_PROOF_FILES = (
    "tests/infrastructure/api/test_p006_7_11_15_9_compat_map_extension_seam.py",
    "tests/infrastructure/api/test_p006_7_11_15_9_compat_live_composition_source.py",
    "frontend/tests/app/features/p006_7_11_15_9_compat_map-extension-loader.test.mjs",
    "frontend/tests/app/features/p006_7_11_15_9_compat_main-source.test.mjs",
    "frontend/tests/pwa/p006_7_11_15_9_compat_extension-seam-refresh.test.mjs",
)


def _authorized_p006_7_11_15_9_cm1_composition_successor(root: Path, target_path: str) -> bool:
    expected = P006_7_11_15_9_CM1_COMPOSITION_SUCCESSOR_SHA256.get(target_path)
    if expected is None or not all((root / proof).is_file() for proof in P006_7_11_15_9_CM1_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


def _authorized_p006_7_11_15_7_composition_successor(root: Path, target_path: str) -> bool:
    expected = P006_7_11_15_7_COMPOSITION_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    proof = root / "tests/infrastructure/api/test_p006_7_11_15_7_city_composition.py"
    if not proof.is_file():
        return False
    candidate = root / target_path
    if not candidate.is_file():
        return False
    digest = sha256(candidate.read_bytes()).hexdigest()
    if digest == expected:
        return True
    if _authorized_p006_7_11_15_9_cm1_composition_successor(root, target_path):
        return True
    if _authorized_p006_ui_10_1_account_enrollment_composition_successor(root, target_path):
        return True
    if _authorized_p006_ui_10_3_layered_admin_composition_successor(root, target_path):
        return True
    return _authorized_p006_7_11_15_10_r2_pwa_successor(root, target_path)


def _authorized_delivery3_existing_path(root: Path, target_path: str) -> bool:
    if target_path == "registries/nngla/spatial_realization/face_polygonization.py":
        return _authorized_d3_lysora_maintenance(root)
    return False


P006_7_11_15_9_1_MAP_EXTENSION_SUCCESSORS = {
    "frontend/public/geography/novegeo/map-extensions/manifest.json": {"extensionId": "nngla-map-extension:municipality:v1", "order": 100, "module": "./src/app/features/novegeo-municipality-map-experience.js"},
    "infrastructure/api/app/nngla_map_extensions/extension_manifest.json": {"extensionId": "nngla-map-extension:municipality:v1", "order": 100, "module": "infrastructure.api.app.nngla_map_extensions.layers.municipality_spatial_publication"},
}


def _authorized_p006_7_11_15_9_1_manifest_successor(
    root: Path,
    target_path: str,
) -> bool:
    """Authorize only the exact additive MUNICIPALITY manifest successors."""
    expected = P006_7_11_15_9_1_MAP_EXTENSION_SUCCESSORS.get(target_path)
    if expected is None:
        return False

    prior_text = _head_text(root, target_path)
    candidate = root / target_path
    if prior_text is None or not candidate.is_file():
        return False

    try:
        prior = json.loads(prior_text)
        current = json.loads(candidate.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return False

    if prior.get("manifestVersion") != current.get("manifestVersion"):
        return False

    if set(prior) != {"manifestVersion", "extensions"}:
        return False

    if set(current) != {"manifestVersion", "extensions"}:
        return False

    if not isinstance(prior.get("extensions"), list):
        return False

    if not isinstance(current.get("extensions"), list):
        return False

    prefix_preserved = (
        current["extensions"][:len(prior["extensions"])] == prior["extensions"]
    )
    if not prefix_preserved:
        return False

    appended = current["extensions"][len(prior["extensions"]):]
    return appended == [expected]


P006_7_11_15_9_2_3_MAP_EXTENSION_SUCCESSOR_TAILS = {
    "frontend/public/geography/novegeo/map-extensions/manifest.json": (
        {"extensionId": "nngla-map-extension:city-district:v1", "order": 200, "module": "./src/app/features/novegeo-city-district-map-experience.js"},
        {"extensionId": "nngla-map-extension:town:v1", "order": 300, "module": "./src/app/features/novegeo-town-map-experience.js"},
    ),
    "infrastructure/api/app/nngla_map_extensions/extension_manifest.json": (
        {"extensionId": "nngla-map-extension:city-district:v1", "order": 200, "module": "infrastructure.api.app.nngla_map_extensions.layers.city_district_spatial_publication"},
        {"extensionId": "nngla-map-extension:town:v1", "order": 300, "module": "infrastructure.api.app.nngla_map_extensions.layers.town_settlement_footprint_publication"},
    ),
}


def _authorized_p006_7_11_15_9_2_3_manifest_successor(root: Path, target_path: str) -> bool:
    expected_tail = P006_7_11_15_9_2_3_MAP_EXTENSION_SUCCESSOR_TAILS.get(target_path)
    if expected_tail is None:
        return False
    prior_text = _head_text(root, target_path)
    candidate = root / target_path
    if prior_text is None or not candidate.is_file():
        return False
    try:
        prior = json.loads(prior_text)
        current = json.loads(candidate.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return False
    if set(prior) != {"manifestVersion", "extensions"} or set(current) != {"manifestVersion", "extensions"}:
        return False
    if prior.get("manifestVersion") != current.get("manifestVersion"):
        return False
    prior_extensions = prior.get("extensions")
    current_extensions = current.get("extensions")
    if not isinstance(prior_extensions, list) or not isinstance(current_extensions, list):
        return False
    if current_extensions[:len(prior_extensions)] != prior_extensions:
        return False
    return current_extensions[len(prior_extensions):] == list(expected_tail)


def test_17p_runs_against_canonical_nngla_repository_surfaces():
    root = _repo_root()
    required = (root / "registries" / "nngla", root / "database" / "migrations", root / "data" / "novegeo" / "nngla", root / "tests")
    missing = [str(path.relative_to(root)) for path in required if not path.is_dir()]
    assert not missing, f"Missing NNGLA repository surfaces: {missing}"


def test_bundle_17n_runtime_contracts_are_present_without_reimplementation():
    root = _repo_root()
    missing = [name for name in BUNDLE_17N_CONTRACTS if not _find_data_file(root, name)]
    assert not missing, f"Bundle 17N required runtime contracts not found: {missing}"


def test_bundle_17o_read_contracts_are_present_without_reimplementation():
    root = _repo_root()
    missing = [name for name in BUNDLE_17O_CONTRACTS if not _find_data_file(root, name)]
    assert not missing, f"Bundle 17O required spatial query/read-model contracts not found: {missing}"


def test_historical_day_zero_registers_remain_present():
    root = _repo_root()
    missing = [name for name in DAY_ZERO_REGISTERS if not _find_data_file(root, name)]
    assert not missing, f"Immutable Day-Zero register evidence is missing: {missing}"


def test_runtime_command_governance_evidence_is_still_reachable():
    corpus = _corpus(_repo_root())
    required_groups = {
        "runtime command": ("runtime_command", "command_catalogue", "command_service"),
        "authorization": ("authorization", "authorisation", "authorized", "authorised"),
        "bulk operation": ("bulk_operation", "bulk operation", "bulk_command"),
        "idempotency": ("idempotency", "idempotent", "idempotency_key"),
        "receipt": ("receipt", "execution_receipt", "command_receipt"),
    }
    missing = [label for label, tokens in required_groups.items() if not any(token in corpus for token in tokens)]
    assert not missing, f"Runtime command/governance evidence groups not reachable: {missing}"


def test_spatial_query_and_cross_registry_read_evidence_is_still_reachable():
    corpus = _corpus(_repo_root())
    required_groups = {
        "containment": ("containment", "contains", "within"),
        "adjacency": ("adjacency", "adjacent"),
        "intersection": ("intersection", "intersects", "crosses"),
        "nearest": ("nearest", "distance"),
        "geocoding": ("geocod", "reverse_geocod"),
        "read model": ("read_model", "read model"),
    }
    missing = [label for label, tokens in required_groups.items() if not any(token in corpus for token in tokens)]
    assert not missing, f"Spatial query/read evidence groups not reachable: {missing}"


P006_7_11_15_9_SEQ29_PRODUCTION_SUCCESSOR_SHA256 = {
    "infrastructure/api/app/nngla_map_extensions/layers/city_district_spatial_publication.py": "69aa07fae916b0cf1c5b725df62b11c2cd0f49e046f6ab3cee6172ab76570a82",
    "infrastructure/api/app/nngla_map_extensions/layers/town_settlement_footprint_publication.py": "8254e9549b423504c2f1815f0d740e405ed0acd197853d4bfa26e760d93ca466",
    "infrastructure/api/services/nngla_city_district_map_read_service.py": "ee96cc832843cb4622b4210f4dd35d8f395c86b6c67b2798c0ed62893be8edba",
    "infrastructure/api/services/nngla_town_map_read_service.py": "cfb414ba0fd93589724306106a8aa1f954c826bc2862b5e3c44a94a8da06d2e6",
    "infrastructure/database/read/nngla_city_district_public_map.py": "4003cc847a624c510b83d9310fb5bc335019a9b4a75f108b032a6a29ef42e0a2",
    "infrastructure/database/read/nngla_municipality_public_map.py": "e86b4958d171f012dcbfc2906d696c3d0980899c00c701d4a01debdbf6120ac2",
    "infrastructure/database/read/nngla_town_public_map.py": "88668fa6f027a928bc4f3a03780702b63725fe5e9b1114bf0af0366cb3bf78cf",
}


def _authorized_p006_7_11_15_9_seq29_production_successor(root: Path, target_path: str) -> bool:
    expected = P006_7_11_15_9_SEQ29_PRODUCTION_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    proof_paths = (
        "database/migrations/m006_07_11_nngla_feature_level_spatial_publication_correction.sql",
        "tests/contract/database/test_p006_7_11_15_9_seq29_feature_level_publication_correction.py",
        "tests/infrastructure/api/test_p006_7_11_15_9_seq29_dependency_correction.py",
        "tests/infrastructure/database/test_p006_7_11_15_9_seq29_public_read_adapters.py",
        "tests/registries/nngla/test_p006_7_11_15_9_seq29_incremental_publication_source.py",
    )
    if not all((root / rel).is_file() for rel in proof_paths):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


P006_7_11_15_10_PRESENTATION_SUCCESSOR_SHA256 = {
    "frontend/src/app/shell/nexilabs-shell.js": "ecc624b5538c77053c1b21d9a9e4d16745b8a5689b8accef957d32ea8dddb577",
    "frontend/src/app/features/novegeo-cartographic-styling-experience.js": "4254255aec4a57f70fb4f8fb7c20c24d1dbb2b65a714664f8dadd3c5cdd7f3ca",
    "frontend/src/app/features/novegeo-region-map-experience.js": "7910557641478ede66d553848facf662d14b693dc33838db2835cc4a6e04b7ef",
    "frontend/src/app/features/novegeo-city-map-experience.js": "78c5b6f7cce0a96d587615230ea0b8cbd9057ad2b842be49200636cb6017b112",
    "frontend/src/app/features/novegeo-municipality-map-experience.js": "e665c475fe35d789857a4d5015caa07d14da1218ebd9334d4fd606123f677744",
    "frontend/src/app/features/novegeo-city-district-map-experience.js": "bc214c662187069bf29cfdc2bab4809f51f378130512dd3a9b066ed7d763fa0a",
    "frontend/src/app/features/novegeo-town-map-experience.js": "6537600e26e2abd6e3dae0c845891ba9fa7192845e0ecce45df8c1c9d77bb737",
}
P006_7_11_15_10_PRESENTATION_PROOF_FILES = (
    "frontend/tests/map/cartography/p006_7_11_15_10_semantic-zoom-v2.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-projection.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_geodesic-scale-v2.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-frame-plan.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-frame-renderer.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_presentation-coordinator.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_capital-role-safety.test.mjs",
    "frontend/tests/app/features/p006_7_11_15_10_layer-provider-seam.test.mjs",
    "frontend/tests/integration/p006_7_11_15_10_bootstrap-order.test.mjs",
    "frontend/tests/integration/p006_7_11_15_10_map-first-css-contract.test.mjs",
    "tests/registries/nngla/test_p006_7_11_15_10_presentation_successor_lock_qualification.py",
)


def _authorized_p006_7_11_15_10_presentation_successor(root: Path, target_path: str) -> bool:
    expected = P006_7_11_15_10_PRESENTATION_SUCCESSOR_SHA256.get(target_path)
    if expected is None or not all((root / proof).is_file() for proof in P006_7_11_15_10_PRESENTATION_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


P006_7_11_15_10_R2_PWA_SUCCESSOR_SHA256 = {
    "frontend/sw.js": "e3271948407449bde5d4da9124d339b7bc61196b82fdcc26fb5b447dd6f30091",
    "frontend/src/pwa/cache-policy.js": "d8f1fcaf98733b95c4c19f3d069a54b79598665dd7cfdb213985d3e35d4263a4",
}
P006_7_11_15_10_R2_PWA_PROOF_FILES = (
    "frontend/tests/pwa/p006_7_11_15_10_r2_map-first-shell-refresh.test.mjs",
    "tests/registries/nngla/test_p006_7_11_15_10_r2_pwa_successor_lock_qualification.py",
)


def _authorized_p006_7_11_15_10_r2_pwa_successor_historical(root: Path, target_path: str) -> bool:
    expected = P006_7_11_15_10_R2_PWA_SUCCESSOR_SHA256.get(target_path)
    if expected is None or not all((root / proof).is_file() for proof in P006_7_11_15_10_R2_PWA_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected

# P006.7.11.15.10.1 — exact verified-defect styling/read-orchestration successor.
P006_7_11_15_10_1_STYLING_ARCHITECTURE_SUCCESSOR_SHA256 = {
    "frontend/src/map/nngla/governed-snapshot-loader.js": "4f2042e3d0f64319bd85460189d11e5aa7295c17a74431631f6313843c48528e",
    "frontend/src/map/geography/live-boundary-client.js": "4c87ca950cb2779553152b9caca964ad5db558da53c263b3b174514e27a120df",
    "frontend/src/map/nngla/national-map-client.js": "10b6854bea743538251313a67c6ed26544bff314fcade015fb0436ada6b7d5c9",
    "frontend/src/map/cartography/presentation-coordinator.js": "319406e8613cc64c7b20b63e802695f9275b95535a653614d16a3c0a5e5b80e4",
    "frontend/styles/novegeo-map-first-v1.css": "4b6f24968c9ce832ef8dfa996d5b27b0636f5d865e53efba21baf1aa045e8690",
    "frontend/src/pwa/cache-policy.js": "06826644a273905bae2259757e20100ddc59f3294eb9f51b1d4e7a246b9a1eea",
    "frontend/sw.js": "92afa24059fdfd3a20dda67e78c99cf114d3e3d015463d4d7839bdf63a14277d",
    "infrastructure/database/runtime/pool.py": "b478ca0808871c9bc4572f119d1f75ef83edaa241668653b77a2eb33fd72879b",
    "infrastructure/api/routers/nngla_map.py": "ad74d774d41f9bddc302524a501d9e5edf55dc6f8533695ffba4b630784a4865",
}
P006_7_11_15_10_1_POST_ACCEPTANCE_REMOVALS = (
    "frontend/P006_15_10_RUNTIME_DIAG.html",
)

P006_7_11_15_10_1_STYLING_ARCHITECTURE_PROOF_FILES = (
    "frontend/tests/map/nngla/p006_7_11_15_10_1_governed_snapshot_loader.test.mjs",
    "frontend/tests/map/cartography/p006_7_11_15_10_presentation-coordinator.test.mjs",
    "frontend/tests/integration/p006_7_11_15_10_map-first-css-contract.test.mjs",
    "frontend/tests/pwa/p006_7_11_15_10_1_styling_architecture_refresh.test.mjs",
    "tests/infrastructure/database/test_p006_7_11_15_10_1_request_scoped_read_session.py",
    "tests/infrastructure/api/test_p006_7_11_15_10_1_map_router_read_session.py",
    "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py",
)


def _authorized_p006_7_11_15_10_1_styling_architecture_successor(root: Path, target_path: str) -> bool:
    expected = P006_7_11_15_10_1_STYLING_ARCHITECTURE_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_7_11_15_10_1_STYLING_ARCHITECTURE_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


# P006.7.11.15.10.1.1 — exact maintenance authorization for the two
# historical frontend tests that .15.10.1 had to update because their prior
# assertions encoded the verified activation defect. This is deliberately
# separate from production-successor authorization and is not a broad
# frontend/tests exemption.
P006_7_11_15_10_1_TEST_SUCCESSOR_SHA256 = {
    "frontend/tests/integration/p006_7_11_15_10_map-first-css-contract.test.mjs": "b757a4a5994cb9d0630a15534338b0d07a4816115ba5f59c07213975cde16278",
    "frontend/tests/map/cartography/p006_7_11_15_10_presentation-coordinator.test.mjs": "f316272fec007d6d284d2b8bb4a451887de0222564e58c14edfdb172797eb99d",
}


def _authorized_p006_7_11_15_10_1_test_successor(root: Path, target_path: str) -> bool:
    """Authorize only the exact reviewed .15.10.1 historical-test successors."""
    expected = P006_7_11_15_10_1_TEST_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_7_11_15_10_1_STYLING_ARCHITECTURE_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


# P006.7.11.15.10.1.2 — exact verified query-amplification maintenance successor.
P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_SUCCESSOR_SHA256 = {
    "infrastructure/database/runtime/pool.py": "65aca27bed69fc12483265df826ebea8a9dd43e2d3d2e6ec32606ac9b28b9a33",
    "infrastructure/database/read/nngla_region_public_map.py": "9cbd1bb6247b764da26eb2bbce5c051b0f920324d1fd70a975dd9e0bb67b58da",
    "infrastructure/database/read/nngla_city_public_map.py": "e654110f5796d6d79d3b07cd14369233d272ca5b513468610cd338dafc19ca4b",
    "infrastructure/database/read/nngla_municipality_public_map.py": "380e76f6545b0a3ecc6e5957615f96bc714e3788d44395da9df3f75af4989d25",
    "infrastructure/database/read/nngla_city_district_public_map.py": "2ad72a7f8558aadb30de87187bc39a1c5b1ea1bc6d1f5d3e970f3cca5f4c73c4",
    "infrastructure/database/read/nngla_town_public_map.py": "50667edaa50382742e5daf266d474b46853f914bf0427dd4575b95490f54e098",
}
P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_PROOF_FILES = (
    "infrastructure/database/runtime/read_materialization.py",
    "tests/infrastructure/database/test_p006_7_11_15_10_1_2_request_read_materialization.py",
    "tests/infrastructure/database/test_p006_7_11_15_10_1_2_public_map_materialization.py",
    "tests/infrastructure/api/test_p006_7_11_15_10_1_2_map_query_amplification.py",
    "tests/registries/nngla/test_p006_7_11_15_10_1_2_request_scoped_materialization_lock_qualification.py",
)


def _authorized_p006_7_11_15_10_1_2_request_materialization_successor(root: Path, target_path: str) -> bool:
    """Authorize only exact existing production successors for .15.10.1.2."""
    expected = P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_7_11_15_10_1_2_REQUEST_MATERIALIZATION_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


# P006.7.11.15.10.1.3 — exact verified frontend/PWA environmental-composition
# and settlement-label coupling maintenance successors. Historical predecessor
# hashes above remain unchanged; this is a separate narrow authorization seam.
P006_7_11_15_10_1_3_UNIFIED_ENVIRONMENTAL_PRODUCTION_SHA256 = {
    "frontend/src/map/cartography/unified-environmental-compositor.js": "b30be53cf63849a5737481166aadac66ce77674f332bad28e8da8b7ec78fad8e",
    "frontend/src/map/cartography/unified-frame-plan.js": "100dc0c386c0dce17c8f11c370cc81a37366b610f1a878913ea5855305238b81",
    "frontend/src/map/cartography/unified-frame-renderer.js": "66be2a1bdd48c52a4d41c805284cde485132c7e884f68db20e88a568f029bbd9",
    "frontend/src/map/cartography/presentation-coordinator.js": "25e412f4b6e4e659b8a5d7565b324fabb89cadee2271c6978f1d1e1a74910e15",
    "frontend/src/pwa/cache-policy.js": "baa55cbe2c227615084f9666568710d9c25259ec8feb673cf28fe4d990807d20",
    "frontend/sw.js": "1db4bdcac4ac719762f3e29e8647de2b6efe6eede3393f8573e36562ce28897c",
}
P006_7_11_15_10_1_3_FRONTEND_TEST_SHA256 = {
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-frame-plan.test.mjs": "05be097b0896a39e766e9a0fb691200891a8a797172164882a35301afd9f78ab",
    "frontend/tests/map/cartography/p006_7_11_15_10_unified-frame-renderer.test.mjs": "7da061caee65a5a209581201dffe3fe4aabd722ec16f912626cfd083a9a5dc36",
    "frontend/tests/map/cartography/p006_7_11_15_10_presentation-coordinator.test.mjs": "70aac0b53eab19451ce3caf89cb64fefe7858ff11964890881b59b4f7bb32ff4",
    "frontend/tests/map/cartography/p006_7_11_15_10_1_3_unified-environmental-compositor.test.mjs": "f367ac70afc0c4bc4c383e4338d0177a83bc6b315be898609227716f052ebdff",
    "frontend/tests/pwa/p006_7_11_15_10_1_3_environmental-composition-refresh.test.mjs": "79d5827758448058fb72a3c82c86d51ba0a177381b7fcca53eb968f8aca3b4ca",
}
P006_7_11_15_10_1_3_PROOF_FILES = (
    "frontend/tests/map/cartography/p006_7_11_15_10_1_3_unified-environmental-compositor.test.mjs",
    "frontend/tests/pwa/p006_7_11_15_10_1_3_environmental-composition-refresh.test.mjs",
    "tests/registries/nngla/test_p006_7_11_15_10_1_3_unified_environmental_composition_lock_qualification.py",
)


def _authorized_p006_7_11_15_10_1_3_unified_environmental_successor(root: Path, target_path: str) -> bool:
    """Authorize only exact reviewed .15.10.1.3 production successors."""
    expected = P006_7_11_15_10_1_3_UNIFIED_ENVIRONMENTAL_PRODUCTION_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_7_11_15_10_1_3_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


def _authorized_p006_7_11_15_10_1_3_frontend_test_successor(root: Path, target_path: str) -> bool:
    """Authorize only exact reviewed .15.10.1.3 frontend-test successors/additions."""
    expected = P006_7_11_15_10_1_3_FRONTEND_TEST_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_7_11_15_10_1_3_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


# P006.UI.10.1.R1 — exact compatibility successor for the already-delivered
# Account & Developer Enrollment Frontend Foundation composition root.
# Historical main.js hashes above remain immutable; this seam recognizes only
# the exact reviewed .10.1 account-enrollment bootstrap successor.
P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_SUCCESSOR_SHA256 = {
    "frontend/src/main.js": "77523c35b98d6c1485850979312dd03bd8a2e32ec74371f380724a4c425bb60f",
}
P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_PROOF_FILES = (
    "frontend/tests/account/account-enrollment-experience.test.mjs",
    "frontend/tests/account/account-enrollment-security.test.mjs",
    "tests/registries/nngla/test_p006_ui_10_1_r1_account_enrollment_composition_successor.py",
)


def _authorized_p006_ui_10_1_account_enrollment_composition_successor(root: Path, target_path: str) -> bool:
    """Authorize only the exact reviewed P006.UI.10.1 main.js successor."""
    expected = P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_UI_10_1_ACCOUNT_ENROLLMENT_COMPOSITION_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


# P006.UI.10.3 — exact reviewed layered Admin authentication composition
# successor. Historical main.js hashes remain immutable; this seam recognizes
# only the exact reviewed .10.3 browser-composition byte sequence.
P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_SUCCESSOR_SHA256 = {
    "frontend/src/main.js": "f2fdb27c6cb2ee2ec436a6b1e06ee78e0eb64d36c1fafb46635cb473452481dd",
}
P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_PROOF_FILES = (
    "frontend/tests/auth/p006-ui-10-3-admin-auth.test.mjs",
    "frontend/tests/auth/p006-ui-10-3-runtime-auth-client.test.mjs",
    "tests/unit/auth/test_p006_ui_10_3_contracts.py",
    "tests/unit/auth/test_p006_ui_10_3_security.py",
)


def _authorized_p006_ui_10_3_layered_admin_composition_successor(
    root: Path,
    target_path: str,
) -> bool:
    """Authorize only the exact reviewed P006.UI.10.3 main.js successor."""
    expected = P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_SUCCESSOR_SHA256.get(
        target_path
    )
    if expected is None:
        return False
    if not all(
        (root / proof).is_file()
        for proof in P006_UI_10_3_LAYERED_ADMIN_COMPOSITION_PROOF_FILES
    ):
        return False
    candidate = root / target_path
    return (
        candidate.is_file()
        and sha256(candidate.read_bytes()).hexdigest() == expected
    )


# P006.UI.10.1.R2 — exact installed-PWA activation maintenance successor.
# The historical v17, .15.10.1.3 and .10.1.R1 hashes remain immutable; this
# seam recognizes only the reviewed service-worker/cache-policy bytes required
# to atomically activate the already-delivered account-enrollment presentation.
P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_SUCCESSOR_SHA256 = {
    "frontend/sw.js": "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d",
    "frontend/src/pwa/cache-policy.js": "2df032f691d551937fb9e0a34ff15b291c218abe14ed69ad99a7a36425e231e2",
}
P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_PROOF_FILES = (
    "frontend/tests/pwa/p006_ui_10_1_r2_account-enrollment-activation-refresh.test.mjs",
    "tests/registries/nngla/test_p006_ui_10_1_r2_installed_pwa_account_enrollment_activation_successor.py",
)


def _authorized_p006_ui_10_1_r2_installed_pwa_activation_successor(root: Path, target_path: str) -> bool:
    """Authorize only exact P006.UI.10.1.R2 PWA activation successors."""
    expected = P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_SUCCESSOR_SHA256.get(target_path)
    if expected is None:
        return False
    if not all((root / proof).is_file() for proof in P006_UI_10_1_R2_INSTALLED_PWA_ACTIVATION_PROOF_FILES):
        return False
    candidate = root / target_path
    return candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == expected


def _authorized_p006_7_11_15_10_r2_pwa_successor(root: Path, target_path: str) -> bool:
    """Preserve R2 bytes and permit only exact reviewed later PWA successors."""
    return (
        _authorized_p006_7_11_15_10_r2_pwa_successor_historical(root, target_path)
        or _authorized_p006_7_11_15_10_1_styling_architecture_successor(root, target_path)
        or _authorized_p006_7_11_15_10_1_3_unified_environmental_successor(root, target_path)
        or _authorized_p006_ui_10_1_r2_installed_pwa_activation_successor(root, target_path)
    )


def test_phase_b_e_does_not_modify_locked_production_or_roadmap_files():
    root = _repo_root()
    proc = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert proc.returncode == 0, proc.stderr
    roadmap_names = {"ROADMAP.md", "PWA_ROADMAP.md", "ROADMAP_TRACKER.md", "roadmap.py", "roadmap_data.py", "roadmap_frontend.py", "pwa_roadmap.py", "pwa_roadmap_data.py", "pwa_roadmap_frontend.py", "roadmap_tracker.py"}
    disallowed = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        path_value = line[3:].strip().replace("\\\\", "/")
        target_path = path_value.split(" -> ", 1)[-1]
        name = target_path.rsplit("/", 1)[-1]
        if name in roadmap_names or target_path.startswith("roadmap/") or target_path.startswith("docs/roadmap/"):
            disallowed.append(target_path)
            continue
        if target_path.startswith("tests/") or target_path.startswith("verification/"):
            continue
        if target_path in P006_7_11_15_10_1_POST_ACCEPTANCE_REMOVALS and status.strip() == "D":
            continue
        if target_path == "registries/nngla/spatial_realization/face_polygonization.py":
            proof = root / "tests/unit/registries/nngla/spatial_realization/test_p006_7_11_15_5_d3_lysora_compatibility.py"
            if proof.is_file():
                continue
            disallowed.append(target_path)
            continue
        if target_path == "database/migrations/migration_manifest.json" and status.strip() == "M":
            current = json.loads((root / target_path).read_text(encoding="utf-8"))
            prior_proc = subprocess.run(["git", "show", f"HEAD:{target_path}"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if prior_proc.returncode != 0:
                disallowed.append(target_path)
                continue
            prior = json.loads(prior_proc.stdout)
            old_rows = prior.get("migrations", [])
            new_rows = current.get("migrations", [])
            root_fields_match = all(current.get(key) == prior.get(key) for key in ("manifest_schema", "manifest_schema_version"))
            append_only = root_fields_match and len(new_rows) > len(old_rows) and new_rows[:len(old_rows)] == old_rows and int(current.get("catalogue_version", 0)) >= int(prior.get("catalogue_version", 0))
            if append_only:
                continue
            disallowed.append(target_path)
            continue
        if _authorized_p006_7_11_15_9_2_3_manifest_successor(root, target_path) or _authorized_p006_7_11_15_9_1_manifest_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_9_seq29_production_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_presentation_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_r2_pwa_successor(root, target_path):
            continue
        if _authorized_p006_ui_10_1_account_enrollment_composition_successor(root, target_path):
            continue
        if _authorized_p006_ui_10_3_layered_admin_composition_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_1_styling_architecture_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_1_2_request_materialization_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_1_test_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_1_3_unified_environmental_successor(root, target_path):
            continue
        if _authorized_p006_7_11_15_10_1_3_frontend_test_successor(root, target_path):
            continue
        if "R" in status or "C" in status:
            disallowed.append(path_value)
            continue
        # A production path is additive only when it did not exist in HEAD.
        # This remains true both before staging (??) and after staging (A/AM).
        if status == "??":
            # Keep the historical untracked-file branch explicit; the HEAD probe
            # below still decides whether the path is genuinely additive.
            pass
        head_probe = subprocess.run(["git", "cat-file", "-e", f"HEAD:{target_path}"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if head_probe.returncode != 0:
            continue
        if _authorized_p006_7_11_15_7_composition_successor(root, target_path):
            continue
        if _authorized_delivery3_existing_path(root, target_path):
            continue
        disallowed.append(target_path)
    assert not disallowed, "Locked production or roadmap surfaces changed during later additive work. Unexpected existing-path changes: " + repr(sorted(disallowed))


def test_delivery3_locked_file_exception_is_structurally_narrow():
    root = _repo_root()
    assert _authorized_d3_lysora_maintenance(root)
    assert not _authorized_delivery3_existing_path(root, "frontend/src/main.js")


def test_p006_7_11_15_7_shared_composition_successors_are_exactly_scoped():
    root = _repo_root()
    assert set(P006_7_11_15_7_COMPOSITION_SUCCESSOR_SHA256) == {
        "frontend/src/main.js",
        "frontend/src/pwa/cache-policy.js",
        "frontend/sw.js",
        "infrastructure/api/app/live_composition.py",
    }
    for target_path in P006_7_11_15_7_COMPOSITION_SUCCESSOR_SHA256:
        assert _authorized_p006_7_11_15_7_composition_successor(root, target_path)
    assert not _authorized_p006_7_11_15_7_composition_successor(root, "frontend/src/app/application.js")
    assert not _authorized_p006_7_11_15_7_composition_successor(root, "roadmap_data.py")
