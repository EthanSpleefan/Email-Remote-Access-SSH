"""Persistent store of processed inbound email IDs."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


_MAX_ENTRIES = 10_000
_RETENTION_DAYS = 7


class SeenEmailStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.cwd() / ".seen_emails.json"
        self._entries: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            self._entries = {}
            return

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._entries = {}
            return

        if not isinstance(raw, list):
            self._entries = {}
            return

        entries: dict[str, str] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            email_id = item.get("id")
            seen_at = item.get("seen_at")
            if isinstance(email_id, str) and isinstance(seen_at, str):
                entries[email_id] = seen_at

        self._entries = entries
        self._prune_old()
        self._enforce_cap()

    def _save(self) -> None:
        payload = [
            {"id": email_id, "seen_at": seen_at}
            for email_id, seen_at in sorted(
                self._entries.items(), key=lambda item: item[1]
            )
        ]
        self._path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def _prune_old(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
        pruned: dict[str, str] = {}
        for email_id, seen_at in self._entries.items():
            try:
                seen_dt = datetime.fromisoformat(seen_at)
                if seen_dt.tzinfo is None:
                    seen_dt = seen_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if seen_dt >= cutoff:
                pruned[email_id] = seen_at
        self._entries = pruned

    def _enforce_cap(self) -> None:
        if len(self._entries) <= _MAX_ENTRIES:
            return
        sorted_items = sorted(self._entries.items(), key=lambda item: item[1])
        self._entries = dict(sorted_items[-_MAX_ENTRIES:])

    def is_seen(self, email_id: str) -> bool:
        return email_id in self._entries

    def mark_seen(self, email_id: str) -> None:
        self._entries[email_id] = datetime.now(timezone.utc).isoformat()
        self._enforce_cap()
        self._save()
