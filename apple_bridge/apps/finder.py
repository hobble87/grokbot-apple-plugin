"""Finder app: current selection and Spotlight search (via `mdfind`) are
read-only; revealing or opening a path are writes."""
from __future__ import annotations

import json

from .. import runner
from ..safety import ToolDef

MDFIND_BIN = "/usr/bin/mdfind"
OPEN_BIN = "/usr/bin/open"

_SELECTION_SCRIPT = r"""
function run(argv) {
    var Finder = Application("Finder");
    var selection = Finder.selection();
    var out = [];
    for (var i = 0; i < selection.length; i++) {
        out.push(decodeURI(selection[i].url()).replace(/^file:\/\//, ""));
    }
    return JSON.stringify(out);
}
"""

_REVEAL_SCRIPT = r"""
function run(argv) {
    var path = argv[0];
    var Finder = Application("Finder");
    Finder.reveal(Path(path));
    Finder.activate();
    return JSON.stringify({status: "revealed", path: path});
}
"""


def _text(args: dict, field: str, required: bool = False, max_len: int = 1000) -> str:
    value = args.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer")
    return value


def _limit(args: dict, default: int = 20, maximum: int = 100) -> int:
    limit = int(args.get("limit", default))
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def selection(_args: dict) -> str:
    output = runner.run_jxa(_SELECTION_SCRIPT)
    return output.strip() or "[]"


def spotlight_search(args: dict) -> str:
    query = _text(args, "query", required=True, max_len=500)
    limit = _limit(args)
    output = runner.run_cli([MDFIND_BIN, query])
    paths = [line for line in output.splitlines() if line.strip()][:limit]
    return json.dumps(paths)


def reveal(args: dict) -> str:
    path = _text(args, "path", required=True)
    return runner.run_jxa(_REVEAL_SCRIPT, path).strip()


def open_path(args: dict) -> str:
    path = _text(args, "path", required=True)
    runner.run_cli([OPEN_BIN, path])
    return json.dumps({"status": "opened", "path": path})


TOOLS = [
    ToolDef(
        name="finder.selection",
        description="List the paths currently selected in Finder.",
        schema={},
        handler=selection,
        kind="read",
    ),
    ToolDef(
        name="finder.spotlight_search",
        description="Search the filesystem with Spotlight (mdfind) and return matching paths.",
        schema={"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
        handler=spotlight_search,
        kind="read",
        required=["query"],
    ),
    ToolDef(
        name="finder.reveal",
        description="Reveal a path in a new Finder window.",
        schema={"path": {"type": "string"}},
        handler=reveal,
        kind="write",
        required=["path"],
    ),
    ToolDef(
        name="finder.open",
        description="Open a path with its default application.",
        schema={"path": {"type": "string"}},
        handler=open_path,
        kind="write",
        required=["path"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
