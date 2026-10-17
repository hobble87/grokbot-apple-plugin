import json

from apple_bridge import calendar_mcp
from apple_bridge.apps import calendar as calendar_app
from apple_bridge.apps import reminders as reminders_app


def _configure(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(json.dumps({"calendar": "Shared", "reminders_list": "Shared"}))


def test_calendar_create_event_delegates_to_apple_events(isolated_config, monkeypatch):
    _configure(isolated_config, monkeypatch)
    monkeypatch.setattr(calendar_mcp, "call_apple_events", lambda *a: {"id": "abc-123"})
    tool = {t.name: t for t in calendar_app.tools()}["calendar.create_event"]
    result = tool.handler({"title": "Standup", "start": "2026-01-01T09:00:00", "end": "2026-01-01T09:15:00"})
    assert json.loads(result) == {"status": "created", "id": "abc-123"}


def test_calendar_list_events_is_read(isolated_config, monkeypatch):
    _configure(isolated_config, monkeypatch)
    monkeypatch.setattr(calendar_mcp, "call_apple_events", lambda *a: [])
    tool = {t.name: t for t in calendar_app.tools()}["calendar.list_events"]
    assert tool.kind == "read"
    assert json.loads(tool.handler({})) == []


def test_reminders_create_delegates_to_apple_events(isolated_config, monkeypatch):
    _configure(isolated_config, monkeypatch)
    monkeypatch.setattr(calendar_mcp, "call_apple_events", lambda *a: {"id": "r-1"})
    tool = {t.name: t for t in reminders_app.tools()}["reminders.create"]
    result = tool.handler({"title": "Buy milk"})
    assert json.loads(result) == {"status": "created", "id": "r-1"}


def test_reminders_list_is_read(isolated_config, monkeypatch):
    _configure(isolated_config, monkeypatch)
    monkeypatch.setattr(calendar_mcp, "call_apple_events", lambda *a: [])
    tool = {t.name: t for t in reminders_app.tools()}["reminders.list"]
    assert tool.kind == "read"
