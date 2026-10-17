"""Reminders app tools: thin ToolDef wrappers around apple_bridge.calendar_mcp,
which already implements the Reminders AppleScript via apple_events.py."""
from __future__ import annotations

from .. import calendar_mcp
from ..safety import ToolDef

TOOLS = [
    ToolDef(
        name="reminders.list",
        description="List open reminders in the configured list.",
        schema={},
        handler=calendar_mcp.list_reminders,
        kind="read",
    ),
    ToolDef(
        name="reminders.create",
        description="Create a reminder in the configured list. Due time optional.",
        schema={"title": {"type": "string"}, "notes": {"type": "string"}, "due": {"type": ["string", "null"], "description": "Local time, or null"}},
        handler=calendar_mcp.create_reminder,
        kind="write",
        required=["title"],
    ),
    ToolDef(
        name="reminders.update",
        description="Update a reminder this assistant created. null due clears the date.",
        schema={"id": {"type": "string"}, "title": {"type": "string"}, "notes": {"type": "string"}, "due": {"type": ["string", "null"]}},
        handler=calendar_mcp.update_reminder,
        kind="write",
        required=["id", "title"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
