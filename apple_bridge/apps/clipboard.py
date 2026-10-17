"""Clipboard access via pbcopy/pbpaste."""
from __future__ import annotations

import json

from .. import runner
from ..safety import ToolDef

MAX_LEN = 100_000


def get(_args: dict) -> str:
    text = runner.run_cli(["/usr/bin/pbpaste"])
    return json.dumps({"text": text})


def set_clipboard(args: dict) -> str:
    text = args.get("text", "")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if len(text) > MAX_LEN:
        raise ValueError(f"text must be {MAX_LEN} characters or fewer")
    runner.run_cli(["/usr/bin/pbcopy"], input_text=text)
    return json.dumps({"status": "copied"})


TOOLS = [
    ToolDef(
        name="clipboard.get",
        description="Read the current macOS clipboard text.",
        schema={},
        handler=get,
        kind="read",
    ),
    ToolDef(
        name="clipboard.set",
        description="Replace the macOS clipboard with the given text.",
        schema={"text": {"type": "string"}},
        handler=set_clipboard,
        kind="write",
        required=["text"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
