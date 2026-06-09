"""Outbound email replies via Resend."""

from __future__ import annotations

import base64

import resend

from emailssh.config import Config
from emailssh.log import log_error


def _reply_subject(subject: str) -> str:
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def send_reply(to: str, subject: str, body: str, cfg: Config) -> None:
    """Send a plain-text reply; logs errors and never raises."""
    params: resend.Emails.SendParams = {
        "from": cfg.resend.from_address,
        "to": [to],
        "subject": _reply_subject(subject),
        "text": body,
    }

    try:
        resend.Emails.send(params)
    except Exception as exc:
        log_error(f"Resend send failed: {exc}")


def send_reply_with_attachment(
    to: str,
    subject: str,
    body: str,
    attachment: bytes,
    filename: str,
    cfg: Config,
) -> None:
    """Send a plain-text reply with a single attachment; logs errors and never raises."""
    params: resend.Emails.SendParams = {
        "from": cfg.resend.from_address,
        "to": [to],
        "subject": _reply_subject(subject),
        "text": body,
        "attachments": [
            {
                "filename": filename,
                "content": base64.b64encode(attachment).decode(),
            }
        ],
    }

    try:
        resend.Emails.send(params)
    except Exception as exc:
        log_error(f"Resend send (with attachment) failed: {exc}")
