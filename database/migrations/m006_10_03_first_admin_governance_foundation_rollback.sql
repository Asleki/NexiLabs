BEGIN;

-- P006.UI.10.3.A rollback. This rollback is valid only before operational
-- .10.3 authority rows are admitted. The migration runner/operator must verify
-- the target is safe before authorizing rollback.

DROP TRIGGER IF EXISTS tr_nexilabs_auth_authority_audit_event_no_truncate
    ON nexilabs_auth.authority_audit_event;
DROP TRIGGER IF EXISTS tr_nexilabs_auth_authority_audit_event_immutable
    ON nexilabs_auth.authority_audit_event;
DROP FUNCTION IF EXISTS nexilabs_auth.reject_authority_audit_event_truncate();
DROP FUNCTION IF EXISTS nexilabs_auth.reject_authority_audit_event_mutation();
DROP TABLE IF EXISTS nexilabs_auth.authority_audit_event;

DROP TRIGGER IF EXISTS tr_nexilabs_auth_enigma_profile_secret_verifier_transition
    ON nexilabs_auth.enigma_profile_secret_verifier;
DROP FUNCTION IF EXISTS nexilabs_auth.validate_enigma_profile_secret_verifier_transition();
DROP TABLE IF EXISTS nexilabs_auth.enigma_profile_secret_verifier;
DROP TRIGGER IF EXISTS tr_nexilabs_auth_admin_developer_id_allocator_transition
    ON nexilabs_auth.admin_developer_id_allocator;
DROP FUNCTION IF EXISTS nexilabs_auth.validate_admin_developer_id_allocator_transition();
DROP FUNCTION IF EXISTS nexilabs_auth.reserve_admin_developer_id();
DROP TABLE IF EXISTS nexilabs_auth.admin_developer_id_allocator;

COMMIT;
