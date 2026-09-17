"""PostgreSQL authority adapter for P006.UI.10.3.

All writes are server-side and operate only on the governed ``nexilabs_auth``
schema. Secrets supplied by callers are already transformed into opaque verifier
payloads before reaching this adapter.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Full, LifoQueue
import secrets
from threading import Lock
from typing import Callable, Iterator

from .contracts import (
    ADMIN_PERMISSION_CODES,
    AUDIT_POLICY_VERSION,
    BOOTSTRAP_POLICY_VERSION,
    ENIGMA_POLICY_VERSION,
    OTP_MAX_ATTEMPTS,
    OTP_MAX_RESENDS,
    OTP_RESEND_COOLDOWN_SECONDS,
    OTP_POLICY_VERSION,
    AuditEventType,
    AuditOutcome,
    BootstrapIdentityInput,
    BootstrapReceipt,
    BootstrapRejected,
    PendingBootstrap,
    SOURCE_LOCK_COMMIT,
)
from .security import normalize_email, receipt_sha256


ConnectFactory = Callable[[], object]
ConnectionCheck = Callable[[object], None]


class PostgreSQLConnectionPool:
    """Small thread-safe pool for the local Production authentication authority.

    P006.UI.10.3 runs a threaded HTTP server against a remote PostgreSQL
    authority. Opening a new TLS/RDS connection for every repository method
    makes a single authentication flow pay connection setup repeatedly. This
    pool keeps a bounded set of physical connections alive while preserving the
    repository's existing per-method transaction boundaries.
    """

    def __init__(
        self,
        connect: ConnectFactory,
        *,
        min_size: int = 1,
        max_size: int = 4,
        acquire_timeout_seconds: float = 15.0,
        check: ConnectionCheck | None = None,
    ):
        min_size = int(min_size)
        max_size = int(max_size)
        if min_size < 0 or max_size < 1 or min_size > max_size:
            raise ValueError("invalid PostgreSQL connection-pool size")
        if float(acquire_timeout_seconds) <= 0:
            raise ValueError("PostgreSQL connection-pool acquire timeout must be positive")
        self._connect = connect
        self._min_size = min_size
        self._max_size = max_size
        self._acquire_timeout_seconds = float(acquire_timeout_seconds)
        self._check = check
        self._available: LifoQueue[object] = LifoQueue(maxsize=max_size)
        self._state_lock = Lock()
        self._created = 0
        self._closed = False

    @staticmethod
    def _usable(connection: object) -> bool:
        return not bool(getattr(connection, "closed", False)) and not bool(
            getattr(connection, "broken", False)
        )

    @staticmethod
    def _close_connection(connection: object) -> None:
        try:
            connection.close()
        except Exception:
            pass

    def _reserve_slot(self) -> bool:
        with self._state_lock:
            if self._closed or self._created >= self._max_size:
                return False
            self._created += 1
            return True

    def _drop_slot(self) -> None:
        with self._state_lock:
            self._created = max(0, self._created - 1)

    def _validate(self, connection: object) -> bool:
        if not self._usable(connection):
            return False
        if self._check is None:
            return True
        try:
            self._check(connection)
        except Exception:
            return False
        return self._usable(connection)

    def _new_connection(self) -> object:
        if not self._reserve_slot():
            raise RuntimeError("PostgreSQL connection pool has no free creation slot")
        try:
            connection = self._connect()
        except BaseException:
            self._drop_slot()
            raise
        if not self._validate(connection):
            self._close_connection(connection)
            self._drop_slot()
            raise RuntimeError("PostgreSQL connection validation failed")
        return connection

    def open(self) -> None:
        """Warm the configured minimum number of physical connections."""
        with self._state_lock:
            if self._closed:
                raise RuntimeError("PostgreSQL connection pool is closed")
        created_now: list[object] = []
        try:
            while True:
                with self._state_lock:
                    needed = self._min_size - self._created
                if needed <= 0:
                    break
                created_now.append(self._new_connection())
        except BaseException:
            for connection in created_now:
                self._close_connection(connection)
                self._drop_slot()
            raise
        for connection in created_now:
            self._available.put_nowait(connection)

    def _acquire(self) -> object:
        with self._state_lock:
            if self._closed:
                raise RuntimeError("PostgreSQL connection pool is closed")

        while True:
            try:
                connection = self._available.get_nowait()
            except Empty:
                connection = None

            if connection is not None:
                if self._validate(connection):
                    return connection
                self._close_connection(connection)
                self._drop_slot()
                continue

            if self._reserve_slot():
                try:
                    connection = self._connect()
                except BaseException:
                    self._drop_slot()
                    raise
                if self._validate(connection):
                    return connection
                self._close_connection(connection)
                self._drop_slot()
                raise RuntimeError("PostgreSQL connection validation failed")

            try:
                connection = self._available.get(timeout=self._acquire_timeout_seconds)
            except Empty as exc:
                raise TimeoutError("PostgreSQL connection pool acquisition timed out") from exc
            if self._validate(connection):
                return connection
            self._close_connection(connection)
            self._drop_slot()

    def _release(self, connection: object, *, discard: bool = False) -> None:
        with self._state_lock:
            closed = self._closed
        if discard or closed or not self._usable(connection):
            self._close_connection(connection)
            self._drop_slot()
            return
        try:
            self._available.put_nowait(connection)
        except Full:
            self._close_connection(connection)
            self._drop_slot()

    @contextmanager
    def connection(self) -> Iterator[object]:
        """Lease one connection and preserve ``with connection`` transactions.

        Successful repository calls commit before the connection is returned.
        Failed calls roll back. A connection is discarded only when it cannot be
        rolled back/committed safely or PostgreSQL reports it closed/broken.
        """
        connection = self._acquire()
        try:
            yield connection
        except BaseException:
            discard = not self._usable(connection)
            try:
                connection.rollback()
            except Exception:
                discard = True
            self._release(connection, discard=discard)
            raise
        else:
            try:
                connection.commit()
            except BaseException:
                try:
                    connection.rollback()
                except Exception:
                    pass
                self._release(connection, discard=True)
                raise
            self._release(connection)

    def close(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
        while True:
            try:
                connection = self._available.get_nowait()
            except Empty:
                break
            self._close_connection(connection)
            self._drop_slot()

    @property
    def created_connection_count(self) -> int:
        with self._state_lock:
            return self._created


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    host: str
    port: int
    database_name: str
    username: str
    password: str
    ssl_mode: str = "require"

    def __post_init__(self) -> None:
        if not self.host.strip() or not self.database_name.strip() or not self.username.strip() or not self.password:
            raise ValueError("PostgreSQL host/database/user/password are required")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("PostgreSQL port is invalid")
        if self.ssl_mode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("PostgreSQL ssl_mode is unsafe")

    def safe_summary(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "databaseName": self.database_name,
            "username": self.username,
            "sslMode": self.ssl_mode,
        }


def psycopg_connect_factory(settings: DatabaseSettings) -> ConnectFactory:
    def connect():
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - exercised in real runtime
            raise RuntimeError("psycopg is required for PostgreSQL first-Admin operations") from exc
        return psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database_name,
            user=settings.username,
            password=settings.password,
            sslmode=settings.ssl_mode,
            connect_timeout=10,
        )
    return connect


def psycopg_connection_check(connection: object) -> None:
    """Validate a pooled PostgreSQL connection with one real server round-trip.

    A psycopg connection can still report ``closed=False`` and ``broken=False``
    after an idle RDS/TLS socket has been closed remotely. Running ``SELECT 1``
    in temporary autocommit mode detects that stale socket before repository code
    receives the lease, without leaving a transaction open in the pool.
    """
    previous_autocommit = bool(getattr(connection, "autocommit", False))
    if not previous_autocommit:
        connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if not row or int(row[0]) != 1:
                raise RuntimeError("PostgreSQL connection check returned an invalid result")
    finally:
        if not previous_autocommit:
            try:
                connection.autocommit = False
            except Exception:
                # The pool discards a connection whenever this check raises, so
                # a broken socket does not need to be repaired in place.
                pass


def _id(prefix: str) -> str:
    return f"{prefix}:{secrets.token_urlsafe(18)}"


def _canonical_audit_receipt(
    *,
    audit_event_id: str,
    event_type: str,
    subject_type: str,
    subject_id: str,
    outcome: str,
    correlation_id: str,
    source_reference: str,
) -> tuple[str, str]:
    reference = f"audit-receipt:{audit_event_id}"
    digest = receipt_sha256(
        {
            "auditEventId": audit_event_id,
            "eventType": event_type,
            "subjectType": subject_type,
            "subjectId": subject_id,
            "outcome": outcome,
            "correlationId": correlation_id,
            "sourceReference": source_reference,
            "policyVersion": AUDIT_POLICY_VERSION,
        }
    )
    return reference, digest


class PostgreSQLFirstAdminAuthority:
    def __init__(
        self,
        connect: ConnectFactory,
        *,
        database_name: str,
        close: Callable[[], None] | None = None,
    ):
        self._connect = connect
        self._close = close
        self.database_name = str(database_name)

    def close(self) -> None:
        if self._close is not None:
            close, self._close = self._close, None
            close()

    @staticmethod
    def _append_audit(
        cursor,
        *,
        event_type: str,
        outcome: str,
        actor_type: str,
        subject_type: str,
        subject_id: str,
        correlation_id: str,
        source_reference: str,
        actor_principal_id: str | None = None,
        actor_admin_operator_id: str | None = None,
        permission_code: str | None = None,
        causation_event_id: str | None = None,
        provider_reference: str | None = None,
        audit_event_id: str | None = None,
        receipt_reference: str | None = None,
        receipt_digest: str | None = None,
    ) -> str:
        audit_event_id = audit_event_id or _id("audit-event")
        if not receipt_reference or not receipt_digest:
            receipt_reference, receipt_digest = _canonical_audit_receipt(
                audit_event_id=audit_event_id,
                event_type=event_type,
                subject_type=subject_type,
                subject_id=subject_id,
                outcome=outcome,
                correlation_id=correlation_id,
                source_reference=source_reference,
            )
        cursor.execute(
            """
            INSERT INTO nexilabs_auth.authority_audit_event (
                audit_event_id, event_type, runtime_mode, actor_type,
                actor_principal_id, actor_admin_operator_id,
                subject_type, subject_id, outcome, permission_code,
                policy_version, source_reference, correlation_id,
                causation_event_id, receipt_reference, receipt_sha256,
                provider_reference
            ) VALUES (
                %s, %s, 'production', %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s
            )
            """,
            (
                audit_event_id, event_type, actor_type,
                actor_principal_id, actor_admin_operator_id,
                subject_type, subject_id, outcome, permission_code,
                AUDIT_POLICY_VERSION, source_reference, correlation_id,
                causation_event_id, receipt_reference, receipt_digest,
                provider_reference,
            ),
        )
        return audit_event_id

    def count_admin_operators(self) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.admin_operator")
                return int(cursor.fetchone()[0])

    def prepare_pending_bootstrap(
        self,
        *,
        identity: BootstrapIdentityInput,
        challenge_id: str,
        otp_verifier_payload: str,
        issued_at: datetime,
        expires_at: datetime,
        correlation_id: str,
    ) -> PendingBootstrap:
        username = identity.username.strip()
        username_key = username.casefold()
        email_address = identity.admin_email.strip()
        email_key = normalize_email(email_address)
        source_reference = f"{SOURCE_LOCK_COMMIT}:{BOOTSTRAP_POLICY_VERSION}"

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.admin_operator")
                if int(cursor.fetchone()[0]) != 0:
                    raise BootstrapRejected("first Admin bootstrap is unavailable after an Admin Operator exists")

                cursor.execute(
                    """
                    SELECT pa.principal_id, ae.email_id
                      FROM nexilabs_auth.principal_account AS pa
                      JOIN nexilabs_auth.account_email AS ae
                        ON ae.principal_id = pa.principal_id
                     WHERE pa.username_key = %s
                       AND pa.identity_type = 'nexadevs_developer'
                       AND pa.account_state = 'PENDING'
                       AND ae.email_key = %s
                       AND ae.verification_state <> 'REVOKED'
                     ORDER BY pa.created_at
                     LIMIT 1
                    """,
                    (username_key, email_key),
                )
                existing = cursor.fetchone()
                if existing:
                    principal_id, email_id = str(existing[0]), str(existing[1])
                    cursor.execute(
                        """
                        UPDATE nexilabs_auth.email_verification_challenge
                           SET challenge_state = 'INVALIDATED',
                               invalidated_at = %s
                         WHERE principal_id = %s
                           AND email_id = %s
                           AND challenge_state = 'ISSUED'
                        """,
                        (issued_at, principal_id, email_id),
                    )
                    cursor.execute(
                        """
                        UPDATE nexilabs_auth.account_email
                           SET verification_state = 'PENDING',
                               verification_requested_at = %s,
                               verification_reference = %s
                         WHERE email_id = %s
                        """,
                        (issued_at, challenge_id, email_id),
                    )
                else:
                    cursor.execute(
                        "SELECT 1 FROM nexilabs_auth.principal_account WHERE username_key = %s",
                        (username_key,),
                    )
                    if cursor.fetchone():
                        raise BootstrapRejected("username already belongs to another principal")
                    cursor.execute(
                        "SELECT 1 FROM nexilabs_auth.account_email WHERE email_key = %s",
                        (email_key,),
                    )
                    if cursor.fetchone():
                        raise BootstrapRejected("Admin email already belongs to another principal")

                    principal_id = _id("principal")
                    email_id = _id("email")
                    cursor.execute(
                        """
                        INSERT INTO nexilabs_auth.principal_account (
                            principal_id, username, username_key, identity_type, account_state
                        ) VALUES (%s, %s, %s, 'nexadevs_developer', 'PENDING')
                        """,
                        (principal_id, username, username_key),
                    )
                    cursor.execute(
                        """
                        INSERT INTO nexilabs_auth.principal_profile (
                            principal_id, first_name, last_name
                        ) VALUES (%s, %s, %s)
                        """,
                        (principal_id, identity.first_name.strip(), identity.last_name.strip()),
                    )
                    cursor.execute(
                        """
                        INSERT INTO nexilabs_auth.account_email (
                            email_id, principal_id, email_address, email_key,
                            verification_state, is_primary,
                            verification_requested_at, verification_reference
                        ) VALUES (%s, %s, %s, %s, 'PENDING', TRUE, %s, %s)
                        """,
                        (email_id, principal_id, email_address, email_key, issued_at, challenge_id),
                    )
                    self._append_audit(
                        cursor,
                        event_type=AuditEventType.FIRST_ADMIN_BOOTSTRAP_STARTED.value,
                        outcome=AuditOutcome.STARTED.value,
                        actor_type="BOOTSTRAP_TERMINAL",
                        subject_type="PRINCIPAL",
                        subject_id=principal_id,
                        correlation_id=correlation_id,
                        source_reference=source_reference,
                    )

                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.email_verification_challenge (
                        challenge_id, principal_id, email_id,
                        otp_verifier_scheme, otp_verifier_version, otp_verifier_payload,
                        challenge_state, policy_version, issued_at, expires_at,
                        max_attempts
                    ) VALUES (
                        %s, %s, %s,
                        'HMAC-SHA256', 1, %s,
                        'ISSUED', %s, %s, %s,
                        %s
                    )
                    """,
                    (challenge_id, principal_id, email_id, otp_verifier_payload, OTP_POLICY_VERSION, issued_at, expires_at, OTP_MAX_ATTEMPTS),
                )
                self._append_audit(
                    cursor,
                    event_type=AuditEventType.FIRST_ADMIN_EMAIL_CHALLENGE_ISSUED.value,
                    outcome=AuditOutcome.ISSUED.value,
                    actor_type="BOOTSTRAP_TERMINAL",
                    subject_type="EMAIL_VERIFICATION_CHALLENGE",
                    subject_id=challenge_id,
                    correlation_id=correlation_id,
                    source_reference=source_reference,
                    actor_principal_id=principal_id,
                )
        return PendingBootstrap(
            principal_id=principal_id,
            email_id=email_id,
            challenge_id=challenge_id,
            correlation_id=correlation_id,
            expires_at=expires_at.isoformat(),
        )

    def record_otp_delivery(
        self,
        *,
        pending: PendingBootstrap,
        provider_reference: str | None,
        delivered: bool,
    ) -> None:
        event_type = (
            AuditEventType.FIRST_ADMIN_EMAIL_OTP_SENT.value
            if delivered
            else AuditEventType.FIRST_ADMIN_EMAIL_OTP_DELIVERY_FAILED.value
        )
        outcome = AuditOutcome.SENT.value if delivered else AuditOutcome.FAILED.value
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._append_audit(
                    cursor,
                    event_type=event_type,
                    outcome=outcome,
                    actor_type="SYSTEM",
                    actor_principal_id=pending.principal_id,
                    subject_type="EMAIL_VERIFICATION_CHALLENGE",
                    subject_id=pending.challenge_id,
                    correlation_id=pending.correlation_id,
                    source_reference=f"{SOURCE_LOCK_COMMIT}:{BOOTSTRAP_POLICY_VERSION}",
                    provider_reference=provider_reference,
                )

    def email_for_pending(self, pending: PendingBootstrap) -> str:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT email_address
                      FROM nexilabs_auth.account_email
                     WHERE email_id = %s AND principal_id = %s
                    """,
                    (pending.email_id, pending.principal_id),
                )
                row = cursor.fetchone()
                if not row:
                    raise BootstrapRejected("pending Admin email no longer exists")
                return str(row[0])

    def resend_email_challenge(
        self,
        *,
        pending: PendingBootstrap,
        otp_verifier_payload: str,
        now: datetime,
        expires_at: datetime,
    ) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT challenge_state, resend_count, last_resend_at
                      FROM nexilabs_auth.email_verification_challenge
                     WHERE challenge_id = %s
                     FOR UPDATE
                    """,
                    (pending.challenge_id,),
                )
                row = cursor.fetchone()
                if not row or str(row[0]) != "ISSUED":
                    raise BootstrapRejected("email verification challenge is not issued")
                resend_count = int(row[1])
                if resend_count >= OTP_MAX_RESENDS:
                    raise BootstrapRejected("email verification resend limit reached")
                last_resend_at = row[2]
                if last_resend_at is not None and (now - last_resend_at).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
                    raise BootstrapRejected("email verification resend cooldown is active")
                cursor.execute(
                    """
                    UPDATE nexilabs_auth.email_verification_challenge
                       SET otp_verifier_payload = %s,
                           otp_verifier_scheme = 'HMAC-SHA256',
                           otp_verifier_version = 1,
                           expires_at = %s,
                           resend_count = resend_count + 1,
                           last_resend_at = %s
                     WHERE challenge_id = %s
                    RETURNING resend_count
                    """,
                    (otp_verifier_payload, expires_at, now, pending.challenge_id),
                )
                return int(cursor.fetchone()[0])

    def verify_email_challenge(
        self,
        *,
        pending: PendingBootstrap,
        otp: str,
        verifier: Callable[[str], bool],
        now: datetime,
    ) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT otp_verifier_payload, challenge_state, expires_at,
                           attempt_count, max_attempts
                      FROM nexilabs_auth.email_verification_challenge
                     WHERE challenge_id = %s
                       AND principal_id = %s
                       AND email_id = %s
                     FOR UPDATE
                    """,
                    (pending.challenge_id, pending.principal_id, pending.email_id),
                )
                row = cursor.fetchone()
                if not row:
                    raise BootstrapRejected("email verification challenge does not exist")
                payload, state, expires_at, attempts, max_attempts = row
                if str(state) != "ISSUED":
                    raise BootstrapRejected("email verification challenge is no longer issued")
                if now >= expires_at:
                    cursor.execute(
                        "UPDATE nexilabs_auth.email_verification_challenge SET challenge_state='EXPIRED' WHERE challenge_id=%s",
                        (pending.challenge_id,),
                    )
                    return False

                success = bool(verifier(str(payload)))
                if success:
                    cursor.execute(
                        """
                        UPDATE nexilabs_auth.email_verification_challenge
                           SET challenge_state='VERIFIED', consumed_at=%s
                         WHERE challenge_id=%s
                        """,
                        (now, pending.challenge_id),
                    )
                    cursor.execute(
                        """
                        UPDATE nexilabs_auth.account_email
                           SET verification_state='VERIFIED', verified_at=%s,
                               verification_reference=%s
                         WHERE email_id=%s AND principal_id=%s
                        """,
                        (now, pending.challenge_id, pending.email_id, pending.principal_id),
                    )
                    self._append_audit(
                        cursor,
                        event_type=AuditEventType.FIRST_ADMIN_EMAIL_VERIFIED.value,
                        outcome=AuditOutcome.VERIFIED.value,
                        actor_type="BOOTSTRAP_TERMINAL",
                        actor_principal_id=pending.principal_id,
                        subject_type="ACCOUNT_EMAIL",
                        subject_id=pending.email_id,
                        correlation_id=pending.correlation_id,
                        source_reference=f"{SOURCE_LOCK_COMMIT}:{BOOTSTRAP_POLICY_VERSION}",
                    )
                    return True

                new_attempts = int(attempts) + 1
                locked = new_attempts >= int(max_attempts)
                cursor.execute(
                    """
                    UPDATE nexilabs_auth.email_verification_challenge
                       SET attempt_count=%s,
                           challenge_state=%s
                     WHERE challenge_id=%s
                    """,
                    (new_attempts, "LOCKED" if locked else "ISSUED", pending.challenge_id),
                )
                self._append_audit(
                    cursor,
                    event_type=AuditEventType.FIRST_ADMIN_EMAIL_OTP_REJECTED.value,
                    outcome=AuditOutcome.DENIED.value,
                    actor_type="BOOTSTRAP_TERMINAL",
                    actor_principal_id=pending.principal_id,
                    subject_type="EMAIL_VERIFICATION_CHALLENGE",
                    subject_id=pending.challenge_id,
                    correlation_id=pending.correlation_id,
                    source_reference=f"{SOURCE_LOCK_COMMIT}:{BOOTSTRAP_POLICY_VERSION}",
                )
                return False

    def active_enigma_catalogues(self) -> dict[int, str]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT word_length, catalogue_id
                      FROM nexilabs_auth.enigma_catalogue
                     WHERE catalogue_state='ACTIVE'
                     ORDER BY word_length
                    """
                )
                return {int(length): str(catalogue_id) for length, catalogue_id in cursor.fetchall()}

    def finalize_first_admin(
        self,
        *,
        pending: PendingBootstrap,
        developer_password_verifier: str,
        admin_password_verifier: str,
        enigma_secret_verifier: str,
        completed_at: datetime,
    ) -> BootstrapReceipt:
        source_reference = f"{SOURCE_LOCK_COMMIT}:{BOOTSTRAP_POLICY_VERSION}"
        credential_id = _id("credential")
        admin_credential_id = _id("credential-admin")
        profile_id = _id("enigma-profile")
        assignment_id = _id("enigma-assignment")
        secret_verifier_id = _id("enigma-secret-verifier")
        admin_operator_id = _id("admin-operator")
        audit_event_id = _id("audit-event")
        receipt_reference = _id("bootstrap-receipt")

        with self._connect() as connection:
            with connection.cursor() as cursor:
                # The allocator row is the transaction-scoped global first-Admin
                # serialization point. The Admin count is intentionally checked
                # only after this lock is held so two concurrent bootstrap
                # terminals cannot both observe the pre-Admin state.
                cursor.execute(
                    "SELECT allocator_key FROM nexilabs_auth.admin_developer_id_allocator WHERE allocator_key='ADMIN_DEVELOPER_ID' FOR UPDATE"
                )
                if not cursor.fetchone():
                    raise BootstrapRejected("Admin Developer ID allocator is unavailable")
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.admin_operator")
                if int(cursor.fetchone()[0]) != 0:
                    raise BootstrapRejected("first Admin already exists")
                cursor.execute(
                    """
                    SELECT pa.account_state, pa.identity_type, ae.verification_state
                      FROM nexilabs_auth.principal_account AS pa
                      JOIN nexilabs_auth.account_email AS ae
                        ON ae.principal_id=pa.principal_id
                     WHERE pa.principal_id=%s AND ae.email_id=%s
                     FOR UPDATE OF pa, ae
                    """,
                    (pending.principal_id, pending.email_id),
                )
                row = cursor.fetchone()
                if not row:
                    raise BootstrapRejected("pending bootstrap identity is missing")
                if str(row[0]) != "PENDING" or str(row[1]) != "nexadevs_developer":
                    raise BootstrapRejected("pending principal is not eligible for first Admin bootstrap")
                if str(row[2]) != "VERIFIED":
                    raise BootstrapRejected("Admin email must be VERIFIED before final bootstrap")

                cursor.execute(
                    """
                    SELECT word_length, catalogue_id
                      FROM nexilabs_auth.enigma_catalogue
                     WHERE catalogue_state='ACTIVE'
                     ORDER BY word_length
                    """
                )
                catalogues = {int(length): str(catalogue_id) for length, catalogue_id in cursor.fetchall()}
                if set(catalogues) != {3, 4, 5}:
                    raise BootstrapRejected("active 3/4/5-letter PostgreSQL Enigma catalogues are required")

                cursor.execute("SELECT nexilabs_auth.reserve_admin_developer_id()")
                admin_developer_id = str(cursor.fetchone()[0])

                cursor.execute(
                    "UPDATE nexilabs_auth.principal_account SET account_state='ACTIVE', updated_at=%s WHERE principal_id=%s",
                    (completed_at, pending.principal_id),
                )
                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.credential_verifier (
                        credential_id, principal_id, credential_kind,
                        verifier_scheme, verifier_version, verifier_payload
                    ) VALUES (%s, %s, 'password', 'pbkdf2_sha256', 1, %s)
                    """,
                    (credential_id, pending.principal_id, developer_password_verifier),
                )
                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.enigma_profile (
                        profile_id, profile_state, created_at, activated_at, profile_reference
                    ) VALUES (%s, 'ACTIVE', %s, %s, %s)
                    """,
                    (profile_id, completed_at, completed_at, receipt_reference),
                )
                for length in (3, 4, 5):
                    cursor.execute(
                        """
                        INSERT INTO nexilabs_auth.enigma_profile_catalogue (
                            profile_id, word_length, catalogue_id, assigned_at
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (profile_id, length, catalogues[length], completed_at),
                    )
                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.enigma_profile_secret_verifier (
                        secret_verifier_id, profile_id, verifier_scheme, verifier_version,
                        verifier_payload, secret_state, policy_version, created_at
                    ) VALUES (%s, %s, 'pbkdf2_sha256', 1, %s, 'ACTIVE', %s, %s)
                    """,
                    (secret_verifier_id, profile_id, enigma_secret_verifier, ENIGMA_POLICY_VERSION, completed_at),
                )
                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.principal_enigma_profile (
                        assignment_id, principal_id, profile_id, assignment_state, assigned_at
                    ) VALUES (%s, %s, %s, 'ACTIVE', %s)
                    """,
                    (assignment_id, pending.principal_id, profile_id, completed_at),
                )

                preliminary_receipt = {
                    "receiptReference": receipt_reference,
                    "auditEventId": audit_event_id,
                    "principalId": pending.principal_id,
                    "adminDeveloperId": admin_developer_id,
                    "adminOperatorId": admin_operator_id,
                    "emailId": pending.email_id,
                    "enigmaProfileId": profile_id,
                    "policyVersion": BOOTSTRAP_POLICY_VERSION,
                    "sourceCommit": SOURCE_LOCK_COMMIT,
                    "databaseName": self.database_name,
                    "completedAt": completed_at.isoformat(),
                }
                receipt_digest = receipt_sha256(preliminary_receipt)

                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.admin_operator (
                        admin_operator_id, principal_id,
                        admin_developer_id, admin_developer_id_key,
                        bound_admin_email_id, admin_state,
                        created_at, bootstrap_reference, audit_reference
                    ) VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s)
                    """,
                    (
                        admin_operator_id,
                        pending.principal_id,
                        admin_developer_id,
                        admin_developer_id.casefold(),
                        pending.email_id,
                        completed_at,
                        receipt_reference,
                        audit_event_id,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO nexilabs_auth.credential_verifier (
                        credential_id, principal_id, credential_kind,
                        verifier_scheme, verifier_version, verifier_payload
                    ) VALUES (%s, %s, 'ADMIN_PASSWORD', 'pbkdf2_sha256', 1, %s)
                    """,
                    (admin_credential_id, pending.principal_id, admin_password_verifier),
                )
                for permission in ADMIN_PERMISSION_CODES:
                    cursor.execute(
                        """
                        INSERT INTO nexilabs_auth.principal_permission (
                            permission_assignment_id, principal_id, permission_code,
                            permission_state, granted_at
                        ) VALUES (%s, %s, %s, 'ACTIVE', %s)
                        """,
                        (_id("permission"), pending.principal_id, permission, completed_at),
                    )

                self._append_audit(
                    cursor,
                    audit_event_id=audit_event_id,
                    event_type=AuditEventType.FIRST_ADMIN_BOOTSTRAP_COMPLETED.value,
                    outcome=AuditOutcome.SUCCEEDED.value,
                    actor_type="BOOTSTRAP_TERMINAL",
                    actor_principal_id=pending.principal_id,
                    subject_type="ADMIN_OPERATOR",
                    subject_id=admin_operator_id,
                    correlation_id=pending.correlation_id,
                    source_reference=source_reference,
                    receipt_reference=receipt_reference,
                    receipt_digest=receipt_digest,
                )

        return BootstrapReceipt(
            receipt_reference=receipt_reference,
            audit_event_id=audit_event_id,
            principal_id=pending.principal_id,
            admin_developer_id=admin_developer_id,
            admin_operator_id=admin_operator_id,
            email_id=pending.email_id,
            enigma_profile_id=profile_id,
            policy_version=BOOTSTRAP_POLICY_VERSION,
            source_commit=SOURCE_LOCK_COMMIT,
            database_name=self.database_name,
            completed_at=completed_at.isoformat(),
            receipt_sha256=receipt_digest,
        )

    def principal_for_password_auth(self, username: str) -> dict[str, object] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pa.principal_id, pa.username, pa.identity_type, pa.account_state,
                           cv.verifier_payload, pep.profile_id
                      FROM nexilabs_auth.principal_account AS pa
                      LEFT JOIN nexilabs_auth.admin_operator AS ao
                        ON ao.principal_id=pa.principal_id
                       AND ao.admin_state='ACTIVE'
                      JOIN nexilabs_auth.credential_verifier AS cv
                        ON cv.principal_id=pa.principal_id
                       AND cv.credential_kind='password'
                       AND cv.credential_state='ACTIVE'
                      JOIN nexilabs_auth.principal_enigma_profile AS pep
                        ON pep.principal_id=pa.principal_id
                       AND pep.assignment_state='ACTIVE'
                      JOIN nexilabs_auth.enigma_profile AS ep
                        ON ep.profile_id=pep.profile_id
                       AND ep.profile_state='ACTIVE'
                     WHERE pa.username_key=%s
                        OR ao.admin_developer_id_key=%s
                     LIMIT 1
                    """,
                    (str(username).strip().casefold(), str(username).strip().casefold()),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                principal_id = str(row[0])
                cursor.execute(
                    """
                    SELECT permission_code
                      FROM nexilabs_auth.principal_permission
                     WHERE principal_id=%s AND permission_state='ACTIVE'
                     ORDER BY permission_code
                    """,
                    (principal_id,),
                )
                permissions = tuple(str(r[0]) for r in cursor.fetchall())
                return {
                    "principalId": principal_id,
                    "username": str(row[1]),
                    "identityType": str(row[2]),
                    "accountState": str(row[3]),
                    "passwordVerifier": str(row[4]),
                    "enigmaProfileId": str(row[5]),
                    "permissions": permissions,
                }

    def enigma_catalogue_row(self, *, profile_id: str, word_length: int, day: int, period: str) -> dict[str, object] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ece.catalogue_id, ece.word_1, ece.word_2, ece.word_3, ec.source_sha256
                      FROM nexilabs_auth.enigma_profile_catalogue AS epc
                      JOIN nexilabs_auth.enigma_catalogue AS ec
                        ON ec.catalogue_id=epc.catalogue_id
                       AND ec.word_length=epc.word_length
                       AND ec.catalogue_state='ACTIVE'
                      JOIN nexilabs_auth.enigma_catalogue_entry AS ece
                        ON ece.catalogue_id=epc.catalogue_id
                       AND ece.word_length=epc.word_length
                     WHERE epc.profile_id=%s
                       AND epc.word_length=%s
                       AND ece.day_of_month=%s
                       AND ece.period=%s
                    """,
                    (profile_id, int(word_length), int(day), period),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "catalogueId": str(row[0]),
                    "words": (str(row[1]), str(row[2]), str(row[3])),
                    "sourceSha256": str(row[4]),
                }

    def active_admin_binding(self, principal_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ao.admin_operator_id, ao.admin_developer_id,
                           ae.email_id, ae.email_address, cv.verifier_payload,
                           pep.profile_id, esv.verifier_payload
                      FROM nexilabs_auth.admin_operator AS ao
                      JOIN nexilabs_auth.account_email AS ae
                        ON ae.email_id=ao.bound_admin_email_id
                       AND ae.principal_id=ao.principal_id
                       AND ae.verification_state='VERIFIED'
                      JOIN nexilabs_auth.credential_verifier AS cv
                        ON cv.principal_id=ao.principal_id
                       AND cv.credential_kind='ADMIN_PASSWORD'
                       AND cv.credential_state='ACTIVE'
                      JOIN nexilabs_auth.principal_enigma_profile AS pep
                        ON pep.principal_id=ao.principal_id
                       AND pep.assignment_state='ACTIVE'
                      JOIN nexilabs_auth.enigma_profile AS ep
                        ON ep.profile_id=pep.profile_id
                       AND ep.profile_state='ACTIVE'
                      JOIN nexilabs_auth.enigma_profile_secret_verifier AS esv
                        ON esv.profile_id=ep.profile_id
                       AND esv.secret_state='ACTIVE'
                     WHERE ao.principal_id=%s
                       AND ao.admin_state='ACTIVE'
                     LIMIT 1
                    """,
                    (principal_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                cursor.execute(
                    """
                    SELECT permission_code
                      FROM nexilabs_auth.principal_permission
                     WHERE principal_id=%s AND permission_state='ACTIVE'
                     ORDER BY permission_code
                    """,
                    (principal_id,),
                )
                permissions = tuple(str(r[0]) for r in cursor.fetchall())
                return {
                    "adminOperatorId": str(row[0]),
                    "adminDeveloperId": str(row[1]),
                    "emailId": str(row[2]),
                    "emailAddress": str(row[3]),
                    "adminPasswordVerifier": str(row[4]),
                    "enigmaProfileId": str(row[5]),
                    "enigmaSecretVerifier": str(row[6]),
                    "permissions": permissions,
                }

    def append_runtime_audit(
        self,
        *,
        event_type: str,
        outcome: str,
        actor_type: str,
        subject_type: str,
        subject_id: str,
        correlation_id: str,
        actor_principal_id: str | None = None,
        actor_admin_operator_id: str | None = None,
        permission_code: str | None = None,
    ) -> str:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                return self._append_audit(
                    cursor,
                    event_type=event_type,
                    outcome=outcome,
                    actor_type=actor_type,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    correlation_id=correlation_id,
                    source_reference=f"{SOURCE_LOCK_COMMIT}:{BOOTSTRAP_POLICY_VERSION}",
                    actor_principal_id=actor_principal_id,
                    actor_admin_operator_id=actor_admin_operator_id,
                    permission_code=permission_code,
                )

    def qualification_snapshot(self) -> dict[str, object]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name
                      FROM information_schema.tables
                     WHERE table_schema='nexilabs_auth'
                       AND table_name IN (
                           'admin_developer_id_allocator',
                           'enigma_profile_secret_verifier',
                           'authority_audit_event'
                       )
                     ORDER BY table_name
                    """
                )
                tables = tuple(str(r[0]) for r in cursor.fetchall())
                cursor.execute(
                    "SELECT allocator_key, id_prefix, sequence_width, next_sequence, format_version FROM nexilabs_auth.admin_developer_id_allocator"
                )
                allocator = cursor.fetchone()
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.admin_operator")
                admin_count = int(cursor.fetchone()[0])
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.authority_audit_event")
                audit_count = int(cursor.fetchone()[0])
                cursor.execute("SELECT COUNT(*) FROM nexilabs_auth.enigma_profile_secret_verifier WHERE secret_state='ACTIVE'")
                enigma_secret_count = int(cursor.fetchone()[0])
                return {
                    "tables": tables,
                    "allocator": tuple(allocator) if allocator else None,
                    "adminOperatorCount": admin_count,
                    "auditEventCount": audit_count,
                    "activeEnigmaSecretVerifierCount": enigma_secret_count,
                }
