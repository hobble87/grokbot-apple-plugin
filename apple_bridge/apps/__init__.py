"""Registry of app modules. Each module exports tools() -> list[ToolDef]."""
from __future__ import annotations

from .. import safety
from . import (
    calendar, clipboard, contacts, findmy, finder, mail, messages, music,
    notes, notifications, photos, reminders, safari, shortcuts,
)

MODULES = (
    calendar, reminders, messages, contacts, notes, clipboard,
    shortcuts, music, finder, notifications, mail, safari, photos, findmy,
)


def collect_tools() -> list[safety.ToolDef]:
    tools: list[safety.ToolDef] = []
    seen: set[str] = set()
    for module in MODULES:
        for tool in module.tools():
            if tool.name in seen:
                raise ValueError(f"duplicate tool name: {tool.name}")
            seen.add(tool.name)
            tools.append(tool)
    return tools
