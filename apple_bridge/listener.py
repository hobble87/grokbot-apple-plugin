"""Watch Messages for new iMessages from allowed contacts and forward them to a webhook.

Your assistant receives a JSON POST per message and replies by calling
`python3 -m apple_bridge.imessage_send` (or the optional reply field below).

Usage:
  python3 -m apple_bridge.listener init     # mark existing messages as already seen
  python3 -m apple_bridge.listener once     # process new messages once
  python3 -m apple_bridge.listener watch    # poll forever (used by launchd)
  python3 -m apple_bridge.listener status
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import config as config_module
from .imessage_send import send_imessage
from .messages_db import (
    conversation_history,
    incoming_messages,
    latest_rowid,
    open_messages,
    private_chat_id,
)

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def _apple_time(value) -> str | None:
    if not value:
        return None
    seconds = value / 1e9 if value > 1e12 else value  # nanoseconds on modern macOS
    return (APPLE_EPOCH + timedelta(seconds=seconds)).isoformat()


def _state_path(cfg: dict) -> Path:
    return Path(cfg["state_dir"]) / "listener-state.json"


def read_state(path: Path) -> dict:
    if not path.exists():
        return {"chats": {}}
    state = json.loads(path.read_text())
    if not isinstance(state.get("chats"), dict):
        raise ValueError(f"Invalid state file: {path}")
    return state


def write_state(state: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.replace(path)


def forward(cfg: dict, payload: dict) -> dict | None:
    """POST payload to the webhook. Returns the parsed JSON response ({} if empty),
    or None if delivery failed (the message will be retried next poll)."""
    if not cfg["webhook_url"]:
        raise ValueError("Set webhook_url / APPLE_BRIDGE_WEBHOOK_URL")
    headers = {"Content-Type": "application/json", **cfg["webhook_headers"]}
    request = urllib.request.Request(
        cfg["webhook_url"], data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if not 200 <= response.status < 300:
                return None
            body = response.read()
    except urllib.error.URLError as error:
        print(f"webhook delivery failed: {error}", file=sys.stderr, flush=True)
        return None
    try:
        return json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        return {}


def process_once(cfg: dict, send: Callable[[str, str], None] = send_imessage) -> int:
    state_path = _state_path(cfg)
    handled = 0
    with closing(open_messages(cfg["messages_db"])) as connection:
        state = read_state(state_path)
        for person in cfg["allowed_contacts"]:
            try:
                chat_id = private_chat_id(connection, person["address"])
            except LookupError as error:
                print(error, file=sys.stderr, flush=True)
                continue
            key = str(chat_id)
            if key not in state["chats"]:
                # First sighting: start from now, don't replay old history.
                state["chats"][key] = {"address": person["address"], "last_rowid": latest_rowid(connection, chat_id)}
                write_state(state, state_path)
                continue
            entry = state["chats"][key]
            for message in incoming_messages(connection, chat_id, entry["last_rowid"]):
                payload = {
                    "from": person["address"],
                    "name": person["name"],
                    "text": message["text"],
                    "guid": message["guid"],
                    "sent_at": _apple_time(message["apple_date"]),
                    "history": conversation_history(connection, chat_id, message["rowid"]),
                }
                result = forward(cfg, payload)
                if result is None:
                    break  # retry from this message next time
                reply = result.get("reply") if isinstance(result, dict) else None
                if isinstance(reply, str) and reply.strip():
                    send(person["address"], reply)
                entry["last_rowid"] = message["rowid"]
                write_state(state, state_path)
                handled += 1
    return handled


def initialize(cfg: dict) -> dict:
    state_path = _state_path(cfg)
    state = {"chats": {}}
    with closing(open_messages(cfg["messages_db"])) as connection:
        for person in cfg["allowed_contacts"]:
            chat_id = private_chat_id(connection, person["address"])
            state["chats"][str(chat_id)] = {"address": person["address"], "last_rowid": latest_rowid(connection, chat_id)}
    write_state(state, state_path)
    return state


def watch(cfg: dict) -> None:
    print("apple-bridge listener started", flush=True)
    while True:
        try:
            handled = process_once(cfg)
            if handled:
                print(f"forwarded {handled} message(s)", flush=True)
            time.sleep(cfg["poll_seconds"])
        except KeyboardInterrupt:
            return
        except Exception as error:  # keep the daemon alive
            print(f"listener error: {error}", file=sys.stderr, flush=True)
            time.sleep(max(10, cfg["poll_seconds"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Forward incoming iMessages to a webhook")
    parser.add_argument("command", choices=("init", "once", "status", "watch"))
    args = parser.parse_args()
    cfg = config_module.load()
    if not cfg["allowed_contacts"]:
        raise SystemExit("No allowed_contacts configured; refusing to forward anything.")
    if args.command == "init":
        print(json.dumps(initialize(cfg), indent=2))
    elif args.command == "once":
        print(json.dumps({"handled": process_once(cfg)}))
    elif args.command == "status":
        print(json.dumps({
            "contacts": [p["address"] for p in cfg["allowed_contacts"]],
            "webhook_configured": bool(cfg["webhook_url"]),
            "state": read_state(_state_path(cfg)),
        }, indent=2))
    else:
        watch(cfg)


if __name__ == "__main__":
    main()
