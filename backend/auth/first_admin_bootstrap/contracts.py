"""P006.UI.10.3 — First Admin bootstrap and layered Admin authentication contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol


MILESTONE_ID = "P006.UI.10.3"
SOURCE_LOCK_COMMIT = "e546ac4bd8570934df39954ee75d03c7a60ed2e5"
BOOTSTRAP_POLICY_VERSION = "first-admin-bootstrap-v1"
OTP_POLICY_VERSION = "first-admin-email-otp-v1"
ENIGMA_POLICY_VERSION = "production-enigma-profile-secret-v1"
ADMIN_ELEVATION_POLICY_VERSION = "admin-elevation-v1"
AUDIT_POLICY_VERSION = "authority-audit-v1"
ADMIN_DEVELOPER_ID_PREFIX = "NEXADEV-ADM-"
ADMIN_DEVELOPER_ID_WIDTH = 6
OTP_LENGTH = 6
OTP_TTL_SECONDS = 600
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_RESENDS = 3
ADMIN_ELEVATION_TTL_SECONDS = 600
DEVELOPER_SESSION_TTL_SECONDS = 3600
ENIGMA_CHALLENGE_TTL_SECONDS = 180

ADMIN_PERMISSION_CODES = (
    "NEXILABS.ADMIN.ELEVATE",
    "NEXILABS.ADMIN_OPERATOR.MANAGE",
    "NEXILABS.DEVELOPER_REQUEST.REVIEW",
    "NEXILABS.DEVELOPER_SETUP.ISSUE",
    "NEXILABS.ENIGMA.GOVERN",
    "NEXILABS.AUDIT.READ",
)


class FirstAdminError(RuntimeError):
    """Base error for governed first-Admin operations."""


class BootstrapRejected(FirstAdminError):
    """Raised when protected bootstrap preconditions are not satisfied."""


class AuthenticationRejected(FirstAdminError):
    """Raised when a Production authentication/elevation operation is denied."""


class MailDeliveryError(FirstAdminError):
    """Raised when the configured mail gateway cannot deliver the OTP."""


class ActorType(StrEnum):
    BOOTSTRAP_TERMINAL = "BOOTSTRAP_TERMINAL"
    PRINCIPAL = "PRINCIPAL"
    ADMIN_OPERATOR = "ADMIN_OPERATOR"
    SYSTEM = "SYSTEM"


class AuditOutcome(StrEnum):
    STARTED = "STARTED"
    ISSUED = "ISSUED"
    SENT = "SENT"
    VERIFIED = "VERIFIED"
    SUCCEEDED = "SUCCEEDED"
    DENIED = "DENIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class AuditEventType(StrEnum):
    FIRST_ADMIN_BOOTSTRAP_STARTED = "FIRST_ADMIN_BOOTSTRAP_STARTED"
    FIRST_ADMIN_EMAIL_CHALLENGE_ISSUED = "FIRST_ADMIN_EMAIL_CHALLENGE_ISSUED"
    FIRST_ADMIN_EMAIL_OTP_SENT = "FIRST_ADMIN_EMAIL_OTP_SENT"
    FIRST_ADMIN_EMAIL_OTP_DELIVERY_FAILED = "FIRST_ADMIN_EMAIL_OTP_DELIVERY_FAILED"
    FIRST_ADMIN_EMAIL_OTP_REJECTED = "FIRST_ADMIN_EMAIL_OTP_REJECTED"
    FIRST_ADMIN_EMAIL_VERIFIED = "FIRST_ADMIN_EMAIL_VERIFIED"
    FIRST_ADMIN_BOOTSTRAP_COMPLETED = "FIRST_ADMIN_BOOTSTRAP_COMPLETED"
    FIRST_ADMIN_BOOTSTRAP_FAILED = "FIRST_ADMIN_BOOTSTRAP_FAILED"
    DEVELOPER_AUTH_SUCCEEDED = "DEVELOPER_AUTH_SUCCEEDED"
    DEVELOPER_AUTH_FAILED = "DEVELOPER_AUTH_FAILED"
    DEVELOPER_SESSION_REVOKED = "DEVELOPER_SESSION_REVOKED"
    ENIGMA_CHALLENGE_ISSUED = "ENIGMA_CHALLENGE_ISSUED"
    ENIGMA_VERIFICATION_SUCCEEDED = "ENIGMA_VERIFICATION_SUCCEEDED"
    ENIGMA_VERIFICATION_FAILED = "ENIGMA_VERIFICATION_FAILED"
    ADMIN_ENIGMA_CHALLENGE_ISSUED = "ADMIN_ENIGMA_CHALLENGE_ISSUED"
    ADMIN_ENIGMA_VERIFICATION_SUCCEEDED = "ADMIN_ENIGMA_VERIFICATION_SUCCEEDED"
    ADMIN_ENIGMA_VERIFICATION_FAILED = "ADMIN_ENIGMA_VERIFICATION_FAILED"
    ADMIN_ELEVATION_SUCCEEDED = "ADMIN_ELEVATION_SUCCEEDED"
    ADMIN_ELEVATION_DENIED = "ADMIN_ELEVATION_DENIED"
    ADMIN_ELEVATION_EXPIRED = "ADMIN_ELEVATION_EXPIRED"
    ADMIN_ELEVATION_REVOKED = "ADMIN_ELEVATION_REVOKED"


@dataclass(frozen=True, slots=True)
class BootstrapIdentityInput:
    username: str
    first_name: str
    last_name: str
    admin_email: str

    def __post_init__(self) -> None:
        if not self.username.strip():
            raise ValueError("username is required")
        if not self.first_name.strip() or not self.last_name.strip():
            raise ValueError("first and last name are required")
        email = self.admin_email.strip()
        if "@" not in email or any(ch.isspace() for ch in email):
            raise ValueError("a valid Admin email is required")


@dataclass(frozen=True, slots=True)
class PendingBootstrap:
    principal_id: str
    email_id: str
    challenge_id: str
    correlation_id: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class BootstrapReceipt:
    receipt_reference: str
    audit_event_id: str
    principal_id: str
    admin_developer_id: str
    admin_operator_id: str
    email_id: str
    enigma_profile_id: str
    policy_version: str
    source_commit: str
    database_name: str
    completed_at: str
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "receiptReference": self.receipt_reference,
            "auditEventId": self.audit_event_id,
            "principalId": self.principal_id,
            "adminDeveloperId": self.admin_developer_id,
            "adminOperatorId": self.admin_operator_id,
            "emailId": self.email_id,
            "enigmaProfileId": self.enigma_profile_id,
            "policyVersion": self.policy_version,
            "sourceCommit": self.source_commit,
            "databaseName": self.database_name,
            "completedAt": self.completed_at,
            "receiptSha256": self.receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class AdminEligibility:
    eligible: bool
    principal_id: str
    admin_operator_id: str | None
    admin_developer_id: str | None
    bound_email_hint: str | None
    permissions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "principalId": self.principal_id,
            "adminOperatorId": self.admin_operator_id,
            "adminDeveloperId": self.admin_developer_id,
            "boundEmailHint": self.bound_email_hint,
            "permissions": list(self.permissions),
        }


@dataclass(frozen=True, slots=True)
class AdminElevation:
    elevation_id: str
    session_id: str
    principal_id: str
    admin_operator_id: str
    permissions: tuple[str, ...]
    issued_at: str
    expires_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "elevationId": self.elevation_id,
            "principalId": self.principal_id,
            "adminOperatorId": self.admin_operator_id,
            "permissions": list(self.permissions),
            "issuedAt": self.issued_at,
            "expiresAt": self.expires_at,
        }


class MailGateway(Protocol):
    def send_email_verification_otp(
        self,
        *,
        recipient: str,
        otp: str,
        expires_at: datetime,
        correlation_id: str,
    ) -> str:
        """Deliver the OTP and return a non-secret provider/message reference."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
