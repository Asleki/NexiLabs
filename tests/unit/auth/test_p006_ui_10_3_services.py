from datetime import datetime, timedelta, timezone

import pytest

from backend.auth.credentials import hash_password
from backend.auth.first_admin_bootstrap.contracts import (
    BootstrapIdentityInput,
    BootstrapReceipt,
    BootstrapRejected,
    PendingBootstrap,
)
from backend.auth.first_admin_bootstrap.mail import MemoryMailGateway
from backend.auth.first_admin_bootstrap.service import (
    FirstAdminBootstrapService,
    ProductionAdminAuthenticationService,
)


NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


class FakeBootstrapAuthority:
    def __init__(self):
        self.pending = None
        self.stored_otp_verifier = None
        self.deliveries = []
        self.resends = 0
        self.finalized = None

    def prepare_pending_bootstrap(self, **kwargs):
        self.stored_otp_verifier = kwargs["otp_verifier_payload"]
        self.pending = PendingBootstrap(
            principal_id="principal:first",
            email_id="email:first",
            challenge_id=kwargs["challenge_id"],
            correlation_id=kwargs["correlation_id"],
            expires_at=kwargs["expires_at"].isoformat(),
        )
        return self.pending

    def email_for_pending(self, pending):
        return "real.admin@example.com"

    def record_otp_delivery(self, **kwargs):
        self.deliveries.append(kwargs)

    def resend_email_challenge(self, **kwargs):
        self.resends += 1
        self.stored_otp_verifier = kwargs["otp_verifier_payload"]
        return self.resends

    def verify_email_challenge(self, *, verifier, **kwargs):
        return verifier(self.stored_otp_verifier)

    def finalize_first_admin(self, **kwargs):
        self.finalized = kwargs
        return BootstrapReceipt(
            receipt_reference="bootstrap-receipt:1",
            audit_event_id="audit-event:1",
            principal_id="principal:first",
            admin_developer_id="NEXADEV-ADM-000001",
            admin_operator_id="admin-operator:1",
            email_id="email:first",
            enigma_profile_id="enigma-profile:1",
            policy_version="first-admin-bootstrap-v1",
            source_commit="e546ac4bd8570934df39954ee75d03c7a60ed2e5",
            database_name="npp_dev",
            completed_at=NOW.isoformat(),
            receipt_sha256="a" * 64,
        )


def test_bootstrap_begin_delivers_real_mail_through_gateway():
    authority = FakeBootstrapAuthority()
    mail = MemoryMailGateway()
    service = FirstAdminBootstrapService(authority=authority, mail_gateway=mail, otp_pepper=b"p" * 32)
    pending = service.begin(BootstrapIdentityInput("alex", "Alex", "Nexa", "real.admin@example.com"), now=NOW)
    assert pending.principal_id == "principal:first"
    assert mail.messages[0]["recipient"] == "real.admin@example.com"
    assert len(mail.messages[0]["otp"]) == 6
    assert authority.deliveries[-1]["delivered"] is True


def test_bootstrap_email_verification_uses_only_stored_verifier():
    authority = FakeBootstrapAuthority()
    mail = MemoryMailGateway()
    service = FirstAdminBootstrapService(authority=authority, mail_gateway=mail, otp_pepper=b"p" * 32)
    pending = service.begin(BootstrapIdentityInput("alex", "Alex", "Nexa", "real.admin@example.com"), now=NOW)
    raw_otp = mail.messages[0]["otp"]
    assert raw_otp not in authority.stored_otp_verifier
    assert service.verify_email(pending, raw_otp, now=NOW) is True


def test_bootstrap_rejects_same_developer_and_admin_password():
    authority = FakeBootstrapAuthority()
    service = FirstAdminBootstrapService(authority=authority, mail_gateway=MemoryMailGateway(), otp_pepper=b"p" * 32)
    pending = PendingBootstrap("p", "e", "c", "corr", NOW.isoformat())
    with pytest.raises(BootstrapRejected, match="must be different"):
        service.finalize(
            pending,
            developer_password="same-password-123",
            enigma_profile_secret="BLUECIPHER",
            admin_password="same-password-123",
            now=NOW,
        )


def test_bootstrap_finalization_hashes_all_three_secrets():
    authority = FakeBootstrapAuthority()
    service = FirstAdminBootstrapService(authority=authority, mail_gateway=MemoryMailGateway(), otp_pepper=b"p" * 32)
    pending = PendingBootstrap("p", "e", "c", "corr", NOW.isoformat())
    service.finalize(
        pending,
        developer_password="developer-password-123",
        enigma_profile_secret="BLUECIPHER",
        admin_password="admin-password-456",
        now=NOW,
    )
    values = authority.finalized
    assert "developer-password-123" not in values["developer_password_verifier"]
    assert "admin-password-456" not in values["admin_password_verifier"]
    assert "BLUECIPHER" not in values["enigma_secret_verifier"]


