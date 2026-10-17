"""Notifications app: display a macOS notification banner (write only)."""
from __future__ import annotations

import json

from .. import runner
from ..safety import ToolDef

_DISPLAY_SCRIPT = r"""
on run argv
    set theText to item 1 of argv
    set theTitle to item 2 of argv
    set theSubtitle to item 3 of argv
    if theSubtitle is "" then
        display notification theText with title theTitle
    else
        display notification theText with title theTitle subtitle theSubtitle
    end if
end run
"""


def _text(args: dict, field: str, required: bool = False, max_len: int = 500) -> str:
    value = args.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer")
    return value


def display(args: dict) -> str:
    text = _text(args, "text", required=True)
    title = _text(args, "title", max_len=200) or "Apple Bridge"
    subtitle = _text(args, "subtitle", max_len=200)
    runner.run_applescript(_DISPLAY_SCRIPT, text, title, subtitle)
    return json.dumps({"status": "sent"})


TOOLS = [
    ToolDef(
        name="notifications.display",
        description="Display a macOS notification banner.",
        schema={"text": {"type": "string"}, "title": {"type": "string"}, "subtitle": {"type": "string"}},
        handler=display,
        kind="write",
        required=["text"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
