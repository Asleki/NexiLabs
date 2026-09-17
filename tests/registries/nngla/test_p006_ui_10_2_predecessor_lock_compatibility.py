"""P006.UI.10.2 — predecessor, strict-hash and committed-manifest qualification.

These tests are additive. They do not replace any historical R1/R2 lock tests.
They qualify that .10.2 touches none of the strict predecessor surfaces that
caused the earlier five regression failures and that the committed .10.2.A
migration-manifest authority remains an immutable prefix for later successors.

Compatibility maintenance:
The original manifest assertion compared the working tree with ``HEAD`` and
expected one new row. That was correct only while .10.2.A was uncommitted.
After .10.2.A became HEAD, the comparison became self-relative and could never
pass. The lock now anchors to the immutable .10.2.A commit instead.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


MIGRATION_ID = "m006_10_02_nexilabs_account_credential_authority"
P006_UI_10_2_A_COMMIT = "cc28249f89ae9b530f0569d306ddd6cc6354e01c"

P006_UI_10_3_REVIEWED_SUCCESSOR_SHA256 = {
    "frontend/src/main.js": "f2fdb27c6cb2ee2ec436a6b1e06ee78e0eb64d36c1fafb46635cb473452481dd",
    "tests/registries/nngla/test_p006_7_11_15_10_presentation_successor_lock_qualification.py": "070d923f522863c28bb7ff8d48d9d226a2d946c65e6b40c9d9dc9e853b053821",
    "tests/registries/nngla/test_p006_7_11_15_9_cm1_r1_lock_qualification.py": "c9062bc26b47aacfc5c54171f1173822a70c6565bb40d29b1bf19401c3c1cb0f",
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py": "3ec98aedf6580f69f6b31924765c1f1c49e636b7cd71f52b908a2ff4ec473cde",
    "tests/registries/nngla/test_p006_7_11_15_10_1_2_request_scoped_materialization_lock_qualification.py": "8d6e7e5361d120568d993219fe4c5320976f62e819f10c3394ef5a2655b5a0f0",
    "tests/registries/nngla/test_p006_7_11_15_10_1_3_unified_environmental_composition_lock_qualification.py": "dd6c9c17cb8d30e69d92a51f5142b388a2152ea787021f234bf66b63cd97934c",
}

IMMUTABLE_PREDECESSOR_PATHS = (
    "frontend/src/main.js",
    "frontend/sw.js",
    "frontend/src/pwa/cache-policy.js",
    "backend/auth/__init__.py",
    "backend/auth/contracts.py",
    "backend/auth/credentials.py",
    "backend/auth/development_server.py",
    "backend/auth/development_service.py",
    "backend/auth/enigma.py",
    "backend/auth/sessions.py",
    "tests/registries/nngla/test_p006_7_11_15_10_presentation_successor_lock_qualification.py",
    "tests/registries/nngla/test_p006_7_11_15_9_cm1_r1_lock_qualification.py",
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py",
    "tests/registries/nngla/test_p006_7_11_15_10_r2_pwa_successor_lock_qualification.py",
    "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py",
    "tests/registries/nngla/test_p006_7_11_15_10_1_2_request_scoped_materialization_lock_qualification.py",
    "tests/registries/nngla/test_p006_7_11_15_10_1_3_unified_environmental_composition_lock_qualification.py",
)

KNOWN_D62C5C1_HASHES = {
    "frontend/src/main.js": "77523c35b98d6c1485850979312dd03bd8a2e32ec74371f380724a4c425bb60f",
    "frontend/sw.js": "7fb8964ddbb9efe64948eb842dd6534f5b6cba2bd8caf87ed56d914064bda84d",
    "frontend/src/pwa/cache-policy.js": "2df032f691d551937fb9e0a34ff15b291c218abe14ed69ad99a7a36425e231e2",
    "tests/registries/nngla/test_p006_7_11_15_10_presentation_successor_lock_qualification.py": "d6a7b002801373e62b83d08366e6f8a91920e1f6f2cebdaad5ae3f5b1b798eb2",
    "tests/registries/nngla/test_p006_7_11_15_9_cm1_r1_lock_qualification.py": "ee676f0cd8387a35ac50393f371e6cebf7e23cc8da7721fe79784c3e9ae182d1",
    "tests/registries/nngla/test_p006_7_11_7_20_operational_backend_lock.py": "77e2706e92d454f9cf2203e7e62275a46e5f1dcce100b825efd17056b9eab8fb",
    "tests/registries/nngla/test_p006_7_11_15_10_r2_pwa_successor_lock_qualification.py": "c07f11f508ddb48d1e9da88c8d9f3cc144ff28b2eb279056c6adda81a132805a",
    "tests/registries/nngla/test_p006_7_11_15_10_1_styling_architecture_lock_qualification.py": "70f744e609c4012d4070fdfbdddd22f5a6bf4494ec063a1a42b528a53d39bf8d",
    "tests/registries/nngla/test_p006_7_11_15_10_1_2_request_scoped_materialization_lock_qualification.py": "b363d3faebb4631ad0f785d0b8c2aed2167429892f0c9381c396bd29abf6a03b",
    "tests/registries/nngla/test_p006_7_11_15_10_1_3_unified_environmental_composition_lock_qualification.py": "636e2dfe99c33539f04f65e788f2dfb62aaccd283e3b269d68782182c577bb62",
}

ROADMAP_PATHS = (
    "ROADMAP.md","PWA_ROADMAP.md","ROADMAP_TRACKER.md",
    "roadmap.py","roadmap_data.py","roadmap_frontend.py",
    "pwa_roadmap.py","pwa_roadmap_data.py","pwa_roadmap_frontend.py",
    "roadmap_tracker.py",
)

def _root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / ".git").exists() and (candidate / "database" / "migrations").is_dir():
            return candidate
    raise AssertionError("git repository root not found")

def _git_bytes(root: Path, revision: str, path: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    return proc.stdout if proc.returncode == 0 else None

def _head_bytes(root: Path, path: str) -> bytes | None:
    return _git_bytes(root, "HEAD", path)

def test_d62c5c1_known_strict_hash_predecessors_are_still_exact() -> None:
    root = _root()
    for path, expected in KNOWN_D62C5C1_HASHES.items():
        candidate = root / path
        assert candidate.is_file(), path
        head = _head_bytes(root, path)
        assert head is not None, path
        assert sha256(head).hexdigest() == expected, path
        reviewed = P006_UI_10_3_REVIEWED_SUCCESSOR_SHA256.get(path)
        if reviewed is None:
            assert candidate.read_bytes() == head, path
        else:
            assert sha256(candidate.read_bytes()).hexdigest() == reviewed, path

def test_all_locked_auth_pwa_strict_tests_and_roadmaps_are_byte_identical_to_head() -> None:
    root = _root()
    for path in (*IMMUTABLE_PREDECESSOR_PATHS, *ROADMAP_PATHS):
        head = _head_bytes(root, path)
        candidate = root / path
        if head is None and not candidate.exists():
            continue
        assert head is not None, f"P006.UI.10.2 must not introduce predecessor path {path}"
        assert candidate.is_file(), f"P006.UI.10.2 must not remove predecessor path {path}"
        reviewed = P006_UI_10_3_REVIEWED_SUCCESSOR_SHA256.get(path)
        if reviewed is not None:
            assert sha256(candidate.read_bytes()).hexdigest() == reviewed, path
            continue
        assert candidate.read_bytes() == head, f"P006.UI.10.2 modified locked predecessor {path}"

def test_complete_migration_manifest_preserves_committed_10_2_a_predecessor_prefix() -> None:
    root = _root()
    path = "database/migrations/migration_manifest.json"
    predecessor_bytes = _git_bytes(root, P006_UI_10_2_A_COMMIT, path)
    assert predecessor_bytes is not None, "immutable P006.UI.10.2.A manifest is unavailable"

    predecessor = json.loads(predecessor_bytes.decode("utf-8"))
    current = json.loads((root / path).read_text(encoding="utf-8"))

    assert predecessor["catalogue_version"] == 15
    assert predecessor["migrations"][-1]["migration_id"] == MIGRATION_ID
    assert predecessor["migrations"][-1]["sequence_number"] == 31

    assert current["manifest_schema"] == predecessor["manifest_schema"]
    assert current["manifest_schema_version"] == predecessor["manifest_schema_version"]
    assert current["catalogue_version"] >= predecessor["catalogue_version"]
    assert len(current["migrations"]) >= len(predecessor["migrations"])
    assert current["migrations"][: len(predecessor["migrations"])] == predecessor["migrations"]

def test_private_development_auth_fixtures_remain_ignored_and_not_production_files() -> None:
    root = _root()
    for path in (
        "development/auth/private/credentials/guests.local.json",
        "development/auth/private/credentials/developers.local.json",
        "development/auth/private/enigma/enigma_words_3.csv",
        "development/auth/private/enigma/enigma_words_4.csv",
        "development/auth/private/enigma/enigma_words_5.csv",
    ):
        proc = subprocess.run(
            ["git", "check-ignore", path],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False,
        )
        assert proc.returncode == 0, f"private fixture is not ignored: {path}"
