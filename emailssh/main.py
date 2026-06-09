"""EmailSSH agent entry point."""

from __future__ import annotations

import sys
import time

import resend

from emailssh import auth
from emailssh.config import Config, load_config
from emailssh.executor import execute, format_output
from emailssh.log import log_cmd, log_error, log_exec, log_info, log_sent, log_warn
from emailssh.mailer import send_reply, send_reply_with_attachment
from emailssh.receiver import ResendReceiver
from emailssh.screenshot import capture as capture_screenshot
from emailssh.session import SessionStore
from emailssh.state import SeenEmailStore
from emailssh.terminal import TerminalStore


def _print_banner(cfg: Config) -> None:
    agent_id = cfg.agent.id
    inbound = cfg.agent.inbound_address
    interval = cfg.agent.poll_interval_seconds

    print("╔══════════════════════════════════════════╗")
    print("║  EmailSSH Agent                          ║")
    print(f"║  Agent ID : {agent_id:<27}║")
    print(f"║  Inbound  : {inbound:<27}║")
    print(f"║  Polling  : every {interval}s{' ' * (18 - len(str(interval)))}║")
    print("╚══════════════════════════════════════════╝")
    print(f"Send commands to: {inbound}")


def process_email(
    email: dict[str, str],
    cfg: Config,
    sessions: SessionStore,
    terminals: TerminalStore,
) -> None:
    sender = email["from"]
    subject = email["subject"]
    body = email["body"]

    if not auth.check_sender(sender, cfg.auth.allowed_senders):
        log_warn(f"Rejected email from {sender} (sender not in whitelist)")
        return

    ok, command = auth.check_secret(body, cfg.auth.shared_secret)
    if not ok:
        log_warn(f"Rejected email from {sender} (invalid shared secret)")
        return

    if not command:
        log_warn(f"Rejected email from {sender} (empty command)")
        return

    sessions.touch(email["id"])
    preview = command.replace("\n", " ")[:60]
    log_cmd(f'{sender} → "{preview}"')

    cmd = command.strip()

    if cmd == "!screenshot":
        png_bytes, err = capture_screenshot()
        if err:
            send_reply(sender, subject, f"Screenshot failed: {err}", cfg)
        else:
            send_reply_with_attachment(
                sender, subject, "Screenshot attached.", png_bytes, "screenshot.png", cfg
            )
        log_sent(f"Reply (screenshot) to {sender}")
        return

    if cmd == "!summon_terminal":
        term, is_new = terminals.summon(subject)
        msg = (
            f"Terminal spawned (key: {term.subject_key})."
            if is_new
            else f"Terminal already running (key: {term.subject_key}). Reply to this thread to send commands."
        )
        send_reply(sender, subject, msg, cfg)
        log_sent(f"Reply (summon_terminal) to {sender}")
        return

    if cmd == "!kill_terminal":
        killed = terminals.kill(subject)
        msg = "Terminal killed." if killed else "No active terminal for this subject."
        send_reply(sender, subject, msg, cfg)
        log_sent(f"Reply (kill_terminal) to {sender}")
        return

    term = terminals.get(subject)
    if term is not None:
        output = term.run(command, cfg.agent.command_timeout_seconds)
        send_reply(sender, subject, output, cfg)
        log_sent(f"Reply (terminal:{term.subject_key}) to {sender}")
        return

    result = execute(command, cfg.agent.command_timeout_seconds)
    log_exec(f"exit {result.returncode} | {result.duration_ms}ms")

    output = format_output(command, result, cfg.agent.id)
    send_reply(sender, subject, output, cfg)
    log_sent(f"Reply to {sender}")


def main() -> None:
    cfg = load_config()
    resend.api_key = cfg.resend.api_key

    receiver = ResendReceiver(cfg)
    seen = SeenEmailStore()
    sessions = SessionStore()
    terminals = TerminalStore()

    _print_banner(cfg)

    try:
        while True:
            try:
                log_info("Polling for new emails...")
                emails = receiver.poll()
                for email in emails:
                    if seen.is_seen(email["id"]):
                        continue
                    seen.mark_seen(email["id"])
                    process_email(email, cfg, sessions, terminals)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                log_error(f"Poll loop error: {exc}")
                time.sleep(cfg.agent.poll_interval_seconds * 3)
                continue

            time.sleep(cfg.agent.poll_interval_seconds)
    except KeyboardInterrupt:
        print("\nEmailSSH agent stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
