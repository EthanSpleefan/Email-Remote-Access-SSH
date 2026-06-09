"""In-memory session metrics (stateless command mode for phase 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class Session:
    started_at: datetime
    command_count: int = 0
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def _prune_stale(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        stale = [
            session_id
            for session_id, session in self._sessions.items()
            if session.last_seen_at < cutoff
        ]
        for session_id in stale:
            del self._sessions[session_id]

    def touch(self, session_id: str) -> Session:
        """Record activity for a session; one email equals one command in phase 1."""
        self._prune_stale()
        now = datetime.now(timezone.utc)
        session = self._sessions.get(session_id)
        if session is None:
            session = Session(started_at=now)
            self._sessions[session_id] = session
        session.command_count += 1
        session.last_seen_at = now
        return session
