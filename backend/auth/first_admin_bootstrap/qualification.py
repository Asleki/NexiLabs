"""Read-only P006.UI.10.3 PostgreSQL qualification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


_REQUIRED_TABLES = {
    "admin_developer_id_allocator",
    "enigma_profile_secret_verifier",
    "authority_audit_event",
}
_REQUIRED_FUNCTIONS = {
    "reserve_admin_developer_id",
    "validate_admin_developer_id_allocator_transition",
    "validate_enigma_profile_secret_verifier_transition",
    "reject_authority_audit_event_mutation",
    "reject_authority_audit_event_truncate",
}
_REQUIRED_INDEXES = {
    "ux_nexilabs_auth_active_enigma_profile_secret",
    "ix_nexilabs_auth_enigma_profile_secret_state",
    "ux_nexilabs_auth_authority_audit_sequence",
    "ix_nexilabs_auth_authority_audit_type_time",
    "ix_nexilabs_auth_authority_audit_actor",
    "ix_nexilabs_auth_authority_audit_subject",
    "ix_nexilabs_auth_authority_audit_correlation",
}


@dataclass(frozen=True, slots=True)
class QualificationReceipt:
    qualified: bool
    tables: tuple[str, ...]
    functions: tuple[str, ...]
    indexes: tuple[str, ...]
    allocator_row: tuple[object, ...] | None
    active_catalogue_lengths: tuple[int, ...]
    active_catalogue_entry_count: int
    admin_operator_count: int
    active_admin_password_count: int
    active_enigma_secret_count: int
    audit_event_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "qualified": self.qualified,
            "tables": list(self.tables),
            "functions": list(self.functions),
            "indexes": list(self.indexes),
            "allocatorRow": list(self.allocator_row) if self.allocator_row else None,
            "activeCatalogueLengths": list(self.active_catalogue_lengths),
            "activeCatalogueEntryCount": self.active_catalogue_entry_count,
            "adminOperatorCount": self.admin_operator_count,
            "activeAdminPasswordCount": self.active_admin_password_count,
            "activeEnigmaSecretCount": self.active_enigma_secret_count,
            "auditEventCount": self.audit_event_count,
        }


def qualify(connect: Callable[[], object], *, expected_admin_count: int | None = None) -> QualificationReceipt:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(
                """
                SELECT table_name
                  FROM information_schema.tables
                 WHERE table_schema='nexilabs_auth'
                   AND table_name = ANY(%s)
                 ORDER BY table_name
                """,
                (list(sorted(_REQUIRED_TABLES)),),
            )
            tables = tuple(str(row[0]) for row in cursor.fetchall())
            cursor.execute(
                """
                SELECT p.proname
                  FROM pg_proc AS p
                  JOIN pg_namespace AS n ON n.oid=p.pronamespace
                 WHERE n.nspname='nexilabs_auth'
                   AND p.proname = ANY(%s)
                 ORDER BY p.proname
                """,
                (list(sorted(_REQUIRED_FUNCTIONS)),),
            )
            functions = tuple(str(row[0]) for row in cursor.fetchall())
            cursor.execute(
                """
                SELECT indexname
                  FROM pg_indexes
                 WHERE schemaname='nexilabs_auth'
                   AND indexname = ANY(%s)
                 ORDER BY indexname
                """,
                (list(sorted(_REQUIRED_INDEXES)),),
            )
            indexes = tuple(str(row[0]) for row in cursor.fetchall())
            cursor.execute(
                """
                SELECT allocator_key, id_prefix, sequence_width, next_sequence, format_version
                  FROM nexilabs_auth.admin_developer_id_allocator
                 WHERE allocator_key='ADMIN_DEVELOPER_ID'
                """
            )
            allocator = cursor.fetchone()
            cursor.execute(
                "SELECT word_length FROM nexilabs_auth.enigma_catalogue WHERE catalogue_state='ACTIVE' ORDER BY word_length"
            )
            lengths = tuple(int(row[0]) for row in cursor.fetchall())
            cursor.execute(
                """
                SELECT COUNT(*)
                  FROM nexilabs_auth.enigma_catalogue_entry AS e
                  JOIN nexilabs_auth.enigma_catalogue AS c
                    ON c.catalogue_id=e.catalogue_id AND c.word_length=e.word_length
                 WHERE c.catalogue_state='ACTIVE'
                """
            )
            entry_count = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.admin_operator")
            admin_count = int(cursor.fetchone()[0])
            cursor.execute(
                "SELECT COUNT(*) FROM nexilabs_auth.credential_verifier WHERE credential_kind='ADMIN_PASSWORD' AND credential_state='ACTIVE'"
            )
            admin_password_count = int(cursor.fetchone()[0])
            cursor.execute(
                "SELECT COUNT(*) FROM nexilabs_auth.enigma_profile_secret_verifier WHERE secret_state='ACTIVE'"
            )
            enigma_secret_count = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.authority_audit_event")
            audit_count = int(cursor.fetchone()[0])

    structural = (
        set(tables) == _REQUIRED_TABLES
        and set(functions) == _REQUIRED_FUNCTIONS
        and set(indexes) == _REQUIRED_INDEXES
        and allocator is not None
        and tuple(allocator[:3]) == ("ADMIN_DEVELOPER_ID", "NEXADEV-ADM-", 6)
        and int(allocator[4]) == 1
        and lengths == (3, 4, 5)
        and entry_count == 279
    )
    bootstrap_ok = expected_admin_count is None or admin_count == expected_admin_count
    if expected_admin_count == 0:
        bootstrap_ok = bootstrap_ok and admin_password_count == 0 and enigma_secret_count == 0
    if expected_admin_count == 1:
        bootstrap_ok = bootstrap_ok and admin_password_count == 1 and enigma_secret_count == 1 and audit_count >= 1
    return QualificationReceipt(
        qualified=bool(structural and bootstrap_ok),
        tables=tables,
        functions=functions,
        indexes=indexes,
        allocator_row=tuple(allocator) if allocator else None,
        active_catalogue_lengths=lengths,
        active_catalogue_entry_count=entry_count,
        admin_operator_count=admin_count,
        active_admin_password_count=admin_password_count,
        active_enigma_secret_count=enigma_secret_count,
        audit_event_count=audit_count,
    )
