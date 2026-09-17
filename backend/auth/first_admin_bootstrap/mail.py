"""Provider-neutral real-email gateway for P006.UI.10.3."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
import smtplib
import ssl

from .contracts import MailDeliveryError


@dataclass(frozen=True, slots=True)
class SmtpMailSettings:
    host: str = "smtp.gmail.com"
    port: int = 465
    username: str = "nexatech.core@gmail.com"
    password: str = ""
    sender_email: str = "nexatech.core@gmail.com"
    sender_name: str = "NexiLabs"
    use_ssl: bool = True

    def __post_init__(self) -> None:
        if not self.host.strip() or not self.username.strip() or not self.password:
            raise ValueError("SMTP host, username and password are required")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("SMTP port is invalid")
        if "@" not in self.sender_email:
            raise ValueError("SMTP sender email is invalid")


class SmtpMailGateway:
    """SMTP implementation. Provider credentials stay outside Git and PostgreSQL."""

    def __init__(self, settings: SmtpMailSettings):
        self.settings = settings

    def send_email_verification_otp(
        self,
        *,
        recipient: str,
        otp: str,
        expires_at: datetime,
        correlation_id: str,
    ) -> str:
        recipient = str(recipient).strip()
        if "@" not in recipient or any(ch.isspace() for ch in recipient):
            raise MailDeliveryError("invalid OTP recipient email")

        message_id = make_msgid(domain="nexilabs.local")
        message = EmailMessage()
        message["From"] = f"{self.settings.sender_name} <{self.settings.sender_email}>"
        message["To"] = recipient
        message["Subject"] = "NexiLabs Admin email verification code"
        message["Message-ID"] = message_id
        message["X-NexiLabs-Correlation"] = correlation_id
        message.set_content(
            "NexiLabs email verification\n\n"
            f"Your one-time verification code is: {otp}\n\n"
            f"It expires at {expires_at.isoformat()}.\n"
            "Do not share this code. NexiLabs will never ask you to send it back by email.\n"
        )

        try:
            if self.settings.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.settings.host,
                    self.settings.port,
                    context=context,
                    timeout=20,
                ) as smtp:
                    smtp.login(self.settings.username, self.settings.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.settings.host, self.settings.port, timeout=20) as smtp:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.login(self.settings.username, self.settings.password)
                    smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailDeliveryError("email verification OTP delivery failed") from exc
        return message_id.strip("<>")


class MemoryMailGateway:
    """Deterministic test gateway; never selected by the Production CLI."""

    def __init__(self):
        self.messages: list[dict[str, object]] = []

    def send_email_verification_otp(self, *, recipient, otp, expires_at, correlation_id) -> str:
        reference = f"memory-mail-{len(self.messages) + 1}"
        self.messages.append(
            {
                "recipient": recipient,
                "otp": otp,
                "expiresAt": expires_at,
                "correlationId": correlation_id,
                "providerReference": reference,
            }
        )
        return reference
