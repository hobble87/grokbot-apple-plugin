"""Notes app: list/search are read-only; create adds a new note (write).
Driven by JXA so results come back as plain JSON. Requires the Notes
Automation permission."""
from __future__ import annotations

from .. import runner
from ..safety import ToolDef

_LIST_SCRIPT = r"""
function run(argv) {
    var limit = parseInt(argv[0], 10) || 20;
    var Notes = Application("Notes");
    var all = Notes.notes();
    var out = [];
    for (var i = 0; i < all.length && out.length < limit; i++) {
        var n = all[i];
        out.push({id: n.id(), name: n.name(), modified: n.modificationDate().toISOString()});
    }
    return JSON.stringify(out);
}
"""

_SEARCH_SCRIPT = r"""
function run(argv) {
    var query = argv[0].toLowerCase();
    var limit = parseInt(argv[1], 10) || 20;
    var Notes = Application("Notes");
    var all = Notes.notes();
    var out = [];
    for (var i = 0; i < all.length && out.length < limit; i++) {
        var n = all[i];
        var name = n.name();
        var body = n.plaintext();
        if (name.toLowerCase().indexOf(query) !== -1 || body.toLowerCase().indexOf(query) !== -1) {
            out.push({id: n.id(), name: name, modified: n.modificationDate().toISOString(), preview: body.slice(0, 200)});
        }
    }
    return JSON.stringify(out);
}
"""

_CREATE_SCRIPT = r"""
function run(argv) {
    var title = argv[0];
    var body = argv[1];
    var folderName = argv[2];
    var Notes = Application("Notes");
    Notes.includeStandardAdditions = true;
    var folder = folderName ? Notes.folders.whose({name: folderName})[0] : Notes.defaultAccount.folders[0];
    var newNote = Notes.Note({name: title, body: body});
    folder.notes.push(newNote);
    return JSON.stringify({id: newNote.id()});
}
"""


def _text(args: dict, field: str, required: bool = False, max_len: int = 20000) -> str:
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


def list_notes(args: dict) -> str:
    output = runner.run_jxa(_LIST_SCRIPT, str(_limit(args)))
    return output.strip() or "[]"


def search(args: dict) -> str:
    query = _text(args, "query", required=True, max_len=200)
    output = runner.run_jxa(_SEARCH_SCRIPT, query, str(_limit(args)))
    return output.strip() or "[]"


def create(args: dict) -> str:
    title = _text(args, "title", required=True, max_len=500)
    body = _text(args, "body")
    folder = _text(args, "folder", max_len=200)
    return runner.run_jxa(_CREATE_SCRIPT, title, body, folder).strip()


LIMIT_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
TOOLS = [
    ToolDef(
        name="notes.list",
        description="List recent notes (id, name, last modified).",
        schema={"limit": LIMIT_SCHEMA},
        handler=list_notes,
        kind="read",
    ),
    ToolDef(
        name="notes.search",
        description="Search note titles and bodies for a substring.",
        schema={"query": {"type": "string"}, "limit": LIMIT_SCHEMA},
        handler=search,
        kind="read",
        required=["query"],
    ),
    ToolDef(
        name="notes.create",
        description="Create a new note, optionally in a named folder (defaults to the account's default folder).",
        schema={"title": {"type": "string"}, "body": {"type": "string"}, "folder": {"type": "string"}},
        handler=create,
        kind="write",
        required=["title"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
