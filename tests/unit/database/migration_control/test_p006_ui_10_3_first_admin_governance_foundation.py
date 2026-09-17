from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
FORWARD = ROOT / "database" / "migrations" / "m006_10_03_first_admin_governance_foundation.sql"
ROLLBACK = ROOT / "database" / "migrations" / "m006_10_03_first_admin_governance_foundation_rollback.sql"


def _sql():
    return FORWARD.read_text(encoding="utf-8")


def test_migration_creates_only_governance_foundation_tables():
    sql = _sql()
    for table in (
        "admin_developer_id_allocator",
        "enigma_profile_secret_verifier",
        "authority_audit_event",
    ):
        assert f"CREATE TABLE nexilabs_auth.{table}" in sql


def test_migration_does_not_seed_admin_or_principal():
    sql = _sql()
    assert "INSERT INTO nexilabs_auth.principal_account" not in sql
    assert "INSERT INTO nexilabs_auth.admin_operator" not in sql
    assert "INSERT INTO nexilabs_auth.credential_verifier" not in sql


def test_allocator_namespace_is_locked_to_v1_format():
    sql = _sql()
    assert "'ADMIN_DEVELOPER_ID', 'NEXADEV-ADM-', 6, 1, 1" in sql
    assert "reserve_admin_developer_id" in sql
    assert "validate_admin_developer_id_allocator_transition" in sql
    assert "MAX(" not in sql.upper()


def test_enigma_profile_secret_is_verifier_only():
    sql = _sql()
    assert "verifier_payload" in sql
    assert "profile_lookup_word" in sql  # only in a protective comment
    assert "Raw profile secrets are never persisted" in sql
    assert "validate_enigma_profile_secret_verifier_transition" in sql


def test_authority_audit_is_append_only_and_no_truncate():
    sql = _sql()
    assert "authority audit events are immutable append-only authority" in sql
    assert "BEFORE UPDATE OR DELETE" in sql
    assert "BEFORE TRUNCATE" in sql


def test_audit_table_contains_references_not_generic_payload_blob():
    sql = _sql()
    assert "receipt_reference" in sql
    assert "receipt_sha256" in sql
    assert "provider_reference" in sql
    assert " jsonb" not in sql.lower()


def test_public_privileges_are_revoked():
    sql = _sql()
    assert "REVOKE ALL ON TABLE nexilabs_auth.authority_audit_event FROM PUBLIC" in sql
    assert "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA nexilabs_auth FROM PUBLIC" in sql


def test_rollback_removes_only_10_3_objects():
    sql = ROLLBACK.read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS nexilabs_auth.authority_audit_event" in sql
    assert "DROP TABLE IF EXISTS nexilabs_auth.enigma_profile_secret_verifier" in sql
    assert "DROP TABLE IF EXISTS nexilabs_auth.admin_developer_id_allocator" in sql
    assert "principal_account" not in sql
    assert "admin_operator" not in sql


def test_audit_admin_actor_fk_binds_operator_to_same_principal():
    sql = _sql()
    assert "FOREIGN KEY (actor_admin_operator_id, actor_principal_id)" in sql
    assert "REFERENCES nexilabs_auth.admin_operator(admin_operator_id, principal_id)" in sql


def test_first_admin_allocator_transition_is_database_enforced():
    sql = _sql()
    assert "NEW.next_sequence <> OLD.next_sequence + 1" in sql
    assert "Admin Developer ID allocator identity and format are immutable" in sql
