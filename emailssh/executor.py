"""Windows subprocess command execution."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    duration_ms: int


def execute(command: str, timeout: int) -> ExecutionResult:
    """Run a command via cmd.exe /c; never raises."""
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            ["cmd.exe", "/c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            returncode=completed.returncode,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            stdout=f"[TIMEOUT: command exceeded {timeout}s]",
            stderr="",
            returncode=-1,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            stdout="",
            stderr=str(exc),
            returncode=-2,
            duration_ms=duration_ms,
        )


def format_output(
    command: str,
    result: ExecutionResult,
    agent_id: str,
) -> str:
    """Format command output for the reply email body."""
    lines = [
        f"> {command}",
        "─────────────────────────────────",
        result.stdout.rstrip("\n"),
    ]

    if result.stderr:
        lines.extend(["", "[stderr]", result.stderr.rstrip("\n")])

    lines.append(
        f"\nexit: {result.returncode} | {result.duration_ms}ms | {agent_id}"
    )
    return "\n".join(lines)
