"""Photos app: read-only metadata access (albums, media search). Never
returns image bytes, only filename/date/dimensions/favorite. Driven by JXA
against Photos.app. Requires the Photos Automation permission."""
from __future__ import annotations

from .. import runner
from ..safety import ToolDef

_LIST_ALBUMS_SCRIPT = r"""
function run(argv) {
    var Photos = Application("Photos");
    var albums = Photos.albums();
    var out = [];
    for (var i = 0; i < albums.length; i++) {
        out.push({name: albums[i].name(), id: albums[i].id()});
    }
    return JSON.stringify(out);
}
"""

_SEARCH_SCRIPT = r"""
function run(argv) {
    var albumName = argv[0];
    var keyword = argv[1] ? argv[1].toLowerCase() : "";
    var startDate = argv[2] ? new Date(argv[2]) : null;
    var endDate = argv[3] ? new Date(argv[3]) : null;
    var limit = parseInt(argv[4], 10) || 20;
    var Photos = Application("Photos");
    var items;
    if (albumName) {
        var albums = Photos.albums.whose({name: albumName})();
        if (albums.length === 0) throw new Error("album not found: " + albumName);
        items = albums[0].mediaItems();
    } else {
        items = Photos.mediaItems();
    }
    var out = [];
    for (var i = 0; i < items.length && out.length < limit; i++) {
        var m = items[i];
        var date = m.date();
        if (startDate && date < startDate) continue;
        if (endDate && date > endDate) continue;
        var filename = m.filename();
        if (keyword && filename.toLowerCase().indexOf(keyword) === -1) continue;
        out.push({filename: filename, date: date.toISOString(), width: m.width(), height: m.height(), favorite: m.favorite()});
    }
    return JSON.stringify(out);
}
"""


def _text(args: dict, field: str, required: bool = False, max_len: int = 200) -> str:
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


def list_albums(_args: dict) -> str:
    output = runner.run_jxa(_LIST_ALBUMS_SCRIPT)
    return output.strip() or "[]"


def search(args: dict) -> str:
    album = _text(args, "album")
    keyword = _text(args, "keyword")
    start_date = _text(args, "start_date", max_len=40)
    end_date = _text(args, "end_date", max_len=40)
    output = runner.run_jxa(_SEARCH_SCRIPT, album, keyword, start_date, end_date, str(_limit(args)))
    return output.strip() or "[]"


LIMIT_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 200, "default": 20}
TOOLS = [
    ToolDef(
        name="photos.list_albums",
        description="List Photos.app album names and ids.",
        schema={},
        handler=list_albums,
        kind="read",
    ),
    ToolDef(
        name="photos.search",
        description=(
            "Search media metadata by album, filename keyword, and/or date range. "
            "Returns filename/date/dimensions/favorite only, never image bytes."
        ),
        schema={
            "album": {"type": "string"},
            "keyword": {"type": "string"},
            "start_date": {"type": "string", "description": "ISO 8601 date, e.g. 2026-01-01"},
            "end_date": {"type": "string", "description": "ISO 8601 date, e.g. 2026-01-31"},
            "limit": LIMIT_SCHEMA,
        },
        handler=search,
        kind="read",
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
