"""Resend inbound email polling and normalisation."""

from __future__ import annotations

import html
from html.parser import HTMLParser
from typing import Any

import resend

from emailssh.config import Config
from emailssh.log import log_error


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _get_field(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _extract_items(response: Any) -> list[Any]:
    if response is None:
        return []

    data = _get_field(response, "data")
    if data is not None:
        if isinstance(data, list):
            return data
        return list(data)

    if isinstance(response, list):
        return response

    return []


def _html_to_text(html_content: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html_content)
    return html.unescape(parser.get_text()).strip()


def _extract_body(text: str | None, html_content: str | None) -> str:
    if text and text.strip():
        return text
    if html_content and html_content.strip():
        return _html_to_text(html_content)
    return ""


def _normalize_recipients(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.lower()]
    return [str(item).lower() for item in value]


def _normalize_email(
    summary: Any,
    full: Any,
    inbound_address: str,
) -> dict[str, str] | None:
    email_id = _get_field(full, "id") or _get_field(summary, "id")
    if not email_id:
        return None

    recipients = _normalize_recipients(
        _get_field(full, "to") or _get_field(summary, "to")
    )
    if inbound_address not in recipients:
        return None

    from_address = (
        _get_field(full, "from_")
        or _get_field(full, "from")
        or _get_field(summary, "from_")
        or _get_field(summary, "from")
        or ""
    )
    subject = _get_field(full, "subject") or _get_field(summary, "subject") or ""
    received_at = (
        _get_field(full, "created_at")
        or _get_field(summary, "created_at")
        or ""
    )
    body = _extract_body(
        _get_field(full, "text"),
        _get_field(full, "html"),
    )

    return {
        "id": str(email_id),
        "from": str(from_address),
        "subject": str(subject),
        "body": body,
        "received_at": str(received_at),
    }


class ResendReceiver:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        resend.api_key = cfg.resend.api_key

    def poll(self) -> list[dict[str, str]]:
        """List inbound emails and fetch full details for matching recipients."""
        response = resend.Emails.Receiving.list()
        items = _extract_items(response)
        inbound = self._cfg.agent.inbound_address.lower()
        emails: list[dict[str, str]] = []

        for summary in items:
            email_id = _get_field(summary, "id")
            if not email_id:
                continue

            recipients = _normalize_recipients(_get_field(summary, "to"))
            if inbound not in recipients:
                continue

            try:
                full = resend.Emails.Receiving.get(email_id=str(email_id))
            except Exception as exc:
                log_error(f"Resend get failed for {email_id}: {exc}")
                continue

            normalized = _normalize_email(summary, full, inbound)
            if normalized is not None:
                emails.append(normalized)

        return emails
