"""Structured stdout logging for the EmailSSH agent."""

from __future__ import annotations

from datetime import datetime


def _emit(level: str, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} [{level:<5}] {message}")


def log_info(message: str) -> None:
    _emit("INFO", message)


def log_cmd(message: str) -> None:
    _emit("CMD", message)


def log_exec(message: str) -> None:
    _emit("EXEC", message)


def log_sent(message: str) -> None:
    _emit("SENT", message)


def log_warn(message: str) -> None:
    _emit("WARN", message)


def log_error(message: str) -> None:
    _emit("ERROR", message)
