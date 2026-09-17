from backend.auth.first_admin_bootstrap.contracts import (
    ADMIN_DEVELOPER_ID_PREFIX,
    ADMIN_DEVELOPER_ID_WIDTH,
    ADMIN_PERMISSION_CODES,
    BootstrapIdentityInput,
    OTP_LENGTH,
    OTP_MAX_ATTEMPTS,
    OTP_MAX_RESENDS,
    OTP_RESEND_COOLDOWN_SECONDS,
    OTP_TTL_SECONDS,
)


def test_admin_id_contract_is_stable_v1():
    assert ADMIN_DEVELOPER_ID_PREFIX == "NEXADEV-ADM-"
    assert ADMIN_DEVELOPER_ID_WIDTH == 6


def test_otp_policy_is_server_side_and_bounded():
    assert (OTP_LENGTH, OTP_TTL_SECONDS, OTP_MAX_ATTEMPTS, OTP_RESEND_COOLDOWN_SECONDS, OTP_MAX_RESENDS) == (6, 600, 5, 60, 3)


def test_first_admin_permissions_are_exact_and_nonempty():
    assert ADMIN_PERMISSION_CODES == (
        "NEXILABS.ADMIN.ELEVATE",
        "NEXILABS.ADMIN_OPERATOR.MANAGE",
        "NEXILABS.DEVELOPER_REQUEST.REVIEW",
        "NEXILABS.DEVELOPER_SETUP.ISSUE",
        "NEXILABS.ENIGMA.GOVERN",
        "NEXILABS.AUDIT.READ",
    )


def test_identity_input_requires_real_email_shape():
    value = BootstrapIdentityInput("alex", "Alex", "Nexa", "alex@example.com")
    assert value.admin_email == "alex@example.com"


def test_identity_input_rejects_bad_email():
    try:
        BootstrapIdentityInput("alex", "Alex", "Nexa", "not-an-email")
    except ValueError as exc:
        assert "email" in str(exc).lower()
    else:
        raise AssertionError("invalid email accepted")


def test_first_admin_finalization_serializes_on_allocator_before_count():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[3] / "backend" / "auth" / "first_admin_bootstrap" / "postgresql.py").read_text(encoding="utf-8")
    lock = "allocator_key='ADMIN_DEVELOPER_ID' FOR UPDATE"
    count = "SELECT COUNT(*) FROM nexilabs_auth.admin_operator"
    finalization = source.index("def finalize_first_admin")
    lock_pos = source.index(lock, finalization)
    count_pos = source.index(count, finalization)
    assert lock_pos < count_pos
