from apple_bridge import calendar_mcp


def test_tool_list_unchanged():
    names = {t["name"] for t in calendar_mcp.tool_list()}
    assert names == {
        "apple_setup_check", "apple_calendar_list", "apple_reminders_list",
        "apple_calendar_create", "apple_calendar_update",
        "apple_reminder_create", "apple_reminder_update",
    }


def test_handle_initialize():
    result = calendar_mcp.handle({"method": "initialize", "params": {}})
    assert result["serverInfo"]["name"] == "apple-bridge-calendar"


def test_handle_tools_list():
    result = calendar_mcp.handle({"method": "tools/list"})
    assert any(t["name"] == "apple_calendar_list" for t in result["tools"])
