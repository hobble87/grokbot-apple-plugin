"""Find My app: read-only access to the cached Items.data/Devices.data JSON
under ~/Library/Caches/com.apple.findmy.fmipcore, written by the Find My
daemon. There is no official API. Apple encrypts this cache on macOS 14.4+,
so these tools raise a clear error rather than returning partial/garbage
data when the files are missing or unreadable. No write tools: nothing here
can be safely automated (device actions like "Play Sound" require the Find
My UI)."""
from __future__ import annotations

import json
from pathlib import Path

from .. import config as config_module
from ..safety import ToolDef

_NOT_FOUND_HINT = (
    "{filename} not found at {path}. Find My must have been opened at least once on this Mac, "
    "or set findmy_cache_dir in config.json to point at the right fmipcore cache directory."
)
_UNREADABLE_HINT = (
    "{filename} at {path} could not be parsed as JSON. Since macOS 14.4, Apple encrypts this "
    "cache, so it may be unreadable even though it exists; this file may also be present but "
    "empty or corrupted. Error: {error}"
)


def _cache_dir(cfg: dict) -> Path:
    return Path(cfg.get("findmy_cache_dir") or config_module.DEFAULT_FINDMY_CACHE_DIR).expanduser()


def _load_cache_file(cfg: dict, filename: str) -> list[dict]:
    path = _cache_dir(cfg) / filename
    if not path.is_file():
        raise RuntimeError(_NOT_FOUND_HINT.format(filename=filename, path=path))
    try:
        data = json.loads(path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(_UNREADABLE_HINT.format(filename=filename, path=path, error=error)) from error
    if not isinstance(data, list):
        raise RuntimeError(f"{filename} at {path} has an unexpected format (expected a JSON array)")
    return data


def list_devices(_args: dict) -> str:
    cfg = config_module.load()
    devices = _load_cache_file(cfg, "Devices.data")
    out = [
        {
            "name": device.get("name"),
            "deviceModel": device.get("deviceModel"),
            "batteryLevel": device.get("batteryLevel"),
            "location": device.get("location"),
        }
        for device in devices
    ]
    return json.dumps(out)


def list_items(_args: dict) -> str:
    cfg = config_module.load()
    items = _load_cache_file(cfg, "Items.data")
    out = [
        {
            "name": item.get("name"),
            "productType": (item.get("productType") or {}).get("name"),
            "batteryStatus": item.get("batteryStatus"),
            "location": item.get("location"),
        }
        for item in items
    ]
    return json.dumps(out)


TOOLS = [
    ToolDef(
        name="findmy.list_devices",
        description=(
            "List this Mac's Find My devices from the cached Devices.data JSON. "
            "Fails with a clear error if the cache is missing or encrypted (macOS 14.4+)."
        ),
        schema={},
        handler=list_devices,
        kind="read",
    ),
    ToolDef(
        name="findmy.list_items",
        description=(
            "List Find My network items (e.g. AirTags) from the cached Items.data JSON. "
            "Fails with a clear error if the cache is missing or encrypted (macOS 14.4+)."
        ),
        schema={},
        handler=list_items,
        kind="read",
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
