"""Operational services for P006.UI.10.3."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from threading import RLock

from backend.auth.credentials import hash_password, verify_password
from backend.auth.enigma import normalize_lookup_index, period_for_hour

from .contracts import (
    ADMIN_ELEVATION_POLICY_VERSION,
    ADMIN_ELEVATION_TTL_SECONDS,
    ADMIN_PERMISSION_CODES,
    BOOTSTRAP_POLICY_VERSION,
    DEVELOPER_SESSION_TTL_SECONDS,
    ENIGMA_CHALLENGE_TTL_SECONDS,
    OTP_TTL_SECONDS,
    AdminEligibility,
    AdminElevation,
    AuditEventType,
    AuditOutcome,
    AuthenticationRejected,
    BootstrapIdentityInput,
    BootstrapRejected,
    PendingBootstrap,
    SOURCE_LOCK_COMMIT,
    utc_now,
)
from .security import (
    generate_otp,
    normalize_email,
    normalize_enigma_secret,
    otp_verifier,
    safe_email_hint,
    split_enigma_response,
    verify_otp,
)


class FirstAdminBootstrapService:
    """Protected-terminal first Admin bootstrap orchestration."""

    def __init__(self, *, authority, mail_gateway, otp_pepper: bytes):
        if not otp_pepper or len(otp_pepper) < 16:
            raise ValueError("bootstrap OTP verifier key must contain at least 16 bytes")
        self.authority = authority
        self.mail_gateway = mail_gateway
        self.otp_pepper = bytes(otp_pepper)

    @staticmethod
    def _safe_password(password: str, label: str) -> str:
        value = str(password)
        if len(value) < 12:
            raise BootstrapRejected(f"{label} must contain at least 12 characters")
        if value.strip() != value:
            raise BootstrapRejected(f"{label} must not begin or end with whitespace")
        return value

    def begin(self, identity: BootstrapIdentityInput, *, now: datetime | None = None) -> PendingBootstrap:
        now = now or utc_now()
        challenge_id = f"email-challenge:{secrets.token_urlsafe(18)}"
        correlation_id = f"bootstrap-correlation:{secrets.token_urlsafe(18)}"
        otp = generate_otp()
        verifier_payload = otp_verifier(
            pepper=self.otp_pepper,
            challenge_id=challenge_id,
            otp=otp,
        )
        expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)
        pending = self.authority.prepare_pending_bootstrap(
            identity=identity,
            challenge_id=challenge_id,
            otp_verifier_payload=verifier_payload,
            issued_at=now,
            expires_at=expires_at,
            correlation_id=correlation_id,
        )
        recipient = self.authority.email_for_pending(pending)
        try:
            provider_reference = self.mail_gateway.send_email_verification_otp(
                recipient=recipient,
                otp=otp,
                expires_at=expires_at,
                correlation_id=correlation_id,
            )
        except Exception:
            self.authority.record_otp_delivery(
                pending=pending,
                provider_reference=None,
                delivered=False,
            )
            raise
        self.authority.record_otp_delivery(
            pending=pending,
            provider_reference=provider_reference,
            delivered=True,
        )
        return pending

    def resend(self, pending: PendingBootstrap, *, now: datetime | None = None) -> None:
        now = now or utc_now()
        otp = generate_otp()
        expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)
        verifier_payload = otp_verifier(
            pepper=self.otp_pepper,
            challenge_id=pending.challenge_id,
            otp=otp,
        )
        self.authority.resend_email_challenge(
            pending=pending,
            otp_verifier_payload=verifier_payload,
            now=now,
            expires_at=expires_at,
        )
        recipient = self.authority.email_for_pending(pending)
        try:
            provider_reference = self.mail_gateway.send_email_verification_otp(
                recipient=recipient,
                otp=otp,
                expires_at=expires_at,
                correlation_id=pending.correlation_id,
            )
        except Exception:
            self.authority.record_otp_delivery(pending=pending, provider_reference=None, delivered=False)
            raise
        self.authority.record_otp_delivery(
            pending=pending,
            provider_reference=provider_reference,
            delivered=True,
        )

    def verify_email(self, pending: PendingBootstrap, otp: str, *, now: datetime | None = None) -> bool:
        now = now or utc_now()
        supplied = str(otp).strip()
        return self.authority.verify_email_challenge(
            pending=pending,
            otp=supplied,
            verifier=lambda stored: verify_otp(
                pepper=self.otp_pepper,
                challenge_id=pending.challenge_id,
                otp=supplied,
                expected=stored,
            ),
            now=now,
        )

    def finalize(
        self,
        pending: PendingBootstrap,
        *,
        developer_password: str,
        enigma_profile_secret: str,
        admin_password: str,
        now: datetime | None = None,
    ):
        developer_password = self._safe_password(developer_password, "Developer password")
        admin_password = self._safe_password(admin_password, "Admin password")
        if hmac.compare_digest(developer_password, admin_password):
            raise BootstrapRejected("Developer password and Admin password must be different")
        enigma_secret = normalize_enigma_secret(enigma_profile_secret)
        now = now or utc_now()
        try:
            return self.authority.finalize_first_admin(
                pending=pending,
                developer_password_verifier=hash_password(developer_password),
                admin_password_verifier=hash_password(admin_password),
                enigma_secret_verifier=hash_password(enigma_secret),
                completed_at=now,
            )
        except Exception:
            try:
                self.authority.append_runtime_audit(
                    event_type=AuditEventType.FIRST_ADMIN_BOOTSTRAP_FAILED.value,
                    outcome=AuditOutcome.FAILED.value,
                    actor_type="BOOTSTRAP_TERMINAL",
                    actor_principal_id=pending.principal_id,
                    subject_type="PRINCIPAL",
                    subject_id=pending.principal_id,
                    correlation_id=pending.correlation_id,
                )
            except Exception:
                pass
            raise


class _RuntimeStore:
    MAX_ENIGMA_ATTEMPTS = 3

    def __init__(self):
        self._lock = RLock()
        self._attempts: dict[str, dict[str, object]] = {}
        self._admin_attempts: dict[str, dict[str, object]] = {}
        self._sessions: dict[str, dict[str, object]] = {}
        self._elevations: dict[str, AdminElevation] = {}

    def create_attempt(
        self,
        record: dict[str, object],
        *,
        lookup_index: int,
        challenge: dict[str, object],
        expected_signature: str,
    ) -> str:
        attempt_id = str(challenge["attemptId"])
        with self._lock:
            self._attempts[attempt_id] = {
                "principal": dict(record),
                "lookupIndex": int(lookup_index),
                "challenge": dict(challenge),
                "expectedSignature": str(expected_signature),
                "attempts": 0,
            }
        return attempt_id

    def attempt(self, attempt_id: str) -> dict[str, object] | None:
        with self._lock:
            value = self._attempts.get(attempt_id)
            return dict(value) if value else None

    def increment_attempts(self, attempt_id: str) -> int:
        with self._lock:
            value = self._attempts[attempt_id]
            value["attempts"] = int(value["attempts"]) + 1
            return int(value["attempts"])

    def consume_attempt(self, attempt_id: str) -> None:
        with self._lock:
            self._attempts.pop(attempt_id, None)

    def create_admin_attempt(
        self,
        *,
        session_id: str,
        principal_id: str,
        binding: dict[str, object],
        lookup_index: int,
        challenge: dict[str, object],
    ) -> str:
        attempt_id = str(challenge["attemptId"])
        with self._lock:
            self._admin_attempts[attempt_id] = {
                "sessionId": str(session_id),
                "principalId": str(principal_id),
                "binding": dict(binding),
                "lookupIndex": int(lookup_index),
                "challenge": dict(challenge),
                "attempts": 0,
            }
        return attempt_id

    def admin_attempt(self, attempt_id: str) -> dict[str, object] | None:
        with self._lock:
            value = self._admin_attempts.get(attempt_id)
            return dict(value) if value else None

    def increment_admin_attempts(self, attempt_id: str) -> int:
        with self._lock:
            value = self._admin_attempts[attempt_id]
            value["attempts"] = int(value["attempts"]) + 1
            return int(value["attempts"])

    def consume_admin_attempt(self, attempt_id: str) -> None:
        with self._lock:
            self._admin_attempts.pop(attempt_id, None)

    def create_session(self, principal: dict[str, object], *, now: datetime) -> dict[str, object]:
        session_id = f"prod-session:{secrets.token_urlsafe(24)}"
        session = {
            "sessionId": session_id,
            "principalId": principal["principalId"],
            "username": principal["username"],
            "identityType": "nexadevs_developer",
            "runtime": "production",
            "permissions": list(principal.get("permissions", ())),
            "authenticationStrength": "developer_password_enigma",
            "issuedAt": now.isoformat(),
            "expiresAt": (now + timedelta(seconds=DEVELOPER_SESSION_TTL_SECONDS)).isoformat(),
        }
        with self._lock:
            self._sessions[session_id] = session
        return dict(session)

    def session(self, session_id: str, *, now: datetime) -> dict[str, object] | None:
        with self._lock:
            value = self._sessions.get(session_id)
            if not value:
                return None
            if datetime.fromisoformat(str(value["expiresAt"])) <= now:
                self._sessions.pop(session_id, None)
                return None
            return dict(value)

    def revoke_session(self, session_id: str) -> bool:
        with self._lock:
            removed = self._sessions.pop(session_id, None) is not None
            for attempt_id, attempt in list(self._admin_attempts.items()):
                if attempt.get("sessionId") == session_id:
                    self._admin_attempts.pop(attempt_id, None)
            for elevation_id, elevation in list(self._elevations.items()):
                if elevation.session_id == session_id:
                    self._elevations.pop(elevation_id, None)
            return removed

    def create_elevation(self, session_id: str, principal_id: str, admin_operator_id: str, permissions: tuple[str, ...], *, now: datetime) -> AdminElevation:
        elevation = AdminElevation(
            elevation_id=f"admin-elevation:{secrets.token_urlsafe(24)}",
            session_id=session_id,
            principal_id=principal_id,
            admin_operator_id=admin_operator_id,
            permissions=tuple(permissions),
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=ADMIN_ELEVATION_TTL_SECONDS)).isoformat(),
        )
        with self._lock:
            self._elevations[elevation.elevation_id] = elevation
        return elevation

    def elevation(self, elevation_id: str, *, session_id: str, now: datetime) -> AdminElevation | None:
        with self._lock:
            elevation = self._elevations.get(elevation_id)
            if not elevation or elevation.session_id != session_id:
                return None
            return elevation

    def revoke_elevation(self, elevation_id: str) -> AdminElevation | None:
        with self._lock:
            return self._elevations.pop(elevation_id, None)


class ProductionAdminAuthenticationService:
    """Production Developer authentication plus conditional Admin elevation."""

    def __init__(self, *, authority, developer_enigma, now=utc_now):
        self.authority = authority
        self.developer_enigma = developer_enigma
        self._now = now
        self.runtime = _RuntimeStore()

    @staticmethod
    def _select_word_length(attempt_id: str) -> int:
        digest = hashlib.sha256(attempt_id.encode("utf-8")).digest()
        return (3, 4, 5)[digest[0] % 3]

    def _issue_postgresql_challenge(self, *, profile_id: str, attempt_prefix: str) -> tuple[dict[str, object], dict[str, object], int]:
        now = self._now()
        attempt_id = f"{attempt_prefix}:{secrets.token_urlsafe(18)}"
        word_length = self._select_word_length(attempt_id)
        period = period_for_hour(now.hour)
        row = self.authority.enigma_catalogue_row(
            profile_id=str(profile_id),
            word_length=word_length,
            day=now.day,
            period=period,
        )
        if not row:
            raise AuthenticationRejected("Production Enigma catalogue row is unavailable")
        words = tuple(str(value) for value in row["words"])
        lookup_index = normalize_lookup_index(sum(len(word) for word in words) + now.day)
        challenge = {
            "challengeId": f"prod-enigma:{secrets.token_urlsafe(18)}",
            "attemptId": attempt_id,
            "wordLength": word_length,
            "words": list(words),
            "period": period,
            "issuedAt": now.isoformat(),
            "expiresAt": (now + timedelta(seconds=ENIGMA_CHALLENGE_TTL_SECONDS)).isoformat(),
        }
        return challenge, row, lookup_index

    def start_developer(self, *, username: str, password: str, runtime: str) -> dict[str, object]:
        if str(runtime).strip().lower() != "production":
            raise AuthenticationRejected("Production authority accepts only the production runtime")
        record = self.authority.principal_for_password_auth(username)
        correlation_id = f"auth-correlation:{secrets.token_urlsafe(18)}"
        if not record or record.get("accountState") != "ACTIVE" or not verify_password(password, str(record.get("passwordVerifier", ""))):
            if record:
                self.authority.append_runtime_audit(
                    event_type=AuditEventType.DEVELOPER_AUTH_FAILED.value,
                    outcome=AuditOutcome.DENIED.value,
                    actor_type="PRINCIPAL",
                    actor_principal_id=str(record["principalId"]),
                    subject_type="PRINCIPAL",
                    subject_id=str(record["principalId"]),
                    correlation_id=correlation_id,
                )
            raise AuthenticationRejected("invalid credentials")

        now = self._now()
        challenge, row, lookup_index = self._issue_postgresql_challenge(
            profile_id=str(record["enigmaProfileId"]),
            attempt_prefix="prod-auth",
        )
        expected_signature = self.developer_enigma.expected_signature(
            word_length=int(challenge["wordLength"]),
            day=now.day,
            period=str(challenge["period"]),
            postgres_words=tuple(str(value) for value in challenge["words"]),
            postgres_source_sha256=str(row.get("sourceSha256", "")),
            lookup_index=lookup_index,
        )
        self.runtime.create_attempt(
            record,
            lookup_index=lookup_index,
            challenge=challenge,
            expected_signature=expected_signature,
        )
        self.authority.append_runtime_audit(
            event_type=AuditEventType.ENIGMA_CHALLENGE_ISSUED.value,
            outcome=AuditOutcome.ISSUED.value,
            actor_type="PRINCIPAL",
            actor_principal_id=str(record["principalId"]),
            subject_type="AUTHENTICATION_ATTEMPT",
            subject_id=str(challenge["attemptId"]),
            correlation_id=correlation_id,
        )
        return {"attemptId": challenge["attemptId"], "challenge": challenge}

    def verify_developer(self, *, attempt_id: str, response: str) -> dict[str, object]:
        current = self.runtime.attempt(str(attempt_id))
        if not current:
            raise AuthenticationRejected("authentication attempt is unavailable")
        challenge = dict(current["challenge"])
        now = self._now()
        principal = dict(current["principal"])
        if datetime.fromisoformat(str(challenge["expiresAt"])) <= now:
            self.runtime.consume_attempt(str(attempt_id))
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ENIGMA_VERIFICATION_FAILED.value,
                outcome=AuditOutcome.EXPIRED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=str(principal["principalId"]),
                subject_type="AUTHENTICATION_ATTEMPT",
                subject_id=str(attempt_id),
                correlation_id=f"auth-correlation:{secrets.token_urlsafe(18)}",
            )
            raise AuthenticationRejected("Enigma challenge expired")
        attempts = self.runtime.increment_attempts(str(attempt_id))
        valid = self.developer_enigma.verify(str(response), str(current["expectedSignature"]))
        correlation_id = f"auth-correlation:{secrets.token_urlsafe(18)}"
        if not valid:
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ENIGMA_VERIFICATION_FAILED.value,
                outcome=AuditOutcome.DENIED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=str(principal["principalId"]),
                subject_type="AUTHENTICATION_ATTEMPT",
                subject_id=str(attempt_id),
                correlation_id=correlation_id,
            )
            if attempts >= self.runtime.MAX_ENIGMA_ATTEMPTS:
                self.runtime.consume_attempt(str(attempt_id))
            raise AuthenticationRejected("invalid Enigma response")
        session = self.runtime.create_session(principal, now=now)
        self.runtime.consume_attempt(str(attempt_id))
        try:
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ENIGMA_VERIFICATION_SUCCEEDED.value,
                outcome=AuditOutcome.SUCCEEDED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=str(principal["principalId"]),
                subject_type="AUTHENTICATION_ATTEMPT",
                subject_id=str(attempt_id),
                correlation_id=correlation_id,
            )
            self.authority.append_runtime_audit(
                event_type=AuditEventType.DEVELOPER_AUTH_SUCCEEDED.value,
                outcome=AuditOutcome.SUCCEEDED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=str(principal["principalId"]),
                subject_type="SESSION",
                subject_id=str(session["sessionId"]),
                correlation_id=correlation_id,
            )
        except BaseException:
            self.runtime.revoke_session(str(session["sessionId"]))
            raise
        return session

    def session(self, session_id: str) -> dict[str, object]:
        value = self.runtime.session(str(session_id), now=self._now())
        if not value:
            raise AuthenticationRejected("session unavailable")
        return value

    def logout(self, session_id: str) -> bool:
        current = self.runtime.session(str(session_id), now=self._now())
        revoked = self.runtime.revoke_session(str(session_id))
        if revoked and current:
            self.authority.append_runtime_audit(
                event_type=AuditEventType.DEVELOPER_SESSION_REVOKED.value,
                outcome=AuditOutcome.REVOKED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=str(current["principalId"]),
                subject_type="SESSION",
                subject_id=str(session_id),
                correlation_id=f"auth-correlation:{secrets.token_urlsafe(18)}",
            )
        return revoked

    def eligibility(self, session_id: str) -> AdminEligibility:
        session = self.session(session_id)
        principal_id = str(session["principalId"])
        binding = self.authority.active_admin_binding(principal_id)
        if not binding:
            return AdminEligibility(False, principal_id, None, None, None, tuple(session.get("permissions", ())))
        permissions = tuple(str(value) for value in binding.get("permissions", ()))
        eligible = "NEXILABS.ADMIN.ELEVATE" in permissions
        return AdminEligibility(
            eligible=eligible,
            principal_id=principal_id,
            admin_operator_id=str(binding["adminOperatorId"]) if eligible else None,
            admin_developer_id=str(binding["adminDeveloperId"]) if eligible else None,
            bound_email_hint=safe_email_hint(str(binding["emailAddress"])) if eligible else None,
            permissions=permissions,
        )

    def start_admin_elevation(self, session_id: str, *, admin_email: str, admin_password: str) -> dict[str, object]:
        session = self.session(session_id)
        principal_id = str(session["principalId"])
        binding = self.authority.active_admin_binding(principal_id)
        correlation_id = f"admin-elevation-correlation:{secrets.token_urlsafe(18)}"
        if not binding or "NEXILABS.ADMIN.ELEVATE" not in tuple(binding.get("permissions", ())):
            raise AuthenticationRejected("Admin elevation is unavailable")
        email_matches = hmac.compare_digest(
            normalize_email(admin_email),
            normalize_email(str(binding["emailAddress"])),
        )
        password_matches = verify_password(admin_password, str(binding["adminPasswordVerifier"]))
        if not email_matches or not password_matches:
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ADMIN_ELEVATION_DENIED.value,
                outcome=AuditOutcome.DENIED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=principal_id,
                subject_type="ADMIN_OPERATOR",
                subject_id=str(binding["adminOperatorId"]),
                correlation_id=correlation_id,
                permission_code="NEXILABS.ADMIN.ELEVATE",
            )
            raise AuthenticationRejected("invalid Admin elevation credentials")

        challenge, _row, lookup_index = self._issue_postgresql_challenge(
            profile_id=str(binding["enigmaProfileId"]),
            attempt_prefix="admin-auth",
        )
        self.runtime.create_admin_attempt(
            session_id=session_id,
            principal_id=principal_id,
            binding=binding,
            lookup_index=lookup_index,
            challenge=challenge,
        )
        self.authority.append_runtime_audit(
            event_type=AuditEventType.ADMIN_ENIGMA_CHALLENGE_ISSUED.value,
            outcome=AuditOutcome.ISSUED.value,
            actor_type="PRINCIPAL",
            actor_principal_id=principal_id,
            subject_type="ADMIN_AUTHENTICATION_ATTEMPT",
            subject_id=str(challenge["attemptId"]),
            correlation_id=correlation_id,
            permission_code="NEXILABS.ADMIN.ELEVATE",
        )
        return {"attemptId": challenge["attemptId"], "challenge": challenge}

    def verify_admin_elevation(self, session_id: str, *, attempt_id: str, response: str) -> AdminElevation:
        session = self.session(session_id)
        current = self.runtime.admin_attempt(str(attempt_id))
        if not current or str(current.get("sessionId")) != str(session_id):
            raise AuthenticationRejected("Admin authentication attempt is unavailable")
        if str(current.get("principalId")) != str(session["principalId"]):
            self.runtime.consume_admin_attempt(str(attempt_id))
            raise AuthenticationRejected("Admin authentication principal mismatch")

        challenge = dict(current["challenge"])
        now = self._now()
        binding = dict(current["binding"])
        principal_id = str(session["principalId"])
        correlation_id = f"admin-elevation-correlation:{secrets.token_urlsafe(18)}"
        if datetime.fromisoformat(str(challenge["expiresAt"])) <= now:
            self.runtime.consume_admin_attempt(str(attempt_id))
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ADMIN_ENIGMA_VERIFICATION_FAILED.value,
                outcome=AuditOutcome.EXPIRED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=principal_id,
                subject_type="ADMIN_AUTHENTICATION_ATTEMPT",
                subject_id=str(attempt_id),
                correlation_id=correlation_id,
                permission_code="NEXILABS.ADMIN.ELEVATE",
            )
            raise AuthenticationRejected("Admin Enigma challenge expired")

        attempts = self.runtime.increment_admin_attempts(str(attempt_id))
        candidate_secret = split_enigma_response(str(response), int(current["lookupIndex"]))
        valid = bool(candidate_secret) and verify_password(
            candidate_secret,
            str(binding["enigmaSecretVerifier"]),
        )
        if not valid:
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ADMIN_ENIGMA_VERIFICATION_FAILED.value,
                outcome=AuditOutcome.DENIED.value,
                actor_type="PRINCIPAL",
                actor_principal_id=principal_id,
                subject_type="ADMIN_AUTHENTICATION_ATTEMPT",
                subject_id=str(attempt_id),
                correlation_id=correlation_id,
                permission_code="NEXILABS.ADMIN.ELEVATE",
            )
            if attempts >= self.runtime.MAX_ENIGMA_ATTEMPTS:
                self.runtime.consume_admin_attempt(str(attempt_id))
            raise AuthenticationRejected("invalid Admin Enigma response")

        elevation = self.runtime.create_elevation(
            session_id,
            principal_id,
            str(binding["adminOperatorId"]),
            tuple(str(value) for value in binding.get("permissions", ())),
            now=now,
        )
        self.runtime.consume_admin_attempt(str(attempt_id))
        try:
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ADMIN_ENIGMA_VERIFICATION_SUCCEEDED.value,
                outcome=AuditOutcome.SUCCEEDED.value,
                actor_type="ADMIN_OPERATOR",
                actor_principal_id=principal_id,
                actor_admin_operator_id=str(binding["adminOperatorId"]),
                subject_type="ADMIN_AUTHENTICATION_ATTEMPT",
                subject_id=str(attempt_id),
                correlation_id=correlation_id,
                permission_code="NEXILABS.ADMIN.ELEVATE",
            )
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ADMIN_ELEVATION_SUCCEEDED.value,
                outcome=AuditOutcome.SUCCEEDED.value,
                actor_type="ADMIN_OPERATOR",
                actor_principal_id=principal_id,
                actor_admin_operator_id=str(binding["adminOperatorId"]),
                subject_type="ADMIN_ELEVATION",
                subject_id=elevation.elevation_id,
                correlation_id=correlation_id,
                permission_code="NEXILABS.ADMIN.ELEVATE",
            )
        except BaseException:
            self.runtime.revoke_elevation(elevation.elevation_id)
            raise
        return elevation

    def require_elevation(self, session_id: str, elevation_id: str, permission_code: str) -> AdminElevation:
        session = self.session(session_id)
        now = self._now()
        elevation = self.runtime.elevation(elevation_id, session_id=session_id, now=now)
        if not elevation:
            raise AuthenticationRejected("Admin elevation is unavailable")
        if datetime.fromisoformat(elevation.expires_at) <= now:
            self.runtime.revoke_elevation(elevation_id)
            self.authority.append_runtime_audit(
                event_type=AuditEventType.ADMIN_ELEVATION_EXPIRED.value,
                outcome=AuditOutcome.EXPIRED.value,
                actor_type="ADMIN_OPERATOR",
                actor_principal_id=elevation.principal_id,
                actor_admin_operator_id=elevation.admin_operator_id,
                subject_type="ADMIN_ELEVATION",
                subject_id=elevation.elevation_id,
                correlation_id=f"admin-elevation-correlation:{secrets.token_urlsafe(18)}",
                permission_code="NEXILABS.ADMIN.ELEVATE",
            )
            raise AuthenticationRejected("Admin elevation expired")
        if permission_code not in elevation.permissions:
            raise AuthenticationRejected("Admin permission denied")
        if elevation.principal_id != str(session["principalId"]):
            raise AuthenticationRejected("Admin elevation principal mismatch")
        return elevation

    def revoke_elevation(self, session_id: str, elevation_id: str) -> bool:
        session = self.session(session_id)
        elevation = self.runtime.revoke_elevation(elevation_id)
        if not elevation or elevation.session_id != session_id:
            return False
        expired = datetime.fromisoformat(elevation.expires_at) <= self._now()
        self.authority.append_runtime_audit(
            event_type=(AuditEventType.ADMIN_ELEVATION_EXPIRED.value if expired else AuditEventType.ADMIN_ELEVATION_REVOKED.value),
            outcome=(AuditOutcome.EXPIRED.value if expired else AuditOutcome.REVOKED.value),
            actor_type="ADMIN_OPERATOR",
            actor_principal_id=str(session["principalId"]),
            actor_admin_operator_id=elevation.admin_operator_id,
            subject_type="ADMIN_ELEVATION",
            subject_id=elevation.elevation_id,
            correlation_id=f"admin-elevation-correlation:{secrets.token_urlsafe(18)}",
            permission_code="NEXILABS.ADMIN.ELEVATE",
        )
        return True
