import pytest

from apple_bridge.safety import ToolDef, WriteNotAllowedError, check_write_allowed, is_write_allowed, visible_tools


def _tool(name="notes.create", kind="write"):
    return ToolDef(name=name, description="d", schema={}, handler=lambda args: "ok", kind=kind)


def test_tool_name_requires_dot():
    with pytest.raises(ValueError):
        ToolDef(name="noapp", description="d", schema={}, handler=lambda a: "x", kind="read")


def test_kind_must_be_read_or_write():
    with pytest.raises(ValueError):
        _tool(kind="delete")


def test_is_write_allowed_exact_name():
    assert is_write_allowed("notes.create", ["notes.create"])
    assert not is_write_allowed("notes.create", ["notes.list"])


def test_is_write_allowed_wildcard():
    assert is_write_allowed("notes.create", ["notes.*"])
    assert not is_write_allowed("calendar.create_event", ["notes.*"])


def test_check_write_allowed_blocks_by_default():
    tool = _tool()
    with pytest.raises(WriteNotAllowedError):
        check_write_allowed(tool, {})


def test_check_write_allowed_passes_when_listed():
    tool = _tool()
    check_write_allowed(tool, {"allow_write_tools": ["notes.*"]})  # no raise


def test_check_write_allowed_ignores_read_tools():
    tool = _tool(name="notes.list", kind="read")
    check_write_allowed(tool, {})  # no raise, reads are unrestricted


def test_visible_tools_filters_disabled_apps():
    tools = [_tool(name="notes.create"), _tool(name="clipboard.get", kind="read")]
    out = visible_tools(tools, {"disabled_apps": ["notes"]})
    assert [t.name for t in out] == ["clipboard.get"]


def test_allow_list_accepts_wire_form_names():
    from apple_bridge.safety import is_write_allowed
    assert is_write_allowed("clipboard.set", ["clipboard_set"])
    assert is_write_allowed("clipboard.set", ["clipboard_*"])
    assert not is_write_allowed("clipboard.set", ["mail_*"])
