"""P006.UI.10.2.G — final read-only AWS persistence-authority qualification.

G creates no database authority. It re-reads the completed A–F persistence
prefix, requires the exact sequence-36 repository/AWS closure state, requalifies
the governed B catalogue against the locked private source bytes, proves zero
operational authority, and returns only safe closure evidence.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from .contracts import (
    EnigmaCatalogueClosureEvidence,
    FinalPersistenceAuthorityQualificationError,
    FinalPersistenceAuthorityQualificationReport,
)


G_MILESTONE = "P006.UI.10.2.G"
G_PREDECESSOR_COMMIT = "34260d66d513c77f3bf9d59ac8a42003537cec43"
G_PREDECESSOR_TAG = "P006.UI.10.2.F-enrollment-notification-audit-persistence"
G_TAG = "P006.UI.10.2.G-final-aws-persistence-authority-qualification"
PARENT_CLOSURE_TAG = "P006.UI.10.2-governed-account-credential-persistence-closed"
G_CATALOGUE_VERSION = 20
G_MIGRATION_COUNT = 36
G_TAIL_SEQUENCE = 36
G_TAIL_ID = "m006_10_02_enrollment_notification_audit_filter_regex_correction"

P006_10_2_CHAIN = (
    (31, "m006_10_02_nexilabs_account_credential_authority",
     "m006_07_11_nngla_municipality_public_read_qualification_admission_correction"),
    (32, "m006_10_02_layered_admin_review_authority",
     "m006_10_02_nexilabs_account_credential_authority"),
    (33, "m006_10_02_email_verification_challenge",
     "m006_10_02_layered_admin_review_authority"),
    (34, "m006_10_02_credential_bundle_storage_delivery",
     "m006_10_02_email_verification_challenge"),
    (35, "m006_10_02_enrollment_notification_audit_persistence",
     "m006_10_02_credential_bundle_storage_delivery"),
    (36, G_TAIL_ID, "m006_10_02_enrollment_notification_audit_persistence"),
)

OPERATIONAL_TABLES = (
    "principal_account",
    "principal_profile",
    "principal_permission",
    "account_email",
    "credential_verifier",
    "developer_access_request",
    "developer_setup",
    "enigma_profile",
    "enigma_profile_catalogue",
    "principal_enigma_profile",
    "admin_operator",
    "developer_access_decision",
    "email_verification_challenge",
    "credential_bundle",
    "credential_bundle_secret",
    "credential_delivery",
    "enrollment_event",
    "notification_delivery",
    "audit_export",
)


class FinalPersistenceAuthorityQualification:
    """Orchestrate the final P006.UI.10.2 closure without performing writes."""

    def __init__(self, pool: Any) -> None:
        if pool is None or not callable(getattr(pool, "connection", None)):
            raise TypeError("pool with connection(read_only=...) is required")
        self.pool = pool

    @staticmethod
    def _git(root: Path, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise FinalPersistenceAuthorityQualificationError(
                f"cannot prove Git source lock: git {' '.join(args)}"
            ) from exc
        return completed.stdout.strip()

    @classmethod
    def verify_source_lock(cls, repository_root: Path) -> tuple[str, str, str]:
        root = Path(repository_root)
        head = cls._git(root, "rev-parse", "HEAD")
        branch = cls._git(root, "rev-parse", "--abbrev-ref", "HEAD")
        origin_main = cls._git(root, "rev-parse", "origin/main")
        tag_type = cls._git(root, "cat-file", "-t", G_PREDECESSOR_TAG)
        tag_commit = cls._git(root, "rev-parse", f"{G_PREDECESSOR_TAG}^{{}}")
        if head != G_PREDECESSOR_COMMIT:
            raise FinalPersistenceAuthorityQualificationError(
                f"G requires F predecessor HEAD {G_PREDECESSOR_COMMIT}, got {head}"
            )
        if branch != "main":
            raise FinalPersistenceAuthorityQualificationError(
                f"G qualification must begin on main, got {branch}"
            )
        if origin_main != G_PREDECESSOR_COMMIT:
            raise FinalPersistenceAuthorityQualificationError(
                f"G requires origin/main at F predecessor {G_PREDECESSOR_COMMIT}, got {origin_main}"
            )
        if tag_type != "tag":
            raise FinalPersistenceAuthorityQualificationError(
                "F predecessor tag must be an annotated tag object"
            )
        if tag_commit != G_PREDECESSOR_COMMIT:
            raise FinalPersistenceAuthorityQualificationError(
                "F annotated tag does not peel to the required predecessor commit"
            )
        return head, branch, tag_commit

    @staticmethod
    def _read_manifest(manifest_path: Path) -> tuple[dict[str, object], tuple[dict[str, object], ...], str]:
        path = Path(manifest_path)
        try:
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FinalPersistenceAuthorityQualificationError(
                "cannot read the live migration manifest"
            ) from exc
        if not isinstance(payload, dict):
            raise FinalPersistenceAuthorityQualificationError("migration manifest root must be an object")
        if payload.get("catalogue_version") != G_CATALOGUE_VERSION:
            raise FinalPersistenceAuthorityQualificationError(
                f"G closure requires catalogue_version {G_CATALOGUE_VERSION}"
            )
        rows = payload.get("migrations")
        if not isinstance(rows, list) or len(rows) != G_MIGRATION_COUNT:
            raise FinalPersistenceAuthorityQualificationError(
                f"G closure requires exactly {G_MIGRATION_COUNT} repository migrations"
            )
        result = tuple(row for row in rows if isinstance(row, dict))
        if len(result) != len(rows):
            raise FinalPersistenceAuthorityQualificationError(
                "migration manifest contains a malformed row"
            )
        sequences = tuple(int(row.get("sequence_number", -1)) for row in result)
        if sequences != tuple(range(1, G_MIGRATION_COUNT + 1)):
            raise FinalPersistenceAuthorityQualificationError(
                "migration manifest sequence is not exact 1..36 closure history"
            )
        for sequence, migration_id, dependency in P006_10_2_CHAIN:
            row = result[sequence - 1]
            if row.get("migration_id") != migration_id:
                raise FinalPersistenceAuthorityQualificationError(
                    f"P006.UI.10.2 migration mismatch at sequence {sequence}"
                )
            if row.get("milestone_id") != "M006.10.2":
                raise FinalPersistenceAuthorityQualificationError(
                    f"P006.UI.10.2 milestone id mismatch at sequence {sequence}"
                )
            if row.get("depends_on") != [dependency]:
                raise FinalPersistenceAuthorityQualificationError(
                    f"P006.UI.10.2 dependency mismatch at sequence {sequence}"
                )
        return payload, result, sha256(raw).hexdigest()

    @classmethod
    def verify_repository_artifacts(
        cls, repository_root: Path
    ) -> tuple[tuple[dict[str, object], ...], str]:
        root = Path(repository_root)
        _, rows, manifest_sha = cls._read_manifest(
            root / "database" / "migrations" / "migration_manifest.json"
        )
        migration_dir = root / "database" / "migrations"
        for row in rows:
            for file_key, hash_key, size_key in (
                ("forward_file", "forward_sha256", "forward_byte_size"),
                ("rollback_file", "rollback_sha256", "rollback_byte_size"),
            ):
                filename = row.get(file_key)
                if not isinstance(filename, str) or not filename:
                    raise FinalPersistenceAuthorityQualificationError(
                        f"migration {row.get('migration_id')} has no {file_key}"
                    )
                path = migration_dir / filename
                if not path.is_file():
                    raise FinalPersistenceAuthorityQualificationError(
                        f"missing migration artifact: {filename}"
                    )
                raw = path.read_bytes()
                if row.get(hash_key) != sha256(raw).hexdigest():
                    raise FinalPersistenceAuthorityQualificationError(
                        f"migration artifact checksum mismatch: {filename}"
                    )
                try:
                    expected_size = int(row.get(size_key, -1))
                except (TypeError, ValueError) as exc:
                    raise FinalPersistenceAuthorityQualificationError(
                        f"invalid migration artifact byte size: {filename}"
                    ) from exc
                if expected_size != len(raw):
                    raise FinalPersistenceAuthorityQualificationError(
                        f"migration artifact byte-size mismatch: {filename}"
                    )
        return rows, manifest_sha

    @staticmethod
    def _assert_ledger(
        manifest_rows: tuple[dict[str, object], ...], ledger_rows: list[tuple[Any, ...]]
    ) -> None:
        if len(ledger_rows) != G_MIGRATION_COUNT:
            raise FinalPersistenceAuthorityQualificationError(
                f"database migration ledger count is {len(ledger_rows)}, expected 36"
            )
        for manifest, ledger in zip(manifest_rows, ledger_rows):
            migration_id, sequence_number, checksum_sha256, status = ledger
            if str(migration_id) != str(manifest.get("migration_id")):
                raise FinalPersistenceAuthorityQualificationError(
                    "database migration ledger contains an unknown/missing migration"
                )
            if int(sequence_number) != int(manifest.get("sequence_number", -1)):
                raise FinalPersistenceAuthorityQualificationError(
                    "database migration ledger sequence mismatch"
                )
            if str(checksum_sha256) != str(manifest.get("forward_sha256")):
                raise FinalPersistenceAuthorityQualificationError(
                    f"database migration checksum mismatch: {migration_id}"
                )
            if str(status) != "APPLIED":
                raise FinalPersistenceAuthorityQualificationError(
                    f"database migration is not APPLIED: {migration_id} ({status})"
                )
        tail = ledger_rows[-1]
        if int(tail[1]) != G_TAIL_SEQUENCE or str(tail[0]) != G_TAIL_ID:
            raise FinalPersistenceAuthorityQualificationError(
                "database migration tail is not the qualified sequence-36 F correction"
            )

    @staticmethod
    def _public_privilege_counts(cursor: Any) -> tuple[int, int, int]:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pg_namespace AS n
            CROSS JOIN LATERAL aclexplode(
                COALESCE(n.nspacl, acldefault('n', n.nspowner))
            ) AS acl
            WHERE n.nspname = 'nexilabs_auth' AND acl.grantee = 0
            """
        )
        schema_count = int(cursor.fetchone()[0])
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.table_privileges
            WHERE table_schema = 'nexilabs_auth' AND grantee = 'PUBLIC'
            """
        )
        table_count = int(cursor.fetchone()[0])
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.routine_privileges
            WHERE routine_schema = 'nexilabs_auth' AND grantee = 'PUBLIC'
            """
        )
        routine_count = int(cursor.fetchone()[0])
        if schema_count or table_count or routine_count:
            raise FinalPersistenceAuthorityQualificationError(
                "PUBLIC privileges remain on governed nexilabs_auth objects"
            )
        return schema_count, table_count, routine_count

    @staticmethod
    def _operational_counts(cursor: Any) -> tuple[tuple[str, int], ...]:
        counts: list[tuple[str, int]] = []
        for table in OPERATIONAL_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM nexilabs_auth.{table}")
            counts.append((table, int(cursor.fetchone()[0])))
        nonzero = [(name, count) for name, count in counts if count != 0]
        if nonzero:
            rendered = ", ".join(f"{name}={count}" for name, count in nonzero)
            raise FinalPersistenceAuthorityQualificationError(
                "G closure requires zero operational authority rows: " + rendered
            )
        return tuple(counts)

    @staticmethod
    def _parent_expected_objects(
        manifest_rows: tuple[dict[str, object], ...]
    ) -> dict[str, tuple[str, ...]]:
        collected: dict[str, set[str]] = {
            "schemas": set(), "tables": set(), "indexes": set(),
            "constraints": set(), "views": set(), "functions": set(),
        }
        for row in manifest_rows[G_TAIL_SEQUENCE - 6:G_TAIL_SEQUENCE]:
            expected = row.get("expected_objects")
            if not isinstance(expected, dict):
                raise FinalPersistenceAuthorityQualificationError(
                    f"migration {row.get('migration_id')} has malformed expected_objects"
                )
            for kind in collected:
                values = expected.get(kind, [])
                if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                    raise FinalPersistenceAuthorityQualificationError(
                        f"migration {row.get('migration_id')} has malformed {kind} inventory"
                    )
                collected[kind].update(values)
        return {kind: tuple(sorted(values)) for kind, values in collected.items()}

    @classmethod
    def _verify_manifest_structural_objects(
        cls, cursor: Any, manifest_rows: tuple[dict[str, object], ...]
    ) -> bool:
        expected = cls._parent_expected_objects(manifest_rows)

        for schema in expected["schemas"]:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s)", (schema,))
            if not bool(cursor.fetchone()[0]):
                raise FinalPersistenceAuthorityQualificationError(f"missing expected schema: {schema}")

        for table in expected["tables"]:
            cursor.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
            if not bool(cursor.fetchone()[0]):
                raise FinalPersistenceAuthorityQualificationError(f"missing expected table: {table}")

        for index in expected["indexes"]:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'nexilabs_auth' AND indexname = %s)",
                (index,),
            )
            if not bool(cursor.fetchone()[0]):
                raise FinalPersistenceAuthorityQualificationError(f"missing expected index: {index}")

        for qualified in expected["constraints"]:
            schema, name = qualified.split(".", 1) if "." in qualified else ("nexilabs_auth", qualified)
            cursor.execute(
                """SELECT EXISTS (
                       SELECT 1 FROM pg_constraint AS c
                       JOIN pg_class AS t ON t.oid = c.conrelid
                       JOIN pg_namespace AS n ON n.oid = t.relnamespace
                       WHERE n.nspname = %s AND c.conname = %s
                   )""",
                (schema, name),
            )
            if not bool(cursor.fetchone()[0]):
                raise FinalPersistenceAuthorityQualificationError(f"missing expected constraint: {qualified}")

        for qualified in expected["views"]:
            schema, name = qualified.split(".", 1) if "." in qualified else ("nexilabs_auth", qualified)
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = %s AND table_name = %s)",
                (schema, name),
            )
            if not bool(cursor.fetchone()[0]):
                raise FinalPersistenceAuthorityQualificationError(f"missing expected view: {qualified}")

        for qualified in expected["functions"]:
            schema, name = qualified.split(".", 1) if "." in qualified else ("nexilabs_auth", qualified)
            cursor.execute(
                """SELECT EXISTS (
                       SELECT 1 FROM pg_proc AS p
                       JOIN pg_namespace AS n ON n.oid = p.pronamespace
                       WHERE n.nspname = %s AND p.proname = %s
                   )""",
                (schema, name),
            )
            if not bool(cursor.fetchone()[0]):
                raise FinalPersistenceAuthorityQualificationError(f"missing expected function: {qualified}")
        return True

    def _verify_account_authority_empty_reads(self) -> bool:
        from backend.auth.persistence.postgresql_account_authority import PostgreSQLAccountAuthority

        authority = PostgreSQLAccountAuthority(self.pool)
        probes = (
            authority.principal_by_username("__p006_ui_10_2_g_absent__"),
            authority.active_password_verifier("__p006_ui_10_2_g_absent__"),
            authority.primary_email("__p006_ui_10_2_g_absent__"),
            authority.developer_setup_by_lookup_key("__p006_ui_10_2_g_absent__"),
            authority.enigma_catalogue_entry(
                profile_id="__p006_ui_10_2_g_absent__",
                word_length=3, day_of_month=1, period="Morning",
            ),
        )
        if any(value is not None for value in probes):
            raise FinalPersistenceAuthorityQualificationError(
                "A PostgreSQLAccountAuthority zero-state runtime read proof failed"
            )
        return True

    @staticmethod
    def _assert_regex_correction(cursor: Any) -> bool:
        cursor.execute(
            """
            SELECT pg_get_constraintdef(c.oid, TRUE)
            FROM pg_constraint AS c
            JOIN pg_class AS t ON t.oid = c.conrelid
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            WHERE n.nspname = 'nexilabs_auth'
              AND t.relname = 'audit_export'
              AND c.conname = 'ck_nexilabs_auth_audit_export_filter_reference'
            """
        )
        row = cursor.fetchone()
        if not row:
            raise FinalPersistenceAuthorityQualificationError(
                "sequence-36 audit filter constraint is missing"
            )
        definition = str(row[0])
        if "{0,1966}" in definition:
            raise FinalPersistenceAuthorityQualificationError(
                "sequence-35 oversized PostgreSQL regex repetition remains active"
            )
        if "A-Za-z0-9._:/=-]*" not in definition or "2048" not in definition:
            raise FinalPersistenceAuthorityQualificationError(
                "sequence-36 PostgreSQL-safe audit filter constraint is not proven"
            )
        return True

    def _inspect_parent_database(
        self,
        *,
        manifest_rows: tuple[dict[str, object], ...],
        expected_database: str,
        expected_auth_tables: tuple[str, ...],
    ) -> dict[str, object]:
        with self.pool.connection(read_only=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database()")
                database_name = str(cursor.fetchone()[0])
                if database_name != expected_database:
                    raise FinalPersistenceAuthorityQualificationError(
                        f"wrong database target: expected {expected_database}, got {database_name}"
                    )
                cursor.execute(
                    "SELECT COALESCE((SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()), FALSE)"
                )
                tls_active = bool(cursor.fetchone()[0])
                if not tls_active:
                    raise FinalPersistenceAuthorityQualificationError("PostgreSQL TLS is not active")
                cursor.execute(
                    """
                    SELECT migration_id, sequence_number, checksum_sha256, status
                    FROM platform.schema_migration ORDER BY sequence_number
                    """
                )
                ledger_rows = list(cursor.fetchall())
                self._assert_ledger(manifest_rows, ledger_rows)

                cursor.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'nexilabs_auth' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
                auth_tables = tuple(str(row[0]) for row in cursor.fetchall())
                if auth_tables != tuple(sorted(expected_auth_tables)):
                    raise FinalPersistenceAuthorityQualificationError(
                        "final nexilabs_auth base-table set differs from the completed A-F authority"
                    )
                manifest_objects_proven = self._verify_manifest_structural_objects(cursor, manifest_rows)
                public_counts = self._public_privilege_counts(cursor)
                operational_counts = self._operational_counts(cursor)

                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.enigma_catalogue")
                catalogue_count = int(cursor.fetchone()[0])
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.enigma_catalogue_entry")
                catalogue_entry_count = int(cursor.fetchone()[0])
                if catalogue_count != 3 or catalogue_entry_count != 279:
                    raise FinalPersistenceAuthorityQualificationError(
                        "B catalogue closure counts must remain exactly 3 catalogues / 279 entries"
                    )
                cursor.execute(
                    """
                    SELECT word_length FROM nexilabs_auth.enigma_catalogue
                    WHERE catalogue_state = 'ACTIVE'
                    ORDER BY word_length
                    """
                )
                active_lengths = tuple(int(row[0]) for row in cursor.fetchall())
                if active_lengths != (3, 4, 5):
                    raise FinalPersistenceAuthorityQualificationError(
                        "B active catalogue invariant must be exactly word lengths 3/4/5"
                    )
                regex_proven = self._assert_regex_correction(cursor)

        return {
            "database_name": database_name,
            "tls_active": tls_active,
            "ledger_rows": ledger_rows,
            "auth_tables": auth_tables,
            "public_counts": public_counts,
            "operational_counts": operational_counts,
            "catalogue_count": catalogue_count,
            "catalogue_entry_count": catalogue_entry_count,
            "active_lengths": active_lengths,
            "regex_proven": regex_proven,
            "manifest_objects_proven": manifest_objects_proven,
        }

    def verify(
        self,
        *,
        repository_root: Path,
        expected_database: str = "npp_dev",
        require_source_lock: bool = True,
    ) -> FinalPersistenceAuthorityQualificationReport:
        root = Path(repository_root).resolve()
        manifest_rows, manifest_sha = self.verify_repository_artifacts(root)

        if require_source_lock:
            source_commit, source_branch, source_tag_commit = self.verify_source_lock(root)
        else:
            source_commit = G_PREDECESSOR_COMMIT
            source_branch = "main"
            source_tag_commit = G_PREDECESSOR_COMMIT

        # Reuse F's final A-F structural/ledger/ACL qualification rather than
        # recreating each predecessor qualifier. G adds the exact-tail-36 and
        # unconditional zero-authority closure that F intentionally did not own.
        from backend.auth.enrollment_notification_audit_persistence.qualification import (
            POST_F_AUTH_TABLES,
            PostgreSQLEnrollmentNotificationAuditQualification,
        )

        predecessor = PostgreSQLEnrollmentNotificationAuditQualification(self.pool).verify(
            repository_root=root,
            expected_database=expected_database,
        )

        # Reuse B's locked source qualification and read-back parity algorithm,
        # but not B's migration-31-era preflight (which correctly expects only
        # the original 12-table authority and is therefore historical now).
        from backend.auth.enigma_catalogue_admission.postgresql import (
            PostgreSQLEnigmaCatalogueAdmission,
        )
        from backend.auth.enigma_catalogue_admission.source import (
            DEFAULT_SOURCE_SPECS,
            qualify_all_sources,
        )

        sources = qualify_all_sources(root, DEFAULT_SOURCE_SPECS)
        read_back = PostgreSQLEnigmaCatalogueAdmission(self.pool).verify_read_back(sources)
        if not read_back.exact_parity or read_back.catalogue_count != 3 or read_back.entry_count != 279:
            raise FinalPersistenceAuthorityQualificationError(
                "B governed Enigma catalogue read-back parity is not exact"
            )

        parent = self._inspect_parent_database(
            manifest_rows=manifest_rows,
            expected_database=expected_database,
            expected_auth_tables=tuple(POST_F_AUTH_TABLES),
        )
        account_authority_empty_read_proven = self._verify_account_authority_empty_reads()

        # Cross-check predecessor evidence against the parent re-read so G is
        # not merely trusting a single adapter/report surface.
        if predecessor.database_name != parent["database_name"] or not predecessor.tls_active:
            raise FinalPersistenceAuthorityQualificationError(
                "A-F predecessor qualification disagrees with G database target/TLS proof"
            )
        if predecessor.public_schema_privilege_count != 0 or (
            predecessor.public_table_privilege_count != 0
            or predecessor.public_routine_privilege_count != 0
        ):
            raise FinalPersistenceAuthorityQualificationError(
                "A-F predecessor qualification reports PUBLIC privilege exposure"
            )
        if predecessor.enigma_catalogue_count != 3 or predecessor.enigma_catalogue_entry_count != 279:
            raise FinalPersistenceAuthorityQualificationError(
                "A-F predecessor qualification disagrees with B catalogue closure counts"
            )

        enigma_evidence = tuple(
            EnigmaCatalogueClosureEvidence(
                catalogue_id=source.spec.catalogue_id,
                word_length=source.spec.word_length,
                catalogue_version=source.spec.catalogue_version,
                source_reference=source.spec.source_reference,
                source_sha256=source.sha256,
                byte_size=source.byte_size,
                row_count=source.row_count,
            )
            for source in sources
        )

        ledger_rows = parent["ledger_rows"]
        public_counts = parent["public_counts"]
        return FinalPersistenceAuthorityQualificationReport(
            source_commit=source_commit,
            source_branch=source_branch,
            source_tag=G_PREDECESSOR_TAG,
            source_tag_commit=source_tag_commit,
            database_name=str(parent["database_name"]),
            tls_active=bool(parent["tls_active"]),
            manifest_sha256=manifest_sha,
            repository_migration_count=len(manifest_rows),
            database_migration_count=len(ledger_rows),
            migration_tail_sequence=int(ledger_rows[-1][1]),
            migration_tail_id=str(ledger_rows[-1][0]),
            nexilabs_auth_tables=tuple(parent["auth_tables"]),
            public_schema_privilege_count=int(public_counts[0]),
            public_table_privilege_count=int(public_counts[1]),
            public_routine_privilege_count=int(public_counts[2]),
            operational_counts=tuple(parent["operational_counts"]),
            enigma_catalogue_count=int(parent["catalogue_count"]),
            enigma_catalogue_entry_count=int(parent["catalogue_entry_count"]),
            active_catalogue_word_lengths=tuple(parent["active_lengths"]),
            enigma_catalogues=enigma_evidence,
            predecessor_a_f_qualified=True,
            enigma_read_back_exact=True,
            audit_filter_regex_correction_proven=bool(parent["regex_proven"]),
            manifest_structural_objects_proven=bool(parent["manifest_objects_proven"]),
            account_authority_empty_read_proven=account_authority_empty_read_proven,
            closure_qualified=True,
        )


__all__ = [
    "G_CATALOGUE_VERSION",
    "G_MIGRATION_COUNT",
    "G_MILESTONE",
    "G_PREDECESSOR_COMMIT",
    "G_PREDECESSOR_TAG",
    "G_TAG",
    "G_TAIL_ID",
    "G_TAIL_SEQUENCE",
    "OPERATIONAL_TABLES",
    "P006_10_2_CHAIN",
    "PARENT_CLOSURE_TAG",
    "FinalPersistenceAuthorityQualification",
]
