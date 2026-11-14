"""Lớp gửi email trừu tượng: console (dev), SMTP hoặc Resend (prod)."""

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger("app.email")


@dataclass
class Email:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    async def send(self, email: Email) -> None: ...


class ConsoleSender:
    """Chỉ dùng ở dev: in email ra stdout (không qua logger để tránh bị che liên kết)."""

    def __init__(self) -> None:
        self.outbox: list[Email] = []

    async def send(self, email: Email) -> None:
        self.outbox.append(email)
        print(f"\n--- EMAIL to={email.to} ---\n{email.subject}\n\n{email.body}\n---\n", flush=True)


class SmtpSender:
    def __init__(self, s: Settings) -> None:
        self.s = s

    def _send_sync(self, email: Email) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.s.email_from, email.to, email.subject
        msg.set_content(email.body)
        with smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if self.s.smtp_user:
                smtp.login(self.s.smtp_user, self.s.smtp_password)
            smtp.send_message(msg)

    async def send(self, email: Email) -> None:
        await asyncio.to_thread(self._send_sync, email)


class ResendSender:
    def __init__(self, s: Settings) -> None:
        self.s = s

    async def send(self, email: Email) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.s.resend_api_key}"},
                json={
                    "from": self.s.email_from,
                    "to": [email.to],
                    "subject": email.subject,
                    "text": email.body,
                },
            )
            resp.raise_for_status()


@lru_cache
def get_email_sender() -> EmailSender:
    s = get_settings()
    if s.email_backend == "smtp":
        return SmtpSender(s)
    if s.email_backend == "resend":
        return ResendSender(s)
    return ConsoleSender()


async def send_email_safe(email: Email) -> None:
    """Gửi nền: lỗi gửi chỉ ghi log, không làm hỏng request đã commit."""
    try:
        await get_email_sender().send(email)
    except Exception as exc:  # noqa: BLE001
        logger.error("email_send_failed", extra={"error": type(exc).__name__})
