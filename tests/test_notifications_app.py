import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import notifications


def test_display_passes_text_title_subtitle(monkeypatch):
    captured = {}

    def fake_run_applescript(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return ""

    monkeypatch.setattr(runner, "run_applescript", fake_run_applescript)
    result = notifications.display({"text": "Build finished", "title": "CI", "subtitle": "main branch"})
    assert captured["args"] == ("Build finished", "CI", "main branch")
    assert json.loads(result) == {"status": "sent"}


def test_display_defaults_title_when_missing(monkeypatch):
    captured = {}

    def fake_run_applescript(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return ""

    monkeypatch.setattr(runner, "run_applescript", fake_run_applescript)
    notifications.display({"text": "hello"})
    assert captured["args"] == ("hello", "Apple Bridge", "")


def test_display_requires_text():
    with pytest.raises(ValueError):
        notifications.display({"text": ""})
