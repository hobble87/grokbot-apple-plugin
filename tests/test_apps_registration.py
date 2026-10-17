from apple_bridge.apps import collect_tools
from apple_bridge.safety import ToolDef


def test_collect_tools_returns_tooldefs():
    tools = collect_tools()
    assert tools
    assert all(isinstance(t, ToolDef) for t in tools)


def test_collect_tools_names_are_unique():
    tools = collect_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names))


def test_every_app_is_represented():
    tools = collect_tools()
    apps = {t.name.split(".", 1)[0] for t in tools}
    assert apps == {"calendar", "reminders", "messages", "contacts", "notes", "clipboard"}


def test_write_tools_include_expected_mutations():
    tools = {t.name: t for t in collect_tools()}
    expected_writes = {
        "calendar.create_event", "calendar.update_event",
        "reminders.create", "reminders.update",
        "messages.send", "notes.create", "clipboard.set",
    }
    actual_writes = {name for name, t in tools.items() if t.kind == "write"}
    assert actual_writes == expected_writes


def test_schemas_are_plain_dicts():
    for tool in collect_tools():
        assert isinstance(tool.schema, dict)
        assert isinstance(tool.required, list)
