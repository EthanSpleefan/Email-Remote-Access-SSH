# EmailSSH with RESEND

Remote command execution over email. Send a command to a Resend inbound address from any mail client; the Windows agent polls Resend, runs the command via `cmd.exe`, and replies with the output.

There is no HTTP server, webhook, tunnel, or IMAP only the [Resend](https://resend.com) Python SDK for send and receive.

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- A **Resend** account with inbound email enabled. Addresses on `@pixaibzi.resend.app` are available by default — no custom domain required.

## Setup

1. Clone this repository and open a terminal in the project directory.

2. Copy the example config and edit it:

   ```bash
   cp config.example.toml config.toml
   ```

3. Fill in `config.toml`:

   | Field | Description |
   |---|---|
   | `resend.api_key` | API key from the [Resend dashboard](https://resend.com/api-keys) |
   | `auth.allowed_senders` | Email addresses allowed to run commands |
   | `auth.shared_secret` | At least 16 characters; required on line 1 of every command email |
   | `agent.inbound_address` | Your Resend inbound address (e.g. `desktop01@pixaibzi.resend.app`) |
   | `resend.from_address` | Verified sending address for replies (often the same as inbound) |

4. Install dependencies:

   ```bash
   uv sync
   ```

## Running

Start the agent (leave it running on the machine you want to control):

```bash
uv run emailssh-agent
```

The agent polls Resend every few seconds (configurable), executes authorised commands, and sends replies.

## Sending a command

Send an email **to** your `inbound_address` from a whitelisted sender. The body must follow this format:

```
your-shared-secret-here
dir C:\Users
```

- **Line 1:** The shared secret (exact match, not passed to the shell).
- **Line 2+:** The command to run (multiline supported).

You receive a plain-text reply with stdout, stderr (if any), exit code, and duration.

## Security notes

- **Sender whitelist** — Only `From` addresses in `allowed_senders` are accepted. Others are logged and silently discarded (no reply).
- **Shared secret** — The first line of the body must match `shared_secret` using a timing-safe comparison. Wrong secrets are discarded without reply.
- **Transport visibility** — Email bodies pass through Resend. Treat the shared secret and command output as visible to your email provider.
- **Powerful by design** — Anyone who knows your secret and can send from a whitelisted address can run arbitrary commands on the host. Use a long random secret and lock down `allowed_senders`.

## Project layout

```
emailssh/
├── config.example.toml   # Template config
├── config.toml           # Your local config (not committed)
├── .seen_emails.json     # Auto-created processed-ID store
└── emailssh/             # Python package
```
