"""Persistent PowerShell sessions keyed by normalised email subject."""

from __future__ import annotations

import queue
import re
import subprocess
import threading
import time

_SENTINEL = "__EMAILSSH_DONE__"


def _normalize_subject(subject: str) -> str:
    """Strip Re:/Fwd: chains, lowercase, strip whitespace."""
    s = subject.strip()
    s = re.sub(r"^(re|fwd?):\s*", "", s, flags=re.IGNORECASE)
    return s.strip().lower()


class PersistentTerminal:
    def __init__(self, subject_key: str) -> None:
        self.subject_key = subject_key
        self._proc = self._spawn()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _spawn(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            ["powershell.exe", "-NoLogo", "-NoExit", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def _read_loop(self) -> None:
        assert self._proc.stdout is not None
        try:
            for line in self._proc.stdout:
                self._queue.put(line)
        finally:
            self._queue.put(None)

    @property
    def alive(self) -> bool:
        return self._proc.returncode is None

    def run(self, command: str, timeout: int = 30) -> str:
        if not self.alive:
            return "[Terminal process has exited. Use !summon_terminal to restart.]"

        with self._lock:
            try:
                assert self._proc.stdin is not None
                self._proc.stdin.write(command + "\n")
                self._proc.stdin.write(f'Write-Host "{_SENTINEL}"\n')
                self._proc.stdin.flush()

                lines: list[str] = []
                deadline = time.monotonic() + timeout

                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        lines.append(f"\n[TIMEOUT: command exceeded {timeout}s]")
                        break
                    try:
                        line = self._queue.get(timeout=min(remaining, 1.0))
                    except queue.Empty:
                        continue
                    if line is None:
                        lines.append("\n[Terminal process exited]")
                        break
                    if line.rstrip("\r\n") == _SENTINEL:
                        break
                    lines.append(line)

                return "".join(lines).rstrip("\n")
            except Exception as exc:
                return f"[Terminal error: {exc}]"

    def kill(self) -> None:
        try:
            self._proc.terminate()
        except Exception:
            pass


class TerminalStore:
    def __init__(self) -> None:
        self._terminals: dict[str, PersistentTerminal] = {}

    def normalize(self, subject: str) -> str:
        return _normalize_subject(subject)

    def get(self, subject: str) -> PersistentTerminal | None:
        key = self.normalize(subject)
        term = self._terminals.get(key)
        if term is not None and not term.alive:
            del self._terminals[key]
            return None
        return term

    def summon(self, subject: str) -> tuple[PersistentTerminal, bool]:
        """Create or return terminal. Returns (terminal, is_new)."""
        key = self.normalize(subject)
        existing = self._terminals.get(key)
        if existing is not None and existing.alive:
            return existing, False
        term = PersistentTerminal(subject_key=key)
        self._terminals[key] = term
        return term, True

    def kill(self, subject: str) -> bool:
        key = self.normalize(subject)
        term = self._terminals.pop(key, None)
        if term:
            term.kill()
            return True
        return False
