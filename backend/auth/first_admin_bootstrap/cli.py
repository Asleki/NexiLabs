"""Protected-terminal first Admin bootstrap CLI for P006.UI.10.3."""
from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
import secrets
import sys

from .contracts import BootstrapIdentityInput, BootstrapRejected, MailDeliveryError
from .mail import SmtpMailGateway, SmtpMailSettings
from .postgresql import DatabaseSettings, PostgreSQLFirstAdminAuthority, psycopg_connect_factory
from .service import FirstAdminBootstrapService


def _required_env(name: str, default: str = "") -> str:
    return str(os.environ.get(name, default)).strip()


def _database_settings() -> DatabaseSettings:
    password = os.environ.get("PGPASSWORD") or getpass("PostgreSQL password: ")
    return DatabaseSettings(
        host=_required_env("PGHOST"),
        port=int(_required_env("PGPORT", "5432")),
        database_name=_required_env("PGDATABASE"),
        username=_required_env("PGUSER"),
        password=password,
        ssl_mode=_required_env("PGSSLMODE", "require"),
    )


def _mail_gateway() -> SmtpMailGateway:
    username = _required_env("NEXILABS_SMTP_USERNAME", "nexatech.core@gmail.com")
    password = os.environ.get("NEXILABS_SMTP_PASSWORD") or getpass(
        f"SMTP app password for {username}: "
    )
    return SmtpMailGateway(
        SmtpMailSettings(
            host=_required_env("NEXILABS_SMTP_HOST", "smtp.gmail.com"),
            port=int(_required_env("NEXILABS_SMTP_PORT", "465")),
            username=username,
            password=password,
            sender_email=_required_env("NEXILABS_SMTP_SENDER", "nexatech.core@gmail.com"),
            sender_name=_required_env("NEXILABS_SMTP_SENDER_NAME", "NexiLabs"),
            use_ssl=_required_env("NEXILABS_SMTP_USE_SSL", "true").lower() not in {"0", "false", "no"},
        )
    )


def _confirmed_secret(label: str) -> str:
    first = getpass(f"{label}: ")
    second = getpass(f"Confirm {label.lower()}: ")
    if first != second:
        raise BootstrapRejected(f"{label} confirmation does not match")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Protected terminal bootstrap for the first NexiLabs Admin-linked NexaDevs principal."
    )
    parser.add_argument(
        "--acknowledge-production-bootstrap",
        action="store_true",
        help="Required explicit acknowledgement. No secret values are accepted as command-line arguments.",
    )
    args = parser.parse_args(argv)
    if not args.acknowledge_production_bootstrap:
        parser.error("--acknowledge-production-bootstrap is required")

    settings = _database_settings()
    authority = PostgreSQLFirstAdminAuthority(
        psycopg_connect_factory(settings),
        database_name=settings.database_name,
    )
    if authority.count_admin_operators() != 0:
        raise BootstrapRejected("first Admin bootstrap refused: an Admin Operator already exists")

    print("\n=== P006.UI.10.3 FIRST ADMIN BOOTSTRAP ===")
    print(json.dumps(settings.safe_summary(), indent=2, sort_keys=True))
    print("No password, OTP, Enigma secret, verifier payload or SMTP credential will be printed.\n")

    identity = BootstrapIdentityInput(
        username=input("NexaDevs username: ").strip(),
        first_name=input("First name: ").strip(),
        last_name=input("Last name: ").strip(),
        admin_email=input("Real Admin email to verify: ").strip(),
    )

    service = FirstAdminBootstrapService(
        authority=authority,
        mail_gateway=_mail_gateway(),
        otp_pepper=secrets.token_bytes(32),
    )
    pending = service.begin(identity)
    print(f"\nOTP sent to the real Admin email. Challenge expires at {pending.expires_at}.")
    print("Type RESEND instead of a code to request a replacement OTP (policy limits apply).")

    while True:
        value = input("Email OTP: ").strip()
        if value.casefold() == "resend":
            service.resend(pending)
            print("Replacement OTP sent.")
            continue
        if service.verify_email(pending, value):
            print("Admin email verified.")
            break
        print("OTP rejected. Check the code/expiry and try again if attempts remain.")

    print("\nEstablish Layer 1 Developer credentials and the separate Layer 2 Admin password.")
    developer_password = _confirmed_secret("Developer password")
    enigma_secret = _confirmed_secret("Production Enigma profile secret (8-64 letters)")
    admin_password = _confirmed_secret("Separate Admin password")

    receipt = service.finalize(
        pending,
        developer_password=developer_password,
        enigma_profile_secret=enigma_secret,
        admin_password=admin_password,
    )
    print("\n=== FIRST ADMIN BOOTSTRAP RECEIPT (NON-SECRET) ===")
    print(json.dumps(receipt.as_dict(), indent=2, sort_keys=True))
    print("\nBootstrap committed. Keep the receipt as qualification evidence.")
    return 0


def entrypoint() -> None:
    try:
        raise SystemExit(main())
    except (BootstrapRejected, MailDeliveryError, ValueError, RuntimeError) as exc:
        print(f"BOOTSTRAP REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    entrypoint()
