"""TOML configuration loading and validation."""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from emailssh.log import log_warn


@dataclass(frozen=True)
class AgentConfig:
    id: str
    inbound_address: str
    poll_interval_seconds: int
    command_timeout_seconds: int


@dataclass(frozen=True)
class AuthConfig:
    allowed_senders: list[str]
    shared_secret: str


@dataclass(frozen=True)
class ResendConfig:
    api_key: str
    from_address: str


@dataclass(frozen=True)
class Config:
    agent: AgentConfig
    auth: AuthConfig
    resend: ResendConfig


def _config_paths() -> list[Path]:
    return [
        Path.cwd() / "config.toml",
        Path.home() / ".emailssh" / "config.toml",
    ]


def load_config() -> Config:
    config_path: Path | None = None
    for path in _config_paths():
        if path.is_file():
            config_path = path
            break

    if config_path is None:
        searched = "\n  ".join(str(p) for p in _config_paths())
        raise SystemExit(
            "EmailSSH config not found. Create config.toml in the current directory "
            f"or at ~/.emailssh/config.toml.\n\nSearched:\n  {searched}\n\n"
            "Copy config.example.toml to config.toml and fill in your values."
        )

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    try:
        agent_raw = raw["agent"]
        auth_raw = raw["auth"]
        resend_raw = raw["resend"]
    except KeyError as exc:
        raise SystemExit(f"Missing required config section: [{exc.args[0]}]") from exc

    shared_secret = str(auth_raw["shared_secret"])
    if len(shared_secret) < 16:
        raise SystemExit(
            "auth.shared_secret must be at least 16 characters. "
            "Use a long random string in config.toml."
        )

    poll_interval = int(agent_raw.get("poll_interval_seconds", 5))
    if poll_interval < 3:
        log_warn(
            f"poll_interval_seconds is {poll_interval}s (below 3s). "
            "Resend rate limits may apply."
        )

    return Config(
        agent=AgentConfig(
            id=str(agent_raw["id"]),
            inbound_address=str(agent_raw["inbound_address"]).lower(),
            poll_interval_seconds=poll_interval,
            command_timeout_seconds=int(agent_raw.get("command_timeout_seconds", 30)),
        ),
        auth=AuthConfig(
            allowed_senders=[
                str(addr).lower() for addr in auth_raw["allowed_senders"]
            ],
            shared_secret=shared_secret,
        ),
        resend=ResendConfig(
            api_key=str(resend_raw["api_key"]),
            from_address=str(resend_raw["from_address"]),
        ),
    )
