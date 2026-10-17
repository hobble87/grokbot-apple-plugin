"""Calendar app tools: thin ToolDef wrappers around apple_bridge.calendar_mcp,
which already implements the Calendar AppleScript via apple_events.py."""
from __future__ import annotations

from .. import calendar_mcp
from ..safety import ToolDef

TOOLS = [
    ToolDef(
        name="calendar.setup_check",
        description="Check that the configured calendar and reminders list exist.",
        schema={},
        handler=calendar_mcp.check_setup,
        kind="read",
    ),
    ToolDef(
        name="calendar.list_events",
        description="List events in the configured calendar for a date window.",
        schema={"from": calendar_mcp.LOCAL, "days": {"type": "integer", "minimum": 1, "maximum": 92, "default": 7}},
        handler=calendar_mcp.list_events,
        kind="read",
    ),
    ToolDef(
        name="calendar.create_event",
        description="Create an event in the configured calendar. Times are local Mac time.",
        schema={"title": {"type": "string"}, "start": calendar_mcp.LOCAL, "end": calendar_mcp.LOCAL, "notes": {"type": "string"}},
        handler=calendar_mcp.create_event,
        kind="write",
        required=["title", "start", "end"],
    ),
    ToolDef(
        name="calendar.update_event",
        description="Update an event this assistant created. Deletes are not supported.",
        schema={"id": {"type": "string"}, "title": {"type": "string"}, "start": calendar_mcp.LOCAL, "end": calendar_mcp.LOCAL, "notes": {"type": "string"}},
        handler=calendar_mcp.update_event,
        kind="write",
        required=["id", "title", "start", "end"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
