"""Shortcuts app: list installed shortcuts (read) and run one by name
(write), via the `shortcuts` CLI."""
from __future__ import annotations

import json

from .. import runner
from ..safety import ToolDef

SHORTCUTS_BIN = "/usr/bin/shortcuts"


def _text(args: dict, field: str, required: bool = False, max_len: int = 4000) -> str:
    value = args.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer")
    return value


def list_shortcuts(_args: dict) -> str:
    output = runner.run_cli([SHORTCUTS_BIN, "list"])
    names = [line.strip() for line in output.splitlines() if line.strip()]
    return json.dumps(names)


def run_shortcut(args: dict) -> str:
    name = _text(args, "name", required=True, max_len=200)
    input_text = args.get("input")
    if input_text is not None and not isinstance(input_text, str):
        raise ValueError("input must be a string")
    argv = [SHORTCUTS_BIN, "run", name]
    if input_text:
        argv += ["-i", "-"]
        output = runner.run_cli(argv, input_text=input_text)
    else:
        output = runner.run_cli(argv)
    return json.dumps({"name": name, "output": output.strip()})


TOOLS = [
    ToolDef(
        name="shortcuts.list",
        description="List the names of installed Shortcuts.",
        schema={},
        handler=list_shortcuts,
        kind="read",
    ),
    ToolDef(
        name="shortcuts.run",
        description="Run a shortcut by name, optionally piping it text input.",
        schema={"name": {"type": "string"}, "input": {"type": "string"}},
        handler=run_shortcut,
        kind="write",
        required=["name"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
