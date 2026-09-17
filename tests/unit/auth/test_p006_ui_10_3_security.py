from backend.auth.first_admin_bootstrap.security import (
    canonical_json_bytes,
    normalize_email,
    normalize_enigma_secret,
    otp_verifier,
    receipt_sha256,
    safe_email_hint,
    split_enigma_response,
    verify_otp,
)


def test_otp_verifier_never_contains_raw_otp():
    value = otp_verifier(pepper=b"p" * 32, challenge_id="challenge:1", otp="123456")
    assert len(value) == 64
    assert "123456" not in value


def test_otp_verifier_is_challenge_bound():
    a = otp_verifier(pepper=b"p" * 32, challenge_id="challenge:1", otp="123456")
    b = otp_verifier(pepper=b"p" * 32, challenge_id="challenge:2", otp="123456")
    assert a != b


def test_verify_otp_rejects_wrong_code():
    expected = otp_verifier(pepper=b"p" * 32, challenge_id="challenge:1", otp="123456")
    assert verify_otp(pepper=b"p" * 32, challenge_id="challenge:1", otp="654321", expected=expected) is False


def test_enigma_secret_is_alphabetic_and_normalized():
    assert normalize_enigma_secret("  bluecipher  ") == "BLUECIPHER"


def test_enigma_response_separates_lookup_index_from_secret():
    assert split_enigma_response("17bluecipher", 17) == "BLUECIPHER"
    assert split_enigma_response("18bluecipher", 17) is None


def test_receipt_hash_is_order_stable():
    assert receipt_sha256({"b": 2, "a": 1}) == receipt_sha256({"a": 1, "b": 2})
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_email_hint_does_not_return_full_local_part():
    assert safe_email_hint("alexandra@example.com") == "a*******a@example.com"
    assert normalize_email("  Alex@Example.COM ") == "alex@example.com"
