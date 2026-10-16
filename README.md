# apple-bridge

Give an AI assistant a phone number. **apple-bridge** runs on a Mac that's signed in to iMessage and:

- **Receives iMessages.** It polls the local Messages database (read-only) for new texts from contacts you allow, then POSTs each one to a webhook (your bot, an automation platform, or a local LLM server).
- **Sends iMessages.** It drives Messages.app via AppleScript, either from the webhook's `reply` field or from a CLI or Python call.
- **Reads and writes Apple Calendar and Reminders.** It ships as a small [MCP](https://modelcontextprotocol.io) server scoped to one calendar and one reminders list that you choose.

It uses only the Python standard library, with no third-party dependencies.

## Requirements

- macOS (tested on Apple silicon, macOS 14/15), with Messages signed in to an Apple ID. A spare Apple ID for the bot is recommended.
- Python 3.10+ (`/usr/bin/python3` or Homebrew).
- macOS permissions, under System Settings → Privacy & Security:
  - **Full Disk Access** for whichever process reads `~/Library/Messages/chat.db` (Terminal, iTerm, or the `python3` binary launchd runs).
  - **Automation** for that process to control **Messages**, **Calendar** and **Reminders**. macOS asks the first time; approve it.
  - **Calendars / Reminders** access, if prompted.
- The Mac must stay awake and logged in, because Messages only syncs in a user session.

## Setup

```bash
git clone https://github.com/<you>/apple-bridge.git
cd apple-bridge
cp config.example.json config.json   # edit it
cp .env.example .env                 # optional, for secrets; never commit
```

Then:

1. Exchange one iMessage between the bot's Apple ID and each allowed contact, so the chat exists in `chat.db`.
2. Run `python3 -m apple_bridge.listener init`. This marks existing history as seen, so nothing old gets forwarded.
3. Run `python3 -m apple_bridge.listener once` to test, then `watch` to run continuously.

## Configuration

Settings come from `config.json`, and environment variables override it.

| Key | Env var | Meaning |
|---|---|---|
| `allowed_contacts` | `APPLE_BRIDGE_ALLOWED_CONTACTS` (comma list) | Phone numbers or Apple IDs whose messages are forwarded. Everyone else is ignored. |
| `webhook_url` | `APPLE_BRIDGE_WEBHOOK_URL` | Where each incoming message is POSTed |
| `webhook_headers` | `APPLE_BRIDGE_WEBHOOK_TOKEN` → `Authorization: Bearer …` | Extra headers for auth |
| `messages_db` | `APPLE_BRIDGE_MESSAGES_DB` | Defaults to `~/Library/Messages/chat.db` |
| `state_dir` | `APPLE_BRIDGE_STATE_DIR` | Where the last-seen state lives (default `./work`) |
| `poll_seconds` | `APPLE_BRIDGE_POLL_SECONDS` | Poll interval, 1–60 (default 3) |
| `calendar` | `APPLE_BRIDGE_CALENDAR` | The single calendar the MCP server may use |
| `reminders_list` | `APPLE_BRIDGE_REMINDERS_LIST` | The single Reminders list the MCP server may use |

`.env` isn't loaded automatically. Export it (`set -a; . ./.env; set +a`) or put the values in the launchd plist.

## Usage

**Send a message:**

```bash
python3 -m apple_bridge.imessage_send +447700900000 --text "Hello from the bot"
echo "multi-line body" | python3 -m apple_bridge.imessage_send someone@example.com
```

```python
from apple_bridge.imessage_send import send_imessage
send_imessage("+447700900000", "Build finished ✅")
```

**Listen and forward:**

```bash
python3 -m apple_bridge.listener watch    # or: once / status / init
```

**Run in the background with launchd:** edit the paths in `launchd/com.example.apple-bridge.plist`, then:

```bash
cp launchd/com.example.apple-bridge.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.apple-bridge.plist
```

Grant Full Disk Access to the exact `python3` path in the plist.

**Calendar and Reminders MCP server:** add it to your MCP client config (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "apple-calendar": {
      "command": "python3",
      "args": ["-m", "apple_bridge.calendar_mcp"],
      "cwd": "/PATH/TO/apple-bridge",
      "env": {"APPLE_BRIDGE_CALENDAR": "Assistant Shared", "APPLE_BRIDGE_REMINDERS_LIST": "Assistant Shared"}
    }
  }
}
```

The server's tools are `apple_setup_check`, `apple_calendar_list`, `apple_reminders_list`, `apple_calendar_create`, `apple_calendar_update`, `apple_reminder_create` and `apple_reminder_update`.

Tip: create a dedicated calendar (e.g. "Assistant Shared") and share it with your iCloud family. The assistant then only sees and edits that one calendar.

## Connecting an AI assistant (webhook)

For every new message from an allowed contact, the listener POSTs:

```json
{
  "from": "+447700900000",
  "name": "Alex",
  "text": "what's on tomorrow?",
  "guid": "…",
  "sent_at": "2026-01-01T09:00:00+00:00",
  "history": [{"role": "user", "content": "…"}, {"role": "assistant", "content": "…"}]
}
```

- Any 2xx response marks the message handled.
- If the response JSON has `{"reply": "text"}`, that text is sent back over iMessage straight away.
- An async assistant can return `{}` and reply later through `imessage_send`, e.g. over SSH to the Mac.
- A non-2xx response or a network error leaves the message unhandled, and it's retried on the next poll.

`examples/webhook_receiver.py` is a 30-line echo server for local testing. Replace `answer()` with a call to your model (OpenAI-compatible API, Ollama, etc.) or point `webhook_url` at your bot platform's inbound webhook.

## Security notes

- **Allow-list only.** Messages from anyone not in `allowed_contacts` are never read into the payload or forwarded. Group chats are ignored.
- `chat.db` is opened **read-only** (`mode=ro`, `query_only`).
- Full Disk Access is powerful, so grant it only to the interpreter that runs this.
- Use HTTPS and a bearer token for the webhook. Keep tokens in `.env` or the plist, never in git (`.gitignore` already covers `.env`, `config.json`, `*.db` and `work/`).
- Message text is untrusted input. If your assistant can take actions, don't let message content alone authorise sends, payments or deletions.
- The calendar server can only update items it created itself, and it can't delete anything.

## Limitations

- macOS only; it relies on AppleScript and the private `chat.db` schema, which Apple may change.
- It polls rather than getting push events, with a default latency of about 3 seconds.
- Text only, with no attachments. On newer macOS some messages keep their body only in `attributedBody`; those arrive with empty `text`.
- Only 1:1 iMessage chats are supported, not SMS or group chats.
- Delivery of sent messages isn't verified. AppleScript only confirms that Messages accepted the message.
- Calendar and Reminders automation can stall for a minute or more while iCloud syncs (timeouts are retried once). Recurring events are returned as Calendar.app exposes them.

## License

MIT, see [LICENSE](LICENSE).
