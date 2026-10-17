import json

import pytest

from apple_bridge import runner, server
from apple_bridge.safety import WriteNotAllowedError


def test_initialize():
    result = server.handle({"method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert result["serverInfo"]["name"] == "apple-bridge"
    assert result["capabilities"]["tools"]["listChanged"] is False


def test_ping_returns_empty_dict():
    assert server.handle({"method": "ping"}) == {}


def test_tools_list_marks_blocked_write_tools():
    result = server.handle({"method": "tools/list"})
    by_name = {t["name"]: t for t in result["tools"]}
    assert "[WRITE" in by_name["clipboard_set"]["description"]
    assert by_name["clipboard_set"]["annotations"]["readOnlyHint"] is False
    assert by_name["clipboard_get"]["annotations"]["readOnlyHint"] is True
    assert "requires allow-list" in by_name["clipboard_set"]["description"]


def test_tools_list_hides_disabled_apps(isolated_config):
    (isolated_config / "config.json").write_text(json.dumps({"disabled_apps": ["clipboard"]}))
    result = server.handle({"method": "tools/list"})
    names = {t["name"] for t in result["tools"]}
    assert not any(name.startswith("clipboard_") for name in names)


def test_call_tool_blocks_write_without_allow_list(monkeypatch):
    monkeypatch.setattr(runner, "run_cli", lambda *a, **k: "")
    with pytest.raises(WriteNotAllowedError):
        server.call_tool("clipboard.set", {"text": "hi"}, {})


def test_call_tool_allows_write_when_allow_listed(monkeypatch):
    captured = {}
    monkeypatch.setattr(runner, "run_cli", lambda argv, **k: captured.setdefault("input", k.get("input_text")))
    result = server.call_tool("clipboard.set", {"text": "hi"}, {"allow_write_tools": ["clipboard.*"]})
    assert json.loads(result) == {"status": "copied"}
    assert captured["input"] == "hi"


def test_call_tool_allows_read_without_allow_list(monkeypatch):
    monkeypatch.setattr(runner, "run_cli", lambda *a, **k: "clipboard contents")
    result = server.call_tool("clipboard.get", {}, {})
    assert json.loads(result) == {"text": "clipboard contents"}


def test_call_tool_unknown_name_raises_lookup_error():
    with pytest.raises(LookupError):
        server.call_tool("nope.nope", {}, {})


def test_handle_tools_call_wraps_errors_as_json_rpc_error():
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "clipboard.set", "arguments": {"text": "hi"}}}
    with pytest.raises(WriteNotAllowedError):
        server.handle(message)


def test_wire_names_are_client_safe():
    import re
    result = server.handle({"method": "tools/list"})
    for t in result["tools"]:
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", t["name"]), t["name"]


def test_call_tool_accepts_wire_name(monkeypatch):
    from apple_bridge import runner
    monkeypatch.setattr(runner, "run_cli", lambda *a, **k: "clip")
    assert "clip" in server.call_tool("clipboard_get", {}, {})
