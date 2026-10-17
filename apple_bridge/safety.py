"""Gating for write tools.

Every tool is classified `read` or `write`. Write tools (send/delete/modify/
run) are refused unless allow-listed in config under `allow_write_tools`,
which accepts exact tool names ("notes.create") or app wildcards
("notes.*"). Reads are allowed by default; whole apps can be switched off
via `disabled_apps`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

KINDS = ("read", "write")


@dataclass(frozen=True)
class ToolDef:
    name: str  # "<app>.<action>", e.g. "notes.create"
    description: str
    schema: dict
    handler: Callable[[dict], str]
    kind: str
    required: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if "." not in self.name:
            raise ValueError(f"tool name {self.name!r} must be '<app>.<action>'")
        if self.kind not in KINDS:
            raise ValueError(f"{self.name}: kind must be one of {KINDS}")


class WriteNotAllowedError(PermissionError):
    pass


def app_name(tool_name: str) -> str:
    return tool_name.split(".", 1)[0]


def is_write_allowed(tool_name: str, allow_write_tools: list[str]) -> bool:
    return tool_name in allow_write_tools or f"{app_name(tool_name)}.*" in allow_write_tools


def check_write_allowed(tool: ToolDef, cfg: dict) -> None:
    if tool.kind == "write" and not is_write_allowed(tool.name, cfg.get("allow_write_tools", [])):
        raise WriteNotAllowedError(
            f'{tool.name} is a write tool; add "{tool.name}" or "{app_name(tool.name)}.*" '
            f"to allow_write_tools in config.json to enable it"
        )


def visible_tools(tools: list[ToolDef], cfg: dict) -> list[ToolDef]:
    disabled = set(cfg.get("disabled_apps", []))
    return [t for t in tools if app_name(t.name) not in disabled]
