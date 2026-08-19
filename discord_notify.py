#!/usr/bin/env python3
"""Claude Code Stop hook: DM a Discord summary when a session finishes.

Reads the Stop hook JSON payload from stdin. Requires DISCORD_BOT_TOKEN and
DISCORD_USER_ID in the environment; if either is missing, exits quietly
(no notification). Never blocks or fails the Claude Code session -- always
exits 0, logging problems to stderr only.

Env vars:
  DISCORD_BOT_TOKEN   Bot token, from the Discord Developer Portal.
  DISCORD_USER_ID     Your Discord user ID (the DM recipient).
  CLAUDE_CONFIG_DIR   Optional. If set, its basename is used as the account
                       label (e.g. ~/.claude-work -> "work"). Unset -> "default".
"""

import json
import os
import socket
import sys
import urllib.error
import urllib.request

DISCORD_API = "https://discord.com/api/v10"
SNIPPET_LIMIT = 500


def log_error(msg):
    sys.stderr.write(f"[discord-notify] {msg}\n")


def account_label():
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        return os.path.basename(os.path.normpath(os.path.expanduser(config_dir))) or "default"
    return "default"


def session_label(payload):
    cwd = payload.get("cwd") or ""
    project = os.path.basename(os.path.normpath(cwd)) if cwd else "unknown-project"
    session_id = payload.get("session_id") or ""
    short_id = session_id[:8] if session_id else "no-id"
    return f"{project} · {short_id}"


def build_message(payload):
    cwd = payload.get("cwd") or ""
    project = os.path.basename(os.path.normpath(cwd)) if cwd else "unknown-project"
    account = account_label()
    hostname = socket.gethostname()
    session = session_label(payload)
    snippet = (payload.get("last_assistant_message") or "").strip()
    if len(snippet) > SNIPPET_LIMIT:
        snippet = snippet[:SNIPPET_LIMIT].rstrip() + "…"

    lines = [
        f"✅ **{project}** finished -- `{account}` on `{hostname}`",
        f"session: `{session}`",
    ]
    if snippet:
        lines.append("\n".join(f"> {line}" for line in snippet.splitlines()))
    return "\n".join(lines)


def discord_request(path, token, body):
    req = urllib.request.Request(
        f"{DISCORD_API}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def notify(token, user_id, content):
    channel = discord_request("/users/@me/channels", token, {"recipient_id": user_id})
    discord_request(f"/channels/{channel['id']}/messages", token, {"content": content})


def main():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    user_id = os.environ.get("DISCORD_USER_ID")
    if not token or not user_id:
        log_error("DISCORD_BOT_TOKEN or DISCORD_USER_ID not set; skipping notification")
        return 0

    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        log_error(f"could not parse hook payload: {e}")
        return 0

    content = build_message(payload)

    try:
        notify(token, user_id, content)
    except urllib.error.HTTPError as e:
        log_error(f"Discord API error {e.code}: {e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        log_error(f"network error contacting Discord: {e.reason}")
    except Exception as e:  # noqa: BLE001 -- hook must never crash the session
        log_error(f"unexpected error: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
