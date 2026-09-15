"""P006.UI.10.2.G — final persistence-authority closure contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class FinalPersistenceAuthorityQualificationError(RuntimeError):
    """Raised when the final P006.UI.10.2 persistence closure cannot be proven."""


@dataclass(frozen=True, slots=True)
class EnigmaCatalogueClosureEvidence:
    catalogue_id: str
    word_length: int
    catalogue_version: int
    source_reference: str
    source_sha256: str
    byte_size: int
    row_count: int

    def safe_summary(self) -> dict[str, object]:
        return {
            "catalogueId": self.catalogue_id,
            "wordLength": self.word_length,
            "catalogueVersion": self.catalogue_version,
            "sourceReference": self.source_reference,
            "sourceSha256": self.source_sha256,
            "byteSize": self.byte_size,
            "rowCount": self.row_count,
        }


@dataclass(frozen=True, slots=True)
class FinalPersistenceAuthorityQualificationReport:
    source_commit: str
    source_branch: str
    source_tag: str
    source_tag_commit: str
    database_name: str
    tls_active: bool
    manifest_sha256: str
    repository_migration_count: int
    database_migration_count: int
    migration_tail_sequence: int
    migration_tail_id: str
    nexilabs_auth_tables: tuple[str, ...]
    public_schema_privilege_count: int
    public_table_privilege_count: int
    public_routine_privilege_count: int
    operational_counts: tuple[tuple[str, int], ...]
    enigma_catalogue_count: int
    enigma_catalogue_entry_count: int
    active_catalogue_word_lengths: tuple[int, ...]
    enigma_catalogues: tuple[EnigmaCatalogueClosureEvidence, ...]
    predecessor_a_f_qualified: bool
    enigma_read_back_exact: bool
    audit_filter_regex_correction_proven: bool
    manifest_structural_objects_proven: bool
    account_authority_empty_read_proven: bool
    closure_qualified: bool

    def operational_count_map(self) -> Mapping[str, int]:
        return dict(self.operational_counts)

    def safe_summary(self) -> dict[str, object]:
        return {
            "sourceCommit": self.source_commit,
            "sourceBranch": self.source_branch,
            "sourceTag": self.source_tag,
            "sourceTagCommit": self.source_tag_commit,
            "databaseName": self.database_name,
            "tlsActive": self.tls_active,
            "manifestSha256": self.manifest_sha256,
            "repositoryMigrationCount": self.repository_migration_count,
            "databaseMigrationCount": self.database_migration_count,
            "migrationTailSequence": self.migration_tail_sequence,
            "migrationTailId": self.migration_tail_id,
            "nexilabsAuthTables": list(self.nexilabs_auth_tables),
            "publicSchemaPrivilegeCount": self.public_schema_privilege_count,
            "publicTablePrivilegeCount": self.public_table_privilege_count,
            "publicRoutinePrivilegeCount": self.public_routine_privilege_count,
            "operationalCounts": dict(self.operational_counts),
            "enigmaCatalogueCount": self.enigma_catalogue_count,
            "enigmaCatalogueEntryCount": self.enigma_catalogue_entry_count,
            "activeCatalogueWordLengths": list(self.active_catalogue_word_lengths),
            "enigmaCatalogues": [item.safe_summary() for item in self.enigma_catalogues],
            "predecessorAFQualified": self.predecessor_a_f_qualified,
            "enigmaReadBackExact": self.enigma_read_back_exact,
            "auditFilterRegexCorrectionProven": self.audit_filter_regex_correction_proven,
            "manifestStructuralObjectsProven": self.manifest_structural_objects_proven,
            "accountAuthorityEmptyReadProven": self.account_authority_empty_read_proven,
            "closureQualified": self.closure_qualified,
        }


__all__ = [
    "EnigmaCatalogueClosureEvidence",
    "FinalPersistenceAuthorityQualificationError",
    "FinalPersistenceAuthorityQualificationReport",
]
