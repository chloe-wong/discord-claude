# discord-claude

Sends you a Discord DM whenever a Claude Code session finishes, so you get a
notification with a summary, the project, the account, and the machine it ran
on. This is a `Stop` hook: it runs after Claude finishes responding, reads the
hook payload from stdin, and posts a message via a Discord bot DM.

Everyone who wants this installs their own copy with their own bot token and
Discord user ID -- there's no shared/central bot. It's stdlib-only Python 3,
no dependencies.

## What the message looks like

```
✅ discord-claude finished -- `work` on `chloes-macbook.local`
session: `discord-claude · a1b2c3d4`
> Set up the Stop hook notifier and pushed the initial commit.
```

- **project**: basename of the session's working directory
- **account**: basename of `$CLAUDE_CONFIG_DIR` if you use one (see below), else `default`
- **machine**: hostname
- **session**: project + first 8 chars of the session ID
- **summary**: the final assistant message of the turn, truncated to ~500 chars

Token usage percentage was considered and dropped for v1 -- Claude Code's
`/usage` command has no scriptable/JSON equivalent, so there's nothing a hook
can read locally. Revisit later via a separate scheduled job against the
Anthropic Admin Usage API if needed; that's a different credential and a
different mechanism than this hook.

## Setup

### 1. Create a Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) > **New Application**.
2. **Bot** tab > **Reset Token** > copy it. This is `DISCORD_BOT_TOKEN`.
3. Under **Privileged Gateway Intents**, nothing extra is needed for DMs.
4. **OAuth2 > URL Generator**: scope `bot`, permission `Send Messages`. Open
   the generated URL and add the bot to any server you're also in (the bot
   must share a server with you to be able to DM you -- it never posts there,
   this is just how Discord allows bot-initiated DMs).

### 2. Get your Discord user ID

Discord app > **User Settings > Advanced > Developer Mode** (enable it) >
right-click your own name anywhere > **Copy User ID**. This is `DISCORD_USER_ID`.

### 3. Set environment variables

Add to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) on every machine
you want notifications from:

```sh
export DISCORD_BOT_TOKEN="..."
export DISCORD_USER_ID="..."
```

### 4. (Optional) Label multiple accounts

If you run multiple Claude accounts concurrently via separate
`CLAUDE_CONFIG_DIR`s, the notifier labels each message with that directory's
basename automatically:

```sh
export CLAUDE_CONFIG_DIR="$HOME/.claude-work"   # messages labeled "work"
```

No `CLAUDE_CONFIG_DIR` set -> messages are labeled `default`.

### 5. Clone this repo

```sh
git clone https://github.com/chloe-wong/discord-claude.git ~/Desktop/discord-claude
```

### 6. Register the hook

Merge the contents of [`settings.snippet.json`](./settings.snippet.json)
into your **user-scope** `~/.claude/settings.json` (not a project's
`.claude/settings.json` -- this should apply everywhere, and user scope keeps
your tokens out of any repo). If you cloned to a location other than
`~/Desktop/discord-claude`, update the `command` path accordingly.

### 7. Test manually before relying on the hook

```sh
echo '{"cwd":"'"$PWD"'","session_id":"test1234","last_assistant_message":"hello from a test run"}' \
  | DISCORD_BOT_TOKEN=$DISCORD_BOT_TOKEN DISCORD_USER_ID=$DISCORD_USER_ID python3 discord_notify.py
```

Run this from inside `~/Desktop/discord-claude` (it needs to be in the same
directory as `discord_notify.py`, or point python3 at the full path). You
should get a DM within a couple seconds, and no output in the terminal.

If nothing arrives, the terminal *will* show a `[discord-notify] ...` line
on stderr explaining why (bad token, bot not sharing a server with you,
invalid user ID, etc.) -- the script always exits 0 so it never blocks a
real Claude Code session, but it still logs failures to stderr, which
prints directly to your terminal in this command since nothing redirects it.

## Notes

- The hook never blocks the session and never raises: missing env vars,
  network failures, and malformed payloads are all logged to stderr and
  swallowed, so a broken Discord setup can't break Claude Code.
- Hook stdout/stderr isn't shown in the Claude Code UI -- it only goes to the
  debug log -- so failures are silent unless you run the script manually to
  check.
