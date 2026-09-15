from pathlib import Path

from backend.auth.final_persistence_authority_qualification.qualification import (
    G_MIGRATION_COUNT,
    G_TAIL_SEQUENCE,
    OPERATIONAL_TABLES,
)


def test_g_is_read_only_and_owns_no_migration_or_persistence_adapter():
    package_dir = Path(__file__).resolve().parents[3] / "backend/auth/final_persistence_authority_qualification"
    qualification = (package_dir / "qualification.py").read_text(encoding="utf-8")
    assert "connection(read_only=False)" not in qualification
    assert "INSERT INTO" not in qualification
    assert "UPDATE nexilabs_auth" not in qualification
    assert "DELETE FROM" not in qualification
    assert not (package_dir / "postgresql.py").exists()
    assert not (package_dir / "service.py").exists()
    assert G_MIGRATION_COUNT == 36
    assert G_TAIL_SEQUENCE == 36
    assert "enigma_catalogue" not in OPERATIONAL_TABLES
    assert "enigma_catalogue_entry" not in OPERATIONAL_TABLES


def test_zero_operational_surface_covers_a_through_f_non_catalogue_authority():
    required = {
        "principal_account", "credential_verifier", "developer_access_request",
        "developer_setup", "admin_operator", "developer_access_decision",
        "email_verification_challenge", "credential_bundle",
        "credential_bundle_secret", "credential_delivery", "enrollment_event",
        "notification_delivery", "audit_export", "enigma_profile",
        "principal_enigma_profile",
    }
    assert required.issubset(set(OPERATIONAL_TABLES))
