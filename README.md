# apple-bridge — GrokBot Apple plugin

Give an AI assistant (GrokBot, Claude, or anything else that speaks MCP) a bridge to the Mac apps you use every day. **apple-bridge** runs on a Mac and exposes:

- **A unified MCP server** (`apple_bridge.server`) with tools for iMessage, Contacts, Notes, Calendar, Reminders, Clipboard, Shortcuts, Music, Finder, Notifications, Mail, Safari, Photos, and Find My.
- **An iMessage listener/webhook bridge** that polls the local Messages database (read-only) for new texts from contacts you allow, then POSTs each one to a webhook (your bot, an automation platform, or a local LLM server), and can reply over iMessage.
- A smaller, original **Calendar + Reminders only** MCP server (`apple_bridge.calendar_mcp`), kept for back-compat, scoped to one calendar and one reminders list.

It uses only the Python standard library, with no third-party dependencies. Everything is driven through AppleScript/JXA (`osascript`) or small Apple CLIs (`shortcuts`, `pbcopy`/`pbpaste`, `mdfind`, `open`); nothing talks to a private Apple server.

## Requirements

- macOS (tested on Apple silicon, macOS 14/15). Python 3.10+ (`/usr/bin/python3` or Homebrew).
- The apps you want to use signed in (iMessage, Mail account added, etc.).
- macOS permissions, under System Settings → Privacy & Security — see the [permissions table](#macos-permissions) below. macOS prompts the first time each app is automated; approve it for whichever process runs `python3` (Terminal, iTerm, or the exact binary launchd uses).
- The Mac must stay awake and logged in, since Messages/Calendar/Reminders/etc. only sync in a user session.

## Quick start

```bash
git clone https://github.com/<you>/apple-bridge.git
cd apple-bridge
cp config.example.json config.json   # edit it
cp .env.example .env                 # optional, for secrets; never commit
python3 -m apple_bridge.server       # unified MCP server, speaks stdio JSON-RPC
```

Add it to your MCP client config (Claude Desktop, GrokBot, Cursor, etc.):

```json
{
  "mcpServers": {
    "apple-bridge": {
      "command": "python3",
      "args": ["-m", "apple_bridge.server"],
      "cwd": "/PATH/TO/apple-bridge",
      "env": {
        "APPLE_BRIDGE_CALENDAR": "Assistant Shared",
        "APPLE_BRIDGE_REMINDERS_LIST": "Assistant Shared",
        "APPLE_BRIDGE_ALLOW_WRITE_TOOLS": "messages.send,calendar.*"
      }
    }
  }
}
```

The server lists its tools over `tools/list` and runs them over `tools/call`, same as any stdio MCP server — no extra client setup needed.

## Safety model

- **Every tool is classified `read` or `write`.** Reads (search, list, list_albums, now_playing, ...) are allowed by default. Writes (send, create, delete, run, display, open, set_volume, ...) are refused unless explicitly allow-listed.
- **`allow_write_tools`** (config key, or `APPLE_BRIDGE_ALLOW_WRITE_TOOLS` as a comma list) takes exact tool names (`"notes.create"`) or whole-app wildcards (`"notes.*"`). Nothing is write-enabled out of the box; `config.example.json` ships with an empty list.
- **`disabled_apps`** (config key, or `APPLE_BRIDGE_DISABLED_APPS`) removes an app's tools entirely, e.g. `["findmy", "mail"]`.
- `tools/list` descriptions are suffixed with `[WRITE – enabled]` or `[WRITE – requires allow-list]` so a client (or a human) can see at a glance what's live, and each tool carries an `annotations.readOnlyHint`.
- Calling a write tool that isn't allow-listed raises a clear `WriteNotAllowedError` telling you exactly which config key to set — it never silently no-ops or silently succeeds.
- All AppleScript/JXA invocations pass arguments via `osascript`'s `argv` (`on run argv` / `function run(argv)`), not string interpolation, so user-supplied text can't break out of the script.
- iMessage-specific controls (allow-list, read-only `chat.db`) are unchanged — see [Security notes](#security-notes).

## Per-app feature matrix

Tool names are shown as exposed over MCP (`app_tool`, which is what most clients require). Internally and in `allow_write_tools` you can use either `app.tool` / `app.*` or `app_tool` / `app_*`.

| App | Tool | Kind | What it does |
|---|---|---|---|
| Calendar | `calendar_setup_check` | read | Check the configured calendar/reminders list exist |
| Calendar | `calendar_list_events` | read | List events in a date window |
| Calendar | `calendar_create_event` | write | Create an event |
| Calendar | `calendar_update_event` | write | Update an event this assistant created (no deletes) |
| Reminders | `reminders_list` | read | List open reminders |
| Reminders | `reminders_create` | write | Create a reminder |
| Reminders | `reminders_update` | write | Update a reminder this assistant created |
| Messages | `messages_history` | read | Recent messages in a 1:1 iMessage chat |
| Messages | `messages_search` | read | Search message text across all chats |
| Messages | `messages_send` | write | Send an iMessage |
| Contacts | `contacts_search` | read | Search Contacts.app by name |
| Notes | `notes_list` | read | List recent notes |
| Notes | `notes_search` | read | Search note titles/bodies |
| Notes | `notes_create` | write | Create a note |
| Clipboard | `clipboard_get` | read | Read the clipboard |
| Clipboard | `clipboard_set` | write | Replace the clipboard |
| Shortcuts | `shortcuts_list` | read | List installed Shortcuts |
| Shortcuts | `shortcuts_run` | write | Run a shortcut, optionally with text input |
| Music | `music_now_playing` | read | Player state + current track |
| Music | `music_search` | read | Search the library |
| Music | `music_playlists` | read | List playlist names |
| Music | `music_play` / `music_pause` / `music_next` / `music_previous` | write | Transport controls |
| Music | `music_play_playlist` | write | Play a playlist by name |
| Music | `music_set_volume` | write | Set sound volume (0-100) |
| Finder | `finder_selection` | read | Paths currently selected in Finder |
| Finder | `finder_spotlight_search` | read | Spotlight (`mdfind`) search |
| Finder | `finder_reveal` | write | Reveal a path in a Finder window |
| Finder | `finder_open` | write | Open a path with its default app |
| Notifications | `notifications_display` | write | Display a notification banner |
| Mail | `mail_list_accounts` | read | List accounts + addresses |
| Mail | `mail_list_mailboxes` | read | List mailboxes |
| Mail | `mail_list_messages` | read | Recent messages in a mailbox |
| Mail | `mail_search` | read | Search by subject/sender |
| Mail | `mail_read_message` | read | Full content of one message |
| Mail | `mail_create_draft` | write | Create a draft (doesn't send) |
| Mail | `mail_send` | write | Compose and send mail |
| Safari | `safari_list_tabs` | read | List open tabs |
| Safari | `safari_bookmarks` | read | Bookmarks from `Bookmarks.plist` |
| Safari | `safari_reading_list` | read | Reading List from `Bookmarks.plist` |
| Safari | `safari_open_url` | write | Open an http(s) URL in a new tab |
| Photos | `photos_list_albums` | read | List album names/ids |
| Photos | `photos_search` | read | Search metadata by album/keyword/date (no image bytes) |
| Find My | `findmy_list_devices` | read | This Mac's devices, from cached JSON |
| Find My | `findmy_list_items` | read | Find My network items (e.g. AirTags), from cached JSON |

## macOS permissions

Grant these to whichever process runs `python3` (Terminal, iTerm, or the launchd-launched binary) under System Settings → Privacy & Security:

| Permission | Needed for |
|---|---|
| **Full Disk Access** | `messages.history`/`messages.search` (`chat.db`), `safari.bookmarks`/`safari.reading_list` (`Bookmarks.plist`), the iMessage listener |
| **Automation** (per target app) | Messages, Calendar, Reminders, Contacts, Notes, Music, Finder, Mail, Safari, Photos — macOS prompts per app the first time a tool touches it; approve each |
| **Contacts** | `contacts.search` |
| **Calendars** | `calendar.*` |
| **Reminders** | `reminders.*` |
| **Photos** | `photos.list_albums`, `photos.search` |
| **Notifications** | Not required — `display notification` doesn't need a grant, but Do Not Disturb/Focus can still suppress banners |

`shortcuts.*`, `clipboard.*`, `finder.spotlight_search`/`finder.open`, and `findmy.*` don't require Automation consent since they go through CLIs or plain file reads, not Apple events.

## Configuration

Settings come from `config.json` (see `config.example.json`), and environment variables override it.

| Key | Env var | Meaning |
|---|---|---|
| `allowed_contacts` | `APPLE_BRIDGE_ALLOWED_CONTACTS` (comma list) | Phone numbers or Apple IDs whose messages are forwarded by the listener. Everyone else is ignored. |
| `webhook_url` | `APPLE_BRIDGE_WEBHOOK_URL` | Where each incoming message is POSTed |
| `webhook_headers` | `APPLE_BRIDGE_WEBHOOK_TOKEN` → `Authorization: Bearer …` | Extra headers for auth |
| `messages_db` | `APPLE_BRIDGE_MESSAGES_DB` | Defaults to `~/Library/Messages/chat.db` |
| `safari_bookmarks_plist` | `APPLE_BRIDGE_SAFARI_BOOKMARKS_PLIST` | Defaults to `~/Library/Safari/Bookmarks.plist` |
| `findmy_cache_dir` | `APPLE_BRIDGE_FINDMY_CACHE_DIR` | Defaults to `~/Library/Caches/com.apple.findmy.fmipcore` |
| `state_dir` | `APPLE_BRIDGE_STATE_DIR` | Where the last-seen state and calendar/reminder ownership records live (default `./work`) |
| `poll_seconds` | `APPLE_BRIDGE_POLL_SECONDS` | Listener poll interval, 1–60 (default 3) |
| `calendar` | `APPLE_BRIDGE_CALENDAR` | The single calendar `calendar.*`/`apple_calendar_*` tools may use |
| `reminders_list` | `APPLE_BRIDGE_REMINDERS_LIST` | The single Reminders list `reminders.*`/`apple_reminder_*` tools may use |
| `allow_write_tools` | `APPLE_BRIDGE_ALLOW_WRITE_TOOLS` (comma list) | Write tools enabled: exact names (`"notes.create"`) or app wildcards (`"notes.*"`) |
| `disabled_apps` | `APPLE_BRIDGE_DISABLED_APPS` (comma list) | App names to hide from the tool list entirely |

`.env` isn't loaded automatically. Export it (`set -a; . ./.env; set +a`) or put the values in the launchd plist.

## Usage

**Unified MCP server:**

```bash
python3 -m apple_bridge.server
```

**Send an iMessage directly (CLI or Python), without the server:**

```bash
python3 -m apple_bridge.imessage_send +447700900000 --text "Hello from the bot"
echo "multi-line body" | python3 -m apple_bridge.imessage_send someone@example.com
```

```python
from apple_bridge.imessage_send import send_imessage
send_imessage("+447700900000", "Build finished ✅")
```

**Listen and forward iMessages to a webhook:**

```bash
python3 -m apple_bridge.listener init     # marks existing history as seen
python3 -m apple_bridge.listener once     # test once
python3 -m apple_bridge.listener watch    # run continuously
python3 -m apple_bridge.listener status
```

Before the first run, exchange one iMessage between the bot's Apple ID and each allowed contact, so the chat exists in `chat.db`.

**Run in the background with launchd:** edit the paths in `launchd/com.example.apple-bridge.plist` (point `ProgramArguments` at `apple_bridge.server` or `apple_bridge.listener watch`, whichever you're running as a daemon), then:

```bash
cp launchd/com.example.apple-bridge.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.apple-bridge.plist
```

Grant Full Disk Access to the exact `python3` path in the plist.

**Calendar and Reminders only MCP server (back-compat):** the original, smaller server still works if you don't want the rest of the apps exposed:

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

Its tools are `apple_setup_check`, `apple_calendar_list`, `apple_reminders_list`, `apple_calendar_create`, `apple_calendar_update`, `apple_reminder_create` and `apple_reminder_update`. Writes here are always on (there's no `allow_write_tools` gate in this server); it only lets the assistant update items it created itself, and it can't delete anything.

Tip: create a dedicated calendar (e.g. "Assistant Shared") and share it with your iCloud family. The assistant then only sees and edits that one calendar.

## Connecting an AI assistant (iMessage webhook)

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

`examples/webhook_receiver.py` is a 30-line echo server for local testing. Replace `answer()` with a call to your model (GrokBot, an OpenAI-compatible API, Ollama, etc.) or point `webhook_url` at your bot platform's inbound webhook.

## Security notes

- **Allow-list only, for both reads and writes.** Messages from anyone not in `allowed_contacts` are never read into the webhook payload or forwarded. Group chats are ignored by the listener.
- `chat.db` is opened **read-only** (`mode=ro`, `query_only`), and so is every other sqlite access in this project.
- Full Disk Access is powerful, so grant it only to the interpreter that runs this.
- Use HTTPS and a bearer token for the webhook. Keep tokens in `.env` or the plist, never in git (`.gitignore` already covers `.env`, `config.json`, `*.db` and `work/`).
- Message text is untrusted input. If your assistant can take actions, don't let message content alone authorise sends, payments or deletions.
- `allow_write_tools` is the main blast-radius control for the unified server: leave it empty for a read-only assistant, or allow-list narrowly (e.g. `messages.send` but not `mail.send`) rather than whole apps, if you're unsure.
- The calendar/reminders tools can only update items they created themselves, tracked in a local state file, and can't delete anything.

## Limitations

- macOS only; it relies on AppleScript/JXA and (for Messages/Safari) private file formats Apple may change.
- The iMessage listener polls rather than getting push events, with a default latency of about 3 seconds.
- iMessage is text only, with no attachments. On newer macOS some messages keep their body only in `attributedBody`; those arrive with empty `text`. Only 1:1 iMessage chats are supported, not SMS or group chats. Delivery of sent messages isn't verified — AppleScript only confirms Messages accepted the message.
- Calendar and Reminders automation can stall for a minute or more while iCloud syncs (timeouts are retried once). Recurring events are returned as Calendar.app exposes them.
- **Find My has no official API.** `findmy.*` reads the Find My daemon's cached `Items.data`/`Devices.data` JSON under `~/Library/Caches/com.apple.findmy.fmipcore`, which only exists if Find My has been opened at least once. Since macOS 14.4, Apple encrypts this cache, so on current systems these tools will likely fail with a clear error rather than return partial data. There's no tool to trigger device actions like "Play Sound" — that requires the Find My UI.
- **Photos never returns image bytes.** `photos.search`/`photos.list_albums` only expose filename, date, dimensions, album, and favorite status — by design, not as a current limitation.
- **Mail send is a real write.** `mail.send` composes and sends immediately with no draft review step; keep it out of `allow_write_tools` unless you trust the model and the inputs. `mail.create_draft` is the safer alternative when you want a human to hit Send.
- Safari's `Bookmarks.plist` and Messages' `chat.db` are undocumented Apple formats parsed as best-effort; a macOS update can change their layout.

## Troubleshooting: tools time out / run over SSH or launchd

If an app tool fails with `osascript timed out after 30s`, macOS is almost always sitting on an **Automation (TCC) consent dialog** on the Mac's screen, and `osascript` blocks silently until a human clicks it — there's no error until the timeout fires. This is most visible for apps you haven't approved yet (Contacts, Notes, Finder, Music, Mail, Safari, Photos); Calendar/Reminders often "just work" only because they were approved in an earlier session.

- Check **System Settings → Privacy & Security → Automation** for the process actually running `python3` and approve the target app listed there.
- When `python3` is launched over **SSH or by launchd**, macOS sometimes attributes the prompt to **`sshd`** or **`launchd`** instead of `python3` — if you don't see `python3` in the Automation list, look for those entries too, or run the command once from a local Terminal/iTerm session so the dialog appears under a process you can click.
- Since this fix, a timeout from `osascript` includes a hint naming the app it was targeting (when it could be determined from the script) plus this guidance, so you don't have to guess from the bare timeout message. A denied prompt surfaces immediately as `-1743` ("not authorized to send Apple events") with an explicit "Automation permission denied" message instead of waiting for the timeout.
- Each app's Automation grant is separate — approving one app doesn't approve the others.

**Find My (`findmy.*`) caches:** the underlying `Items.data`/`Devices.data` JSON files only exist if the Find My app has been opened at least once under the account running this tool; a fresh account with no cache will see a clear "not found" error rather than a timeout. On newer macOS these cache files are also encrypted, so even when present they may be unreadable.

## Running tests

The test suite mocks `runner.py`'s subprocess/sqlite calls and `calendar_mcp`'s Apple-events boundary, so it runs on Linux or any machine without macOS:

```bash
python3 -m pytest -q
```

## License

MIT, see [LICENSE](LICENSE).
