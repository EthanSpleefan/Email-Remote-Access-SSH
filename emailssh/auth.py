"""Sender whitelist and shared-secret verification."""

from __future__ import annotations

import hmac
import re


_DISPLAY_NAME_RE = re.compile(r"^(.+?)\s*<([^>]+)>$")


def _normalize_address(address: str) -> str:
    address = address.strip()
    match = _DISPLAY_NAME_RE.match(address)
    if match:
        return match.group(2).strip().lower()
    return address.lower()


def check_sender(from_address: str, allowed: list[str]) -> bool:
    """Return True if the sender is on the whitelist (case-insensitive)."""
    normalized = _normalize_address(from_address)
    allowed_normalized = {_normalize_address(addr) for addr in allowed}
    return normalized in allowed_normalized


def check_secret(body: str, secret: str) -> tuple[bool, str]:
    """Verify line 1 of the body matches the shared secret; return the command."""
    if not body:
        return False, ""

    if "\n" in body:
        first_line, remainder = body.split("\n", 1)
        command = remainder.lstrip("\r")
    else:
        first_line = body
        command = ""

    first_line = first_line.strip()
    secret = secret.strip()

    if hmac.compare_digest(first_line, secret):
        return True, command.strip()

    return False, ""
