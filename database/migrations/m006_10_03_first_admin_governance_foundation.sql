BEGIN;

-- P006.UI.10.3.A / migration identity M006.10.3
-- First Admin governance foundation.
--
-- This migration creates authority structure only. It intentionally creates no
-- principal, Admin Operator, password verifier, OTP, session, elevation, mail,
-- or user-specific Enigma secret. The first Admin remains an explicitly
-- authorized protected-terminal operation after this migration is qualified.

CREATE TABLE nexilabs_auth.admin_developer_id_allocator (
    allocator_key text PRIMARY KEY,
    id_prefix text NOT NULL,
    sequence_width integer NOT NULL,
    next_sequence bigint NOT NULL,
    format_version integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_nexilabs_auth_admin_id_allocator_key CHECK (
        allocator_key = 'ADMIN_DEVELOPER_ID'
    ),
    CONSTRAINT ck_nexilabs_auth_admin_id_allocator_prefix CHECK (
        id_prefix = 'NEXADEV-ADM-'
    ),
    CONSTRAINT ck_nexilabs_auth_admin_id_allocator_width CHECK (
        sequence_width = 6
    ),
    CONSTRAINT ck_nexilabs_auth_admin_id_allocator_sequence CHECK (
        next_sequence BETWEEN 1 AND 1000000
    ),
    CONSTRAINT ck_nexilabs_auth_admin_id_allocator_version CHECK (
        format_version = 1
    ),
    CONSTRAINT ck_nexilabs_auth_admin_id_allocator_time CHECK (
        updated_at >= created_at
    )
);

-- Structural namespace seed only. This is not an Admin identity or account.
INSERT INTO nexilabs_auth.admin_developer_id_allocator (
    allocator_key, id_prefix, sequence_width, next_sequence, format_version
) VALUES ('ADMIN_DEVELOPER_ID', 'NEXADEV-ADM-', 6, 1, 1);

CREATE FUNCTION nexilabs_auth.reserve_admin_developer_id()
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    reserved_id text;
BEGIN
    UPDATE nexilabs_auth.admin_developer_id_allocator
       SET next_sequence = next_sequence + 1,
           updated_at = CURRENT_TIMESTAMP
     WHERE allocator_key = 'ADMIN_DEVELOPER_ID'
       AND next_sequence < 1000000
    RETURNING id_prefix || lpad((next_sequence - 1)::text, sequence_width, '0')
         INTO reserved_id;

    IF reserved_id IS NULL THEN
        RAISE EXCEPTION USING
            ERRCODE = '22003',
            MESSAGE = 'Admin Developer ID namespace exhausted';
    END IF;

    RETURN reserved_id;
END;
$$;

CREATE FUNCTION nexilabs_auth.validate_admin_developer_id_allocator_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING
            ERRCODE = '55000',
            MESSAGE = 'Admin Developer ID allocator authority cannot be deleted';
    END IF;

    IF NEW.allocator_key IS DISTINCT FROM OLD.allocator_key
       OR NEW.id_prefix IS DISTINCT FROM OLD.id_prefix
       OR NEW.sequence_width IS DISTINCT FROM OLD.sequence_width
       OR NEW.format_version IS DISTINCT FROM OLD.format_version
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION USING
            ERRCODE = '23514',
            MESSAGE = 'Admin Developer ID allocator identity and format are immutable';
    END IF;

    IF NEW.next_sequence <> OLD.next_sequence + 1
       OR NEW.updated_at < OLD.updated_at THEN
        RAISE EXCEPTION USING
            ERRCODE = '23514',
            MESSAGE = 'Admin Developer ID allocator may advance by exactly one only';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER tr_nexilabs_auth_admin_developer_id_allocator_transition
BEFORE UPDATE OR DELETE
ON nexilabs_auth.admin_developer_id_allocator
FOR EACH ROW
EXECUTE FUNCTION nexilabs_auth.validate_admin_developer_id_allocator_transition();

COMMENT ON TABLE nexilabs_auth.admin_developer_id_allocator IS
    'Governed monotonic allocator for Admin-designated NexaDevs Developer IDs. The visible prefix conveys no authorization.';
COMMENT ON FUNCTION nexilabs_auth.reserve_admin_developer_id() IS
    'Transaction-scoped allocation of the next NEXADEV-ADM-###### identifier; rolled-back transactions do not consume the identifier.';

