"""Secret-safe helpers for P006.UI.10.3."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import asdict, is_dataclass
from datetime import datetime

from .contracts import OTP_LENGTH


_ENIGMA_SECRET = re.compile(r"^[A-Za-z]{8,64}$")


def normalize_email(value: str) -> str:
    return str(value).strip().casefold()


def generate_otp() -> str:
    upper = 10**OTP_LENGTH
    return f"{secrets.randbelow(upper):0{OTP_LENGTH}d}"


def otp_verifier(*, pepper: bytes, challenge_id: str, otp: str) -> str:
    if not pepper or len(pepper) < 16:
        raise ValueError("OTP verifier key must contain at least 16 bytes")
    normalized = str(otp).strip()
    if len(normalized) != OTP_LENGTH or not normalized.isdigit():
        raise ValueError("OTP must be a six-digit value")
    message = f"{challenge_id}\0{normalized}".encode("utf-8")
    return hmac.new(pepper, message, hashlib.sha256).hexdigest()


def verify_otp(*, pepper: bytes, challenge_id: str, otp: str, expected: str) -> bool:
    try:
        actual = otp_verifier(pepper=pepper, challenge_id=challenge_id, otp=otp)
    except ValueError:
        return False
    return hmac.compare_digest(actual, str(expected))


def normalize_enigma_secret(value: str) -> str:
    secret = "".join(str(value).strip().split()).upper()
    if not _ENIGMA_SECRET.fullmatch(secret):
        raise ValueError("Enigma profile secret must contain 8-64 alphabetic characters")
    return secret


def normalize_enigma_response(value: str) -> str:
    return "".join(str(value).strip().split()).upper()


def split_enigma_response(response: str, expected_lookup_index: int) -> str | None:
    normalized = normalize_enigma_response(response)
    prefix = str(int(expected_lookup_index))
    if not normalized.startswith(prefix):
        return None
    candidate = normalized[len(prefix):]
    if not _ENIGMA_SECRET.fullmatch(candidate):
        return None
    return candidate


def canonical_json_bytes(value: object) -> bytes:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def receipt_sha256(value: object) -> str:
    return sha256_hex(canonical_json_bytes(value))


def safe_email_hint(email: str) -> str:
    local, sep, domain = normalize_email(email).partition("@")
    if not sep:
        return ""
    if len(local) <= 2:
        masked = local[:1] + "*"
    else:
        masked = local[:1] + ("*" * min(len(local) - 2, 8)) + local[-1:]
    return f"{masked}@{domain}"


def isoformat(value: datetime) -> str:
    return value.isoformat()
