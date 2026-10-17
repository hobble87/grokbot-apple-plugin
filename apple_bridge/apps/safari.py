"""Safari app: listing open tabs (JXA) and parsing the Bookmarks.plist for
bookmarks/reading list are read-only; opening a URL is a write. Reading the
plist directly (no `runner` subprocess involved) needs Full Disk Access
since Safari's container is sandboxed."""
from __future__ import annotations

import json
import plistlib
from pathlib import Path
from urllib.parse import urlparse

from .. import config as config_module
from .. import runner
from ..safety import ToolDef

_LIST_TABS_SCRIPT = r"""
function run(argv) {
    var Safari = Application("Safari");
    var out = [];
    var windows = Safari.windows();
    for (var w = 0; w < windows.length; w++) {
        var tabs = windows[w].tabs();
        for (var t = 0; t < tabs.length; t++) {
            out.push({window: w + 1, index: t + 1, title: tabs[t].name(), url: tabs[t].url()});
        }
    }
    return JSON.stringify(out);
}
"""

_OPEN_URL_SCRIPT = r"""
function run(argv) {
    var url = argv[0];
    var Safari = Application("Safari");
    Safari.activate();
    var doc = Safari.Document({url: url});
    Safari.documents.push(doc);
    return JSON.stringify({status: "opened", url: url});
}
"""

_ALLOWED_URL_SCHEMES = {"http", "https"}


def _text(args: dict, field: str, required: bool = False, max_len: int = 2000) -> str:
    value = args.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer")
    return value


def _limit(args: dict, default: int = 20, maximum: int = 200) -> int:
    limit = int(args.get("limit", default))
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def _bookmarks_path(cfg: dict) -> Path:
    return Path(cfg.get("safari_bookmarks_plist") or config_module.DEFAULT_SAFARI_BOOKMARKS_PLIST).expanduser()


def _walk(node: dict, folder: str) -> list[dict]:
    items = []
    node_type = node.get("WebBookmarkType")
    if node_type == "WebBookmarkTypeLeaf":
        url = node.get("URLString", "")
        title = (node.get("URIDictionary") or {}).get("title", url)
        items.append({"title": title, "url": url, "folder": folder, "reading_list": "ReadingList" in node})
        return items
    title = node.get("Title", "")
    child_folder = f"{folder}/{title}" if folder and title else (title or folder)
    for child in node.get("Children") or []:
        items.extend(_walk(child, child_folder))
    return items


def _load_bookmarks(cfg: dict) -> list[dict]:
    path = _bookmarks_path(cfg)
    if not path.is_file():
        raise RuntimeError(
            f"Safari bookmarks plist not found at {path}. Grant this process Full Disk Access "
            "or set safari_bookmarks_plist in config.json."
        )
    try:
        with path.open("rb") as handle:
            data = plistlib.load(handle)
    except (plistlib.InvalidFileException, OSError) as error:
        raise RuntimeError(f"could not parse Safari bookmarks plist at {path}: {error}") from error
    return _walk(data, "")


def list_tabs(_args: dict) -> str:
    output = runner.run_jxa(_LIST_TABS_SCRIPT)
    return output.strip() or "[]"


def bookmarks(args: dict) -> str:
    cfg = config_module.load()
    limit = _limit(args)
    items = [item for item in _load_bookmarks(cfg) if not item["reading_list"]]
    return json.dumps(items[:limit])


def reading_list(args: dict) -> str:
    cfg = config_module.load()
    limit = _limit(args)
    items = [item for item in _load_bookmarks(cfg) if item["reading_list"]]
    return json.dumps(items[:limit])


def open_url(args: dict) -> str:
    url = _text(args, "url", required=True)
    scheme = urlparse(url).scheme.lower()
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise ValueError("url must start with http:// or https://")
    return runner.run_jxa(_OPEN_URL_SCRIPT, url).strip()


LIMIT_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 200, "default": 20}
TOOLS = [
    ToolDef(
        name="safari.list_tabs",
        description="List open tabs across all Safari windows.",
        schema={},
        handler=list_tabs,
        kind="read",
    ),
    ToolDef(
        name="safari.bookmarks",
        description="List bookmarks parsed read-only from Bookmarks.plist (needs Full Disk Access).",
        schema={"limit": LIMIT_SCHEMA},
        handler=bookmarks,
        kind="read",
    ),
    ToolDef(
        name="safari.reading_list",
        description="List Reading List entries parsed read-only from Bookmarks.plist (needs Full Disk Access).",
        schema={"limit": LIMIT_SCHEMA},
        handler=reading_list,
        kind="read",
    ),
    ToolDef(
        name="safari.open_url",
        description="Open an http(s) URL in a new Safari tab.",
        schema={"url": {"type": "string"}},
        handler=open_url,
        kind="write",
        required=["url"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