class FakeDeveloperEnigma:
    def expected_signature(self, *, lookup_index: int, **kwargs):
        return f"{lookup_index}LOOKUP"

    @staticmethod
    def verify(response, expected_signature):
        normalized = "".join(str(response).strip().upper().split())
        return normalized == str(expected_signature).upper()


class FakeRuntimeAuthority:
    def __init__(self):
        self.audit = []
        self.principal = {
            "principalId": "principal:first",
            "username": "alex",
            "identityType": "nexadevs_developer",
            "accountState": "ACTIVE",
            "passwordVerifier": hash_password("developer-password-123"),
            "enigmaProfileId": "enigma-profile:1",
            "permissions": (
                "NEXILABS.ADMIN.ELEVATE",
                "NEXILABS.AUDIT.READ",
            ),
        }
        self.binding = {
            "adminOperatorId": "admin-operator:1",
            "adminDeveloperId": "NEXADEV-ADM-000001",
            "emailId": "email:first",
            "emailAddress": "real.admin@example.com",
            "adminPasswordVerifier": hash_password("admin-password-456"),
            "enigmaProfileId": "enigma-profile:1",
            "enigmaSecretVerifier": hash_password("BLUECIPHER"),
            "permissions": self.principal["permissions"],
        }

    def principal_for_password_auth(self, username):
        key = username.casefold()
        return dict(self.principal) if key in {"alex", "nexadev-adm-000001"} else None

    def enigma_catalogue_row(self, **kwargs):
        return {
            "catalogueId": "cat",
            "words": ("CAT", "DOG", "OWL"),
            "sourceSha256": "a" * 64,
        }

    def append_runtime_audit(self, **kwargs):
        self.audit.append(kwargs)
        return "audit:1"

    def active_admin_binding(self, principal_id):
        return dict(self.binding) if principal_id == "principal:first" else None


def _service(authority=None, now=lambda: NOW):
    return ProductionAdminAuthenticationService(
        authority=authority or FakeRuntimeAuthority(),
        developer_enigma=FakeDeveloperEnigma(),
        now=now,
    )


def _logged_in_service(authority=None, now=lambda: NOW):
    service = _service(authority=authority, now=now)
    result = service.start_developer(username="alex", password="developer-password-123", runtime="production")
    # CAT+DOG+OWL = 9 letters; 9 + day 15 = lookup index 24.
    session = service.verify_developer(attempt_id=result["attemptId"], response="24LOOKUP")
    return service, session


def _elevate(service, session, *, response="24BLUECIPHER"):
    started = service.start_admin_elevation(
        session["sessionId"],
        admin_email="real.admin@example.com",
        admin_password="admin-password-456",
    )
    return service.verify_admin_elevation(
        session["sessionId"],
        attempt_id=started["attemptId"],
        response=response,
    )


def test_production_primary_auth_rejects_simulation_runtime():
    service = _service()
    with pytest.raises(Exception, match="production runtime"):
        service.start_developer(username="alex", password="developer-password-123", runtime="simulation")


def test_production_primary_auth_issues_postgresql_enigma_challenge():
    service = _service()
    result = service.start_developer(username="alex", password="developer-password-123", runtime="production")
    assert result["attemptId"].startswith("prod-auth:")
    assert result["challenge"]["words"] == ["CAT", "DOG", "OWL"]


def test_production_developer_enigma_uses_private_lookup_word_not_admin_secret():
    service = _service()
    result = service.start_developer(username="alex", password="developer-password-123", runtime="production")
    session = service.verify_developer(attempt_id=result["attemptId"], response="24LOOKUP")
    assert session["sessionId"].startswith("prod-session:")
    assert session["authenticationStrength"] == "developer_password_enigma"


def test_production_developer_enigma_rejects_admin_bootstrap_secret():
    service = _service()
    result = service.start_developer(username="alex", password="developer-password-123", runtime="production")
    with pytest.raises(Exception, match="invalid Enigma response"):
        service.verify_developer(attempt_id=result["attemptId"], response="24BLUECIPHER")


def test_admin_eligibility_requires_active_binding_and_permission():
    service, session = _logged_in_service()
    eligibility = service.eligibility(session["sessionId"])
    assert eligibility.eligible is True
    assert eligibility.admin_developer_id == "NEXADEV-ADM-000001"
    assert eligibility.bound_email_hint != "real.admin@example.com"


def test_admin_login_requires_bound_email_before_enigma_is_issued():
    service, session = _logged_in_service()
    with pytest.raises(Exception, match="invalid Admin elevation credentials"):
        service.start_admin_elevation(
            session["sessionId"],
            admin_email="other@example.com",
            admin_password="admin-password-456",
        )
    assert service.runtime._admin_attempts == {}


def test_admin_login_requires_separate_admin_password_before_enigma_is_issued():
    service, session = _logged_in_service()
    with pytest.raises(Exception, match="invalid Admin elevation credentials"):
        service.start_admin_elevation(
            session["sessionId"],
            admin_email="real.admin@example.com",
            admin_password="developer-password-123",
        )
    assert service.runtime._admin_attempts == {}