CREATE TABLE nexilabs_auth.enigma_profile_secret_verifier (
    secret_verifier_id text PRIMARY KEY,
    profile_id text NOT NULL
        REFERENCES nexilabs_auth.enigma_profile(profile_id),
    verifier_scheme text NOT NULL,
    verifier_version integer NOT NULL DEFAULT 1,
    verifier_payload text NOT NULL,
    secret_state text NOT NULL DEFAULT 'ACTIVE',
    policy_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at timestamptz NULL,
    CONSTRAINT ck_nexilabs_auth_enigma_secret_verifier_id CHECK (
        length(btrim(secret_verifier_id)) BETWEEN 1 AND 255
    ),
    CONSTRAINT ck_nexilabs_auth_enigma_secret_verifier_scheme CHECK (
        length(btrim(verifier_scheme)) BETWEEN 1 AND 80
        AND lower(btrim(verifier_scheme)) NOT IN (
            'raw', 'plaintext', 'cleartext', 'reversible'
        )
    ),
    CONSTRAINT ck_nexilabs_auth_enigma_secret_verifier_version CHECK (
        verifier_version > 0
    ),
    CONSTRAINT ck_nexilabs_auth_enigma_secret_verifier_payload CHECK (
        length(verifier_payload) BETWEEN 20 AND 4096
    ),
    CONSTRAINT ck_nexilabs_auth_enigma_secret_state CHECK (
        secret_state IN ('ACTIVE', 'RETIRED', 'REVOKED')
    ),
    CONSTRAINT ck_nexilabs_auth_enigma_secret_policy CHECK (
        length(btrim(policy_version)) BETWEEN 1 AND 255
    ),
    CONSTRAINT ck_nexilabs_auth_enigma_secret_state_time CHECK (
        (secret_state = 'ACTIVE' AND ended_at IS NULL)
        OR (secret_state IN ('RETIRED', 'REVOKED') AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX ux_nexilabs_auth_active_enigma_profile_secret
    ON nexilabs_auth.enigma_profile_secret_verifier (profile_id)
    WHERE secret_state = 'ACTIVE';
CREATE INDEX ix_nexilabs_auth_enigma_profile_secret_state
    ON nexilabs_auth.enigma_profile_secret_verifier (profile_id, secret_state, created_at DESC);

CREATE FUNCTION nexilabs_auth.validate_enigma_profile_secret_verifier_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING
            ERRCODE = '55000',
            MESSAGE = 'Enigma profile secret verifier history cannot be deleted';
    END IF;

    IF OLD.secret_state <> 'ACTIVE' THEN
        RAISE EXCEPTION USING
            ERRCODE = '23514',
            MESSAGE = 'terminal Enigma profile secret verifier rows are immutable';
    END IF;

    IF NEW.secret_verifier_id IS DISTINCT FROM OLD.secret_verifier_id
       OR NEW.profile_id IS DISTINCT FROM OLD.profile_id
       OR NEW.verifier_scheme IS DISTINCT FROM OLD.verifier_scheme
       OR NEW.verifier_version IS DISTINCT FROM OLD.verifier_version
       OR NEW.verifier_payload IS DISTINCT FROM OLD.verifier_payload
       OR NEW.policy_version IS DISTINCT FROM OLD.policy_version
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION USING
            ERRCODE = '23514',
            MESSAGE = 'Enigma profile secret verifier identity and verifier material are immutable';
    END IF;

    IF NEW.secret_state NOT IN ('RETIRED', 'REVOKED')
       OR NEW.ended_at IS NULL
       OR NEW.ended_at < OLD.created_at THEN
        RAISE EXCEPTION USING
            ERRCODE = '23514',
            MESSAGE = 'active Enigma profile secret verifier may only retire or revoke with an end time';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER tr_nexilabs_auth_enigma_profile_secret_verifier_transition
BEFORE UPDATE OR DELETE
ON nexilabs_auth.enigma_profile_secret_verifier
FOR EACH ROW
EXECUTE FUNCTION nexilabs_auth.validate_enigma_profile_secret_verifier_transition();

COMMENT ON TABLE nexilabs_auth.enigma_profile_secret_verifier IS
    'Profile-specific opaque verifier authority used with shared PostgreSQL Enigma catalogues. Raw profile secrets are never persisted.';
COMMENT ON COLUMN nexilabs_auth.enigma_profile_secret_verifier.verifier_payload IS
    'Opaque one-way verifier only; never the raw profile secret or development CSV profile_lookup_word.';

CREATE TABLE nexilabs_auth.authority_audit_event (
    audit_event_id text PRIMARY KEY,
    event_sequence bigint GENERATED ALWAYS AS IDENTITY,
    event_type text NOT NULL,
    runtime_mode text NOT NULL,
    actor_type text NOT NULL,
    actor_principal_id text NULL
        REFERENCES nexilabs_auth.principal_account(principal_id),
    actor_admin_operator_id text NULL,
    subject_type text NOT NULL,
    subject_id text NOT NULL,
    outcome text NOT NULL,
    permission_code text NULL,
    policy_version text NOT NULL,
    source_reference text NOT NULL,
    correlation_id text NOT NULL,
    causation_event_id text NULL
        REFERENCES nexilabs_auth.authority_audit_event(audit_event_id),
    receipt_reference text NOT NULL,
    receipt_sha256 text NOT NULL,
    provider_reference text NULL,
    occurred_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_nexilabs_auth_authority_audit_admin_operator
        FOREIGN KEY (actor_admin_operator_id, actor_principal_id)
        REFERENCES nexilabs_auth.admin_operator(admin_operator_id, principal_id),
    CONSTRAINT ck_nexilabs_auth_authority_audit_id CHECK (
        length(btrim(audit_event_id)) BETWEEN 1 AND 255
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_event_type CHECK (
        length(btrim(event_type)) BETWEEN 1 AND 160
        AND event_type = upper(event_type)
        AND event_type ~ '^[A-Z0-9_]+$'
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_runtime CHECK (
        runtime_mode IN ('production', 'simulation')
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_actor CHECK (
        actor_type IN ('BOOTSTRAP_TERMINAL', 'PRINCIPAL', 'ADMIN_OPERATOR', 'SYSTEM')
        AND (actor_type <> 'PRINCIPAL' OR actor_principal_id IS NOT NULL)
        AND (actor_type <> 'ADMIN_OPERATOR' OR (
            actor_principal_id IS NOT NULL AND actor_admin_operator_id IS NOT NULL
        ))
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_subject_type CHECK (
        length(btrim(subject_type)) BETWEEN 1 AND 160
        AND subject_type = upper(subject_type)
        AND subject_type ~ '^[A-Z0-9_]+$'
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_subject_id CHECK (
        length(btrim(subject_id)) BETWEEN 1 AND 512
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_outcome CHECK (
        outcome IN ('STARTED', 'ISSUED', 'SENT', 'VERIFIED', 'SUCCEEDED', 'DENIED', 'FAILED', 'EXPIRED', 'REVOKED')
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_permission CHECK (
        permission_code IS NULL
        OR length(btrim(permission_code)) BETWEEN 1 AND 255
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_policy CHECK (
        length(btrim(policy_version)) BETWEEN 1 AND 255
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_source CHECK (
        length(btrim(source_reference)) BETWEEN 1 AND 1024
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_correlation CHECK (
        length(btrim(correlation_id)) BETWEEN 1 AND 255
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_causation CHECK (
        causation_event_id IS NULL OR causation_event_id <> audit_event_id
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_receipt_reference CHECK (
        length(btrim(receipt_reference)) BETWEEN 1 AND 1024
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_receipt_sha256 CHECK (
        receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_nexilabs_auth_authority_audit_provider_reference CHECK (
        provider_reference IS NULL
        OR length(btrim(provider_reference)) BETWEEN 1 AND 1024
    )
);

CREATE UNIQUE INDEX ux_nexilabs_auth_authority_audit_sequence
    ON nexilabs_auth.authority_audit_event (event_sequence);
CREATE INDEX ix_nexilabs_auth_authority_audit_type_time
    ON nexilabs_auth.authority_audit_event (event_type, occurred_at DESC);
CREATE INDEX ix_nexilabs_auth_authority_audit_actor
    ON nexilabs_auth.authority_audit_event (actor_principal_id, actor_admin_operator_id, occurred_at DESC);
CREATE INDEX ix_nexilabs_auth_authority_audit_subject
    ON nexilabs_auth.authority_audit_event (subject_type, subject_id, occurred_at DESC);
CREATE INDEX ix_nexilabs_auth_authority_audit_correlation
    ON nexilabs_auth.authority_audit_event (correlation_id, occurred_at);

CREATE FUNCTION nexilabs_auth.reject_authority_audit_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = '55000',
        MESSAGE = 'authority audit events are immutable append-only authority';
END;
$$;

CREATE TRIGGER tr_nexilabs_auth_authority_audit_event_immutable
BEFORE UPDATE OR DELETE
ON nexilabs_auth.authority_audit_event
FOR EACH ROW
EXECUTE FUNCTION nexilabs_auth.reject_authority_audit_event_mutation();

CREATE FUNCTION nexilabs_auth.reject_authority_audit_event_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = '55000',
        MESSAGE = 'authority audit history cannot be truncated';
END;
$$;

CREATE TRIGGER tr_nexilabs_auth_authority_audit_event_no_truncate
BEFORE TRUNCATE
ON nexilabs_auth.authority_audit_event
FOR EACH STATEMENT
EXECUTE FUNCTION nexilabs_auth.reject_authority_audit_event_truncate();

COMMENT ON TABLE nexilabs_auth.authority_audit_event IS
    'Immutable cross-cutting authentication and governance audit authority. Stores references and receipt hashes, never secret payloads.';
COMMENT ON COLUMN nexilabs_auth.authority_audit_event.receipt_sha256 IS
    'SHA-256 of canonical non-secret receipt evidence generated for the event.';

REVOKE ALL ON TABLE nexilabs_auth.admin_developer_id_allocator FROM PUBLIC;
REVOKE ALL ON TABLE nexilabs_auth.enigma_profile_secret_verifier FROM PUBLIC;
REVOKE ALL ON TABLE nexilabs_auth.authority_audit_event FROM PUBLIC;
REVOKE ALL ON FUNCTION nexilabs_auth.reserve_admin_developer_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION nexilabs_auth.validate_admin_developer_id_allocator_transition() FROM PUBLIC;
REVOKE ALL ON FUNCTION nexilabs_auth.validate_enigma_profile_secret_verifier_transition() FROM PUBLIC;
REVOKE ALL ON FUNCTION nexilabs_auth.reject_authority_audit_event_mutation() FROM PUBLIC;
REVOKE ALL ON FUNCTION nexilabs_auth.reject_authority_audit_event_truncate() FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA nexilabs_auth FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA nexilabs_auth FROM PUBLIC;

COMMIT;
