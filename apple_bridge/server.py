"""Unified stdio MCP server exposing every apple_bridge app as tools.

Run with: python3 -m apple_bridge.server

Write tools (send/delete/modify/run) are refused unless allow-listed via
`allow_write_tools` in config.json; see safety.py. Whole apps can be turned
off with `disabled_apps`. For back-compat, the original Calendar/Reminders-only
server still works: python3 -m apple_bridge.calendar_mcp
"""
from __future__ import annotations

import json
import sys

from . import config as config_module
from .apps import collect_tools
from .safety import check_write_allowed, is_write_allowed, visible_tools

WRITE_BLOCKED_SUFFIX = " [WRITE – requires allow-list]"
WRITE_ENABLED_SUFFIX = " [WRITE – enabled]"


def tool_list(cfg: dict) -> list[dict]:
    allow = cfg.get("allow_write_tools", [])
    out = []
    for tool in visible_tools(collect_tools(), cfg):
        description = tool.description
        if tool.kind == "write":
            description += WRITE_ENABLED_SUFFIX if is_write_allowed(tool.name, allow) else WRITE_BLOCKED_SUFFIX
        out.append({
            "name": tool.name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": tool.schema,
                "required": tool.required,
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": tool.kind == "read"},
        })
    return out


def call_tool(name: str, arguments: dict, cfg: dict) -> str:
    tools_by_name = {t.name: t for t in visible_tools(collect_tools(), cfg)}
    tool = tools_by_name.get(name)
    if tool is None:
        raise LookupError(f"unknown tool {name}")
    check_write_allowed(tool, cfg)
    return tool.handler(arguments)


def handle(message: dict) -> dict | None:
    method = message.get("method")
    if method == "initialize":
        return {
            "protocolVersion": message.get("params", {}).get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "apple-bridge", "version": "0.2.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": tool_list(config_module.load())}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        text = call_tool(name, params.get("arguments") or {}, config_module.load())
        return {"content": [{"type": "text", "text": text}], "isError": False}
    if message.get("id") is None:
        return None
    raise NotImplementedError(method)


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        request_id = message.get("id")
        try:
            result = handle(message)
            if request_id is None:
                continue
            reply = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except NotImplementedError as error:
            reply = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"method not found: {error}"}}
        except Exception as error:
            reply = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(error)}}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
