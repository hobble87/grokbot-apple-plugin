"""Contacts app: read-only search via Contacts.app, driven by JXA so results
come back as plain JSON. Requires the Contacts Automation permission."""
from __future__ import annotations

from .. import runner
from ..safety import ToolDef

_SEARCH_SCRIPT = r"""
function run(argv) {
    var query = argv[0];
    var limit = parseInt(argv[1], 10) || 20;
    var Contacts = Application("Contacts");
    var people = Contacts.people.whose({name: {_contains: query}})();
    var out = [];
    for (var i = 0; i < people.length && out.length < limit; i++) {
        var p = people[i];
        out.push({
            id: p.id(),
            name: p.name(),
            emails: p.emails().map(function (e) { return e.value(); }),
            phones: p.phones().map(function (ph) { return ph.value(); }),
        });
    }
    return JSON.stringify(out);
}
"""


def _query(args: dict, max_len: int = 200) -> str:
    value = args.get("query", "")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("query is required")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError(f"query must be {max_len} characters or fewer")
    return value


def _limit(args: dict, default: int = 20, maximum: int = 100) -> int:
    limit = int(args.get("limit", default))
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def search(args: dict) -> str:
    query = _query(args)
    limit = _limit(args)
    output = runner.run_jxa(_SEARCH_SCRIPT, query, str(limit))
    return output.strip() or "[]"


TOOLS = [
    ToolDef(
        name="contacts.search",
        description="Search Contacts.app by name; returns emails and phone numbers.",
        schema={"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
        handler=search,
        kind="read",
        required=["query"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
