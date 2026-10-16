"""Load settings from a JSON file plus environment-variable overrides.

Lookup order for the config file:
  1. $APPLE_BRIDGE_CONFIG
  2. ./config.json (next to the package's parent directory)
Environment variables always win over the file.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MESSAGES_DB = Path.home() / "Library" / "Messages" / "chat.db"


def _load_file() -> dict:
    path = Path(os.environ.get("APPLE_BRIDGE_CONFIG", ROOT / "config.json"))
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _list_env(name: str) -> list[str] | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def load() -> dict:
    data = _load_file()
    cfg: dict = {
        "messages_db": os.path.expanduser(os.environ.get("APPLE_BRIDGE_MESSAGES_DB", data.get("messages_db") or str(DEFAULT_MESSAGES_DB))),
        "state_dir": os.environ.get("APPLE_BRIDGE_STATE_DIR", data.get("state_dir") or str(ROOT / "work")),
        "poll_seconds": int(os.environ.get("APPLE_BRIDGE_POLL_SECONDS", data.get("poll_seconds", 3))),
        "calendar": os.environ.get("APPLE_BRIDGE_CALENDAR", data.get("calendar", "")),
        "reminders_list": os.environ.get("APPLE_BRIDGE_REMINDERS_LIST", data.get("reminders_list", "")),
        "webhook_url": os.environ.get("APPLE_BRIDGE_WEBHOOK_URL", data.get("webhook_url", "")),
        "webhook_headers": dict(data.get("webhook_headers", {})),
    }
    token = os.environ.get("APPLE_BRIDGE_WEBHOOK_TOKEN")
    if token:
        cfg["webhook_headers"]["Authorization"] = f"Bearer {token}"

    contacts = data.get("allowed_contacts", [])
    env_contacts = _list_env("APPLE_BRIDGE_ALLOWED_CONTACTS")
    if env_contacts is not None:
        contacts = [{"address": a, "name": a} for a in env_contacts]
    seen = set()
    cleaned = []
    for person in contacts:
        if isinstance(person, str):
            person = {"address": person, "name": person}
        address = str(person.get("address", "")).strip()
        if not address:
            raise ValueError("every allowed_contacts entry needs an address")
        if address.casefold() in seen:
            raise ValueError(f"duplicate contact {address}")
        seen.add(address.casefold())
        cleaned.append({"address": address, "name": str(person.get("name") or address).strip()})
    cfg["allowed_contacts"] = cleaned
    if not 1 <= cfg["poll_seconds"] <= 60:
        raise ValueError("poll_seconds must be between 1 and 60")
    return cfg
