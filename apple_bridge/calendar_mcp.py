"""Minimal stdio MCP server exposing one Apple Calendar and one Reminders list.

Point any MCP-capable assistant (Claude Desktop, Cursor, etc.) at:
  python3 -m apple_bridge.calendar_mcp

Safety model: the assistant can read the configured collections, create items
in them, and update only items it created itself (tracked in a state file).
Deletes are not supported.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from . import config as config_module
from .apple_events import call_apple_events

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def settings() -> dict:
    cfg = config_module.load()
    for key in ("calendar", "reminders_list"):
        if not cfg.get(key, "").strip():
            raise ValueError(f"Set {key} in config.json (or APPLE_BRIDGE_{key.upper()})")
    return cfg


def _state_path() -> Path:
    return Path(config_module.load()["state_dir"]) / "calendar_items.json"


def local_datetime(value, field: str) -> str:
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be local time in YYYY-MM-DDTHH:MM:SS format")
    datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    return value


def _due_text(args: dict) -> str:
    """Models often send "None"/"null" for no due date; treat those as undated."""
    due = args.get("due")
    if due is None or (isinstance(due, str) and due.strip().casefold() in {"", "-", "none", "null", "nil", "undated", "no due date"}):
        return "-"
    return local_datetime(due, "due")


def _text(args: dict, field: str, required: bool = False) -> str:
    value = args.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > 4000:
        raise ValueError(f"{field} must be 4000 characters or fewer")
    return value


def _state() -> dict:
    path = _state_path()
    if not path.exists():
        return {"events": [], "reminders": []}
    state = json.loads(path.read_text())
    if not isinstance(state.get("events"), list) or not isinstance(state.get("reminders"), list):
        raise ValueError("ownership state is invalid; refusing to modify items")
    return state


def _write_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.replace(path)


def _remember(category: str, item_id: str, collection: str) -> None:
    if not item_id:
        raise RuntimeError("Calendar/Reminders created an item without returning its ID")
    state = _state()
    if item_id not in state[category]:
        state[category].append(item_id)
    state.setdefault("collections", {})[category] = collection
    _write_state(state)


def _owned(category: str, item_id: str, collection: str) -> None:
    state = _state()
    if item_id not in state[category] or state.get("collections", {}).get(category) != collection:
        raise PermissionError("only items created by this assistant in the configured collection can be updated")


def check_setup(_args: dict) -> str:
    cfg = settings()
    return json.dumps(call_apple_events("check", cfg["calendar"], cfg["reminders_list"]))


def list_events(args: dict) -> str:
    cfg = settings()
    days = int(args.get("days", 7))
    start = args.get("from") or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
    start = local_datetime(start, "from")
    end = (datetime.fromisoformat(start) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    return json.dumps(call_apple_events("list_events", cfg["calendar"], start, end), ensure_ascii=False, indent=2)


def list_reminders(_args: dict) -> str:
    cfg = settings()
    return json.dumps(call_apple_events("list_reminders", cfg["reminders_list"]), ensure_ascii=False, indent=2)


def create_event(args: dict) -> str:
    cfg = settings()
    title = _text(args, "title", required=True)
    start = local_datetime(args.get("start"), "start")
    end = local_datetime(args.get("end"), "end")
    if end <= start:
        raise ValueError("end must be later than start")
    created = call_apple_events("create_event", cfg["calendar"], title, start, end, _text(args, "notes"))
    _remember("events", created["id"], cfg["calendar"])
    return json.dumps({"status": "created", **created})


def update_event(args: dict) -> str:
    cfg = settings()
    item_id = _text(args, "id", required=True)
    _owned("events", item_id, cfg["calendar"])
    title = _text(args, "title", required=True)
    start = local_datetime(args.get("start"), "start")
    end = local_datetime(args.get("end"), "end")
    if end <= start:
        raise ValueError("end must be later than start")
    updated = call_apple_events("update_event", cfg["calendar"], item_id, title, start, end, _text(args, "notes"))
    return json.dumps({"status": "updated", **updated})


def create_reminder(args: dict) -> str:
    cfg = settings()
    created = call_apple_events("create_reminder", cfg["reminders_list"], _text(args, "title", required=True), _text(args, "notes"), _due_text(args))
    _remember("reminders", created["id"], cfg["reminders_list"])
    return json.dumps({"status": "created", **created})


def update_reminder(args: dict) -> str:
    cfg = settings()
    item_id = _text(args, "id", required=True)
    _owned("reminders", item_id, cfg["reminders_list"])
    updated = call_apple_events("update_reminder", cfg["reminders_list"], item_id, _text(args, "title", required=True), _text(args, "notes"), _due_text(args))
    return json.dumps({"status": "updated", **updated})


LOCAL = {"type": "string", "description": "Local time YYYY-MM-DDTHH:MM:SS"}
TOOLS: dict[str, tuple[str, dict, Callable[[dict], str], bool]] = {
    "apple_setup_check": ("Check the configured calendar and reminders list exist.", {}, check_setup, True),
    "apple_calendar_list": ("List events in the configured calendar for a date window.",
        {"from": LOCAL, "days": {"type": "integer", "minimum": 1, "maximum": 92, "default": 7}}, list_events, True),
    "apple_reminders_list": ("List open reminders in the configured list.", {}, list_reminders, True),
    "apple_calendar_create": ("Create an event in the configured calendar. Times are local Mac time.",
        {"title": {"type": "string"}, "start": LOCAL, "end": LOCAL, "notes": {"type": "string"}}, create_event, False),
    "apple_calendar_update": ("Update an event this assistant created. Deletes are not supported.",
        {"id": {"type": "string"}, "title": {"type": "string"}, "start": LOCAL, "end": LOCAL, "notes": {"type": "string"}}, update_event, False),
    "apple_reminder_create": ("Create a reminder in the configured list. Due time optional.",
        {"title": {"type": "string"}, "notes": {"type": "string"}, "due": {"type": ["string", "null"], "description": "Local time, or null"}}, create_reminder, False),
    "apple_reminder_update": ("Update a reminder this assistant created. null due clears the date.",
        {"id": {"type": "string"}, "title": {"type": "string"}, "notes": {"type": "string"}, "due": {"type": ["string", "null"]}}, update_reminder, False),
}
REQUIRED = {
    "apple_calendar_create": ["title", "start", "end"],
    "apple_calendar_update": ["id", "title", "start", "end"],
    "apple_reminder_create": ["title"],
    "apple_reminder_update": ["id", "title"],
}


def tool_list() -> list[dict]:
    return [{
        "name": name, "description": desc,
        "inputSchema": {"type": "object", "properties": props, "required": REQUIRED.get(name, []), "additionalProperties": False},
        "annotations": {"readOnlyHint": ro},
    } for name, (desc, props, _h, ro) in TOOLS.items()]


def handle(message: dict) -> dict | None:
    method = message.get("method")
    if method == "initialize":
        return {
            "protocolVersion": message.get("params", {}).get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "apple-bridge-calendar", "version": "0.1.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": tool_list()}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        if name not in TOOLS:
            raise LookupError(f"unknown tool {name}")
        return {"content": [{"type": "text", "text": TOOLS[name][2](params.get("arguments") or {})}], "isError": False}
    if message.get("id") is None:
        return None
    raise NotImplementedError(method)


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        request_id = message.get("id")
        try:
            result = handle(message)
            if request_id is None:
                continue
            reply = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except NotImplementedError as error:
            reply = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"method not found: {error}"}}
        except Exception as error:
            reply = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(error)}}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
