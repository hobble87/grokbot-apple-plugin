import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import finder


def test_selection_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '["/Users/you/Desktop/file.txt"]')
    assert json.loads(finder.selection({})) == ["/Users/you/Desktop/file.txt"]


def test_selection_defaults_to_empty_list(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: "")
    assert finder.selection({}) == "[]"


def test_spotlight_search_passes_query_and_truncates_to_limit(monkeypatch):
    captured = {}

    def fake_run_cli(argv, **k):
        captured["argv"] = argv
        return "/a/one.txt\n/a/two.txt\n/a/three.txt\n"

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)
    result = finder.spotlight_search({"query": "report", "limit": 2})
    assert captured["argv"] == [finder.MDFIND_BIN, "report"]
    assert json.loads(result) == ["/a/one.txt", "/a/two.txt"]


def test_spotlight_search_requires_query():
    with pytest.raises(ValueError):
        finder.spotlight_search({"query": ""})


def test_reveal_passes_path(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"status": "revealed", "path": "/Users/you/Desktop"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = finder.reveal({"path": "/Users/you/Desktop"})
    assert captured["args"] == ("/Users/you/Desktop",)
    assert json.loads(result) == {"status": "revealed", "path": "/Users/you/Desktop"}


def test_reveal_requires_path():
    with pytest.raises(ValueError):
        finder.reveal({"path": ""})


def test_open_path_calls_open_cli(monkeypatch):
    captured = {}

    def fake_run_cli(argv, **k):
        captured["argv"] = argv
        return ""

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)
    result = finder.open_path({"path": "/Users/you/Documents/report.pdf"})
    assert captured["argv"] == [finder.OPEN_BIN, "/Users/you/Documents/report.pdf"]
    assert json.loads(result) == {"status": "opened", "path": "/Users/you/Documents/report.pdf"}


def test_open_path_requires_path():
    with pytest.raises(ValueError):
        finder.open_path({"path": ""})
