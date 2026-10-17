import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import shortcuts


def test_list_shortcuts_splits_lines(monkeypatch):
    monkeypatch.setattr(runner, "run_cli", lambda argv, **k: "Morning Routine\nTurn Off Lights\n")
    result = shortcuts.list_shortcuts({})
    assert json.loads(result) == ["Morning Routine", "Turn Off Lights"]


def test_run_shortcut_without_input(monkeypatch):
    captured = {}

    def fake_run_cli(argv, input_text=None, timeout=runner.DEFAULT_TIMEOUT):
        captured["argv"] = argv
        captured["input_text"] = input_text
        return "done\n"

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)
    result = shortcuts.run_shortcut({"name": "Morning Routine"})
    assert captured["argv"] == [shortcuts.SHORTCUTS_BIN, "run", "Morning Routine"]
    assert captured["input_text"] is None
    assert json.loads(result) == {"name": "Morning Routine", "output": "done"}


def test_run_shortcut_with_input_pipes_stdin(monkeypatch):
    captured = {}

    def fake_run_cli(argv, input_text=None, timeout=runner.DEFAULT_TIMEOUT):
        captured["argv"] = argv
        captured["input_text"] = input_text
        return ""

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)
    shortcuts.run_shortcut({"name": "Echo", "input": "hello"})
    assert captured["argv"] == [shortcuts.SHORTCUTS_BIN, "run", "Echo", "-i", "-"]
    assert captured["input_text"] == "hello"


def test_run_shortcut_requires_name():
    with pytest.raises(ValueError):
        shortcuts.run_shortcut({"name": ""})


def test_run_shortcut_rejects_non_string_input():
    with pytest.raises(ValueError):
        shortcuts.run_shortcut({"name": "x", "input": 5})
