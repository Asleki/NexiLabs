from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from backend.auth.final_persistence_authority_qualification.contracts import (
    FinalPersistenceAuthorityQualificationError,
)
from backend.auth.final_persistence_authority_qualification.qualification import (
    G_MIGRATION_COUNT,
    G_PREDECESSOR_COMMIT,
    G_PREDECESSOR_TAG,
    G_TAIL_ID,
    FinalPersistenceAuthorityQualification,
    P006_10_2_CHAIN,
)


def _make_repository(root: Path) -> None:
    migration_dir = root / "database" / "migrations"
    migration_dir.mkdir(parents=True)
    chain = {sequence: (mid, dep) for sequence, mid, dep in P006_10_2_CHAIN}
    rows = []
    previous = None
    for sequence in range(1, G_MIGRATION_COUNT + 1):
        migration_id = f"m_test_{sequence:02d}"
        dependency = previous
        if sequence in chain:
            migration_id, dependency = chain[sequence]
        forward_name = f"{migration_id}.sql"
        rollback_name = f"{migration_id}_rollback.sql"
        forward = f"-- forward {sequence}\n".encode()
        rollback = f"-- rollback {sequence}\n".encode()
        (migration_dir / forward_name).write_bytes(forward)
        (migration_dir / rollback_name).write_bytes(rollback)
        rows.append({
            "migration_id": migration_id,
            "milestone_id": "M006.10.2" if sequence >= 31 else "TEST",
            "sequence_number": sequence,
            "forward_file": forward_name,
            "rollback_file": rollback_name,
            "depends_on": [] if dependency is None else [dependency],
            "forward_sha256": sha256(forward).hexdigest(),
            "rollback_sha256": sha256(rollback).hexdigest(),
            "forward_byte_size": len(forward),
            "rollback_byte_size": len(rollback),
        })
        previous = migration_id
    payload = {"catalogue_version": 20, "migrations": rows}
    (migration_dir / "migration_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def test_repository_closure_verifies_every_migration_artifact(tmp_path):
    _make_repository(tmp_path)
    rows, manifest_sha = FinalPersistenceAuthorityQualification.verify_repository_artifacts(tmp_path)
    assert len(rows) == 36
    assert rows[-1]["migration_id"] == G_TAIL_ID
    assert len(manifest_sha) == 64


def test_repository_closure_rejects_artifact_drift(tmp_path):
    _make_repository(tmp_path)
    manifest = json.loads((tmp_path / "database/migrations/migration_manifest.json").read_text())
    target = tmp_path / "database/migrations" / manifest["migrations"][10]["forward_file"]
    target.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(FinalPersistenceAuthorityQualificationError, match="checksum mismatch"):
        FinalPersistenceAuthorityQualification.verify_repository_artifacts(tmp_path)


def test_source_lock_requires_f_commit_main_and_peeled_tag(monkeypatch, tmp_path):
    answers = {
        ("rev-parse", "HEAD"): G_PREDECESSOR_COMMIT,
        ("rev-parse", "--abbrev-ref", "HEAD"): "main",
        ("rev-parse", "origin/main"): G_PREDECESSOR_COMMIT,
        ("cat-file", "-t", G_PREDECESSOR_TAG): "tag",
        ("rev-parse", f"{G_PREDECESSOR_TAG}^{{}}"): G_PREDECESSOR_COMMIT,
    }
    monkeypatch.setattr(
        FinalPersistenceAuthorityQualification,
        "_git",
        staticmethod(lambda root, *args: answers[args]),
    )
    assert FinalPersistenceAuthorityQualification.verify_source_lock(tmp_path) == (
        G_PREDECESSOR_COMMIT, "main", G_PREDECESSOR_COMMIT
    )


def test_ledger_requires_exact_36_applied_and_checksum_match(tmp_path):
    _make_repository(tmp_path)
    _, rows, _ = FinalPersistenceAuthorityQualification._read_manifest(
        tmp_path / "database/migrations/migration_manifest.json"
    )
    ledger = [
        (row["migration_id"], row["sequence_number"], row["forward_sha256"], "APPLIED")
        for row in rows
    ]
    FinalPersistenceAuthorityQualification._assert_ledger(rows, ledger)
    with pytest.raises(FinalPersistenceAuthorityQualificationError, match="expected 36"):
        FinalPersistenceAuthorityQualification._assert_ledger(rows, ledger[:-1])


class _RegexCursor:
    def __init__(self, definition: str):
        self.definition = definition
    def execute(self, query, params=None):
        return None
    def fetchone(self):
        return (self.definition,)


def test_sequence_36_regex_proof_rejects_oversized_bounded_repetition():
    bad = "CHECK (filter_reference ~ '^[A-Z].{0,1966}$' AND length(filter_reference) <= 2048)"
    with pytest.raises(FinalPersistenceAuthorityQualificationError, match="oversized"):
        FinalPersistenceAuthorityQualification._assert_regex_correction(_RegexCursor(bad))
    good = "CHECK (filter_reference ~ '^[A-Z][A-Z0-9_]{2,79}:[A-Za-z0-9][A-Za-z0-9._:/=-]*$' AND length(filter_reference) <= 2048)"
    assert FinalPersistenceAuthorityQualification._assert_regex_correction(_RegexCursor(good)) is True


def test_parent_manifest_object_inventory_aggregates_exact_31_to_36_surface():
    rows = tuple(
        {
            "sequence_number": i,
            "migration_id": f"m{i}",
            "expected_objects": {
                "schemas": ["nexilabs_auth"] if i == 31 else [],
                "tables": [f"nexilabs_auth.t{i}"],
                "indexes": [f"ix_t{i}"],
                "constraints": [f"nexilabs_auth.ck_t{i}"],
                "views": [],
                "functions": [f"nexilabs_auth.fn_t{i}"],
            },
        }
        for i in range(1, 37)
    )
    inventory = FinalPersistenceAuthorityQualification._parent_expected_objects(rows)
    assert inventory["schemas"] == ("nexilabs_auth",)
    assert inventory["tables"] == tuple(f"nexilabs_auth.t{i}" for i in range(31, 37))
    assert inventory["indexes"] == tuple(f"ix_t{i}" for i in range(31, 37))
    assert inventory["constraints"] == tuple(f"nexilabs_auth.ck_t{i}" for i in range(31, 37))
    assert inventory["functions"] == tuple(f"nexilabs_auth.fn_t{i}" for i in range(31, 37))


def test_account_authority_runtime_proof_requires_all_zero_state_reads(monkeypatch):
    import sys
    import types

    persistence = types.ModuleType("backend.auth.persistence")
    adapter_module = types.ModuleType("backend.auth.persistence.postgresql_account_authority")

    class GoodAuthority:
        def __init__(self, pool): self.pool = pool
        def principal_by_username(self, value): return None
        def active_password_verifier(self, value): return None
        def primary_email(self, value): return None
        def developer_setup_by_lookup_key(self, value): return None
        def enigma_catalogue_entry(self, **kwargs): return None

    adapter_module.PostgreSQLAccountAuthority = GoodAuthority
    monkeypatch.setitem(sys.modules, "backend.auth.persistence", persistence)
    monkeypatch.setitem(sys.modules, "backend.auth.persistence.postgresql_account_authority", adapter_module)

    class Pool:
        def connection(self, read_only=True): raise AssertionError("fake adapter should not access pool")

    qualifier = FinalPersistenceAuthorityQualification(Pool())
    assert qualifier._verify_account_authority_empty_reads() is True

    class BadAuthority(GoodAuthority):
        def active_password_verifier(self, value): return object()

    adapter_module.PostgreSQLAccountAuthority = BadAuthority
    with pytest.raises(FinalPersistenceAuthorityQualificationError, match="zero-state runtime read proof"):
        qualifier._verify_account_authority_empty_reads()