def test_admin_credentials_issue_fresh_shared_enigma_challenge():
    service, session = _logged_in_service()
    result = service.start_admin_elevation(
        session["sessionId"],
        admin_email="real.admin@example.com",
        admin_password="admin-password-456",
    )
    assert result["attemptId"].startswith("admin-auth:")
    assert result["challenge"]["words"] == ["CAT", "DOG", "OWL"]
    assert service.runtime._elevations == {}


def test_admin_enigma_requires_bootstrap_secret_and_creates_short_lived_elevation():
    service, session = _logged_in_service()
    elevation = _elevate(service, session)
    assert elevation.elevation_id.startswith("admin-elevation:")
    assert elevation.admin_operator_id == "admin-operator:1"
    assert "NEXILABS.ADMIN.ELEVATE" in elevation.permissions


def test_admin_enigma_rejects_developer_lookup_word():
    service, session = _logged_in_service()
    started = service.start_admin_elevation(
        session["sessionId"],
        admin_email="real.admin@example.com",
        admin_password="admin-password-456",
    )
    with pytest.raises(Exception, match="invalid Admin Enigma response"):
        service.verify_admin_elevation(
            session["sessionId"],
            attempt_id=started["attemptId"],
            response="24LOOKUP",
        )


def test_logout_revokes_base_session_related_admin_attempt_and_elevation():
    service, session = _logged_in_service()
    started = service.start_admin_elevation(
        session["sessionId"],
        admin_email="real.admin@example.com",
        admin_password="admin-password-456",
    )
    assert service.logout(session["sessionId"]) is True
    assert service.runtime._admin_attempts == {}
    with pytest.raises(Exception, match="session unavailable"):
        service.session(session["sessionId"])
    with pytest.raises(Exception, match="session unavailable"):
        service.verify_admin_elevation(
            session["sessionId"], attempt_id=started["attemptId"], response="24BLUECIPHER"
        )


def test_production_primary_auth_accepts_admin_developer_id_as_layer1_identifier():
    service = _service()
    result = service.start_developer(
        username="NEXADEV-ADM-000001",
        password="developer-password-123",
        runtime="production",
    )
    assert result["attemptId"].startswith("prod-auth:")


def test_require_elevation_enforces_exact_permission():
    service, session = _logged_in_service()
    elevation = _elevate(service, session)
    granted = service.require_elevation(
        session["sessionId"], elevation.elevation_id, "NEXILABS.AUDIT.READ"
    )
    assert granted.elevation_id == elevation.elevation_id
    with pytest.raises(Exception, match="Admin permission denied"):
        service.require_elevation(
            session["sessionId"], elevation.elevation_id, "NEXILABS.DEVELOPER_SETUP.ISSUE"
        )


def test_expired_admin_elevation_is_denied_and_audited():
    clock = {"now": NOW}
    authority = FakeRuntimeAuthority()
    service, session = _logged_in_service(authority=authority, now=lambda: clock["now"])
    elevation = _elevate(service, session)
    clock["now"] = NOW + timedelta(minutes=11)
    with pytest.raises(Exception, match="Admin elevation expired"):
        service.require_elevation(
            session["sessionId"], elevation.elevation_id, "NEXILABS.AUDIT.READ"
        )
    assert any(item["event_type"] == "ADMIN_ELEVATION_EXPIRED" for item in authority.audit)


class FailingSuccessAuditAuthority(FakeRuntimeAuthority):
    def __init__(self):
        super().__init__()
        self.fail_event_type = None

    def append_runtime_audit(self, **kwargs):
        if kwargs.get("event_type") == self.fail_event_type:
            raise RuntimeError("audit authority unavailable")
        return super().append_runtime_audit(**kwargs)


def test_developer_session_is_removed_if_success_audit_cannot_be_committed():
    authority = FailingSuccessAuditAuthority()
    service = _service(authority=authority)
    result = service.start_developer(
        username="alex",
        password="developer-password-123",
        runtime="production",
    )
    authority.fail_event_type = "DEVELOPER_AUTH_SUCCEEDED"
    with pytest.raises(RuntimeError, match="audit authority unavailable"):
        service.verify_developer(attempt_id=result["attemptId"], response="24LOOKUP")
    assert service.runtime._sessions == {}


def test_admin_elevation_is_removed_if_success_audit_cannot_be_committed():
    authority = FailingSuccessAuditAuthority()
    service, session = _logged_in_service(authority=authority)
    started = service.start_admin_elevation(
        session["sessionId"],
        admin_email="real.admin@example.com",
        admin_password="admin-password-456",
    )
    authority.fail_event_type = "ADMIN_ELEVATION_SUCCEEDED"
    with pytest.raises(RuntimeError, match="audit authority unavailable"):
        service.verify_admin_elevation(
            session["sessionId"],
            attempt_id=started["attemptId"],
            response="24BLUECIPHER",
        )
    assert service.runtime._elevations == {}
