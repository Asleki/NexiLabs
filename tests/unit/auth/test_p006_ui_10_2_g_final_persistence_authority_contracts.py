from backend.auth.final_persistence_authority_qualification.contracts import (
    EnigmaCatalogueClosureEvidence,
    FinalPersistenceAuthorityQualificationReport,
)


def test_safe_summary_is_closure_evidence_only():
    evidence = EnigmaCatalogueClosureEvidence(
        catalogue_id="enigma:catalogue:shared:3:v1",
        word_length=3,
        catalogue_version=1,
        source_reference="development/auth/private/enigma/enigma_words_3.csv",
        source_sha256="a" * 64,
        byte_size=123,
        row_count=93,
    )
    report = FinalPersistenceAuthorityQualificationReport(
        source_commit="c" * 40,
        source_branch="main",
        source_tag="P006.UI.10.2.F-tag",
        source_tag_commit="c" * 40,
        database_name="npp_dev",
        tls_active=True,
        manifest_sha256="b" * 64,
        repository_migration_count=36,
        database_migration_count=36,
        migration_tail_sequence=36,
        migration_tail_id="m006_10_02_enrollment_notification_audit_filter_regex_correction",
        nexilabs_auth_tables=("principal_account",),
        public_schema_privilege_count=0,
        public_table_privilege_count=0,
        public_routine_privilege_count=0,
        operational_counts=(("principal_account", 0),),
        enigma_catalogue_count=3,
        enigma_catalogue_entry_count=279,
        active_catalogue_word_lengths=(3, 4, 5),
        enigma_catalogues=(evidence,),
        predecessor_a_f_qualified=True,
        enigma_read_back_exact=True,
        audit_filter_regex_correction_proven=True,
        manifest_structural_objects_proven=True,
        account_authority_empty_read_proven=True,
        closure_qualified=True,
    )
    summary = report.safe_summary()
    assert summary["closureQualified"] is True
    assert summary["operationalCounts"] == {"principal_account": 0}
    assert summary["enigmaCatalogues"][0]["sourceSha256"] == "a" * 64
    assert summary["manifestStructuralObjectsProven"] is True
    assert summary["accountAuthorityEmptyReadProven"] is True
    text = repr(summary).lower()
    for forbidden in ("password", "raw otp", "download token", "enigma response"):
        assert forbidden not in text
