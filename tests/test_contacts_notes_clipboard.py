import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import clipboard, contacts, notes


def test_contacts_search_passes_query_and_limit(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '[{"id": "1", "name": "Alex Example", "emails": [], "phones": []}]'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = contacts.search({"query": "Alex", "limit": 5})
    assert captured["args"] == ("Alex", "5")
    assert json.loads(result) == [{"id": "1", "name": "Alex Example", "emails": [], "phones": []}]


def test_contacts_search_requires_query():
    with pytest.raises(ValueError):
        contacts.search({"query": ""})


def test_notes_list_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: "[]")
    assert notes.list_notes({}) == "[]"


def test_notes_create_passes_title_body_folder(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"id": "x-note-1"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = notes.create({"title": "Groceries", "body": "milk, eggs", "folder": "Personal"})
    assert captured["args"] == ("Groceries", "milk, eggs", "Personal")
    assert json.loads(result) == {"id": "x-note-1"}


def test_notes_create_requires_title():
    with pytest.raises(ValueError):
        notes.create({"title": ""})


def test_clipboard_get_wraps_pbpaste_output(monkeypatch):
    monkeypatch.setattr(runner, "run_cli", lambda argv, **k: "copied text")
    assert json.loads(clipboard.get({})) == {"text": "copied text"}


def test_clipboard_set_passes_input_text(monkeypatch):
    captured = {}

    def fake_run_cli(argv, input_text=None, timeout=runner.DEFAULT_TIMEOUT):
        captured["argv"] = argv
        captured["input_text"] = input_text
        return ""

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)
    result = clipboard.set_clipboard({"text": "hello clipboard"})
    assert json.loads(result) == {"status": "copied"}
    assert captured["argv"] == ["/usr/bin/pbcopy"]
    assert captured["input_text"] == "hello clipboard"


def test_clipboard_set_rejects_non_string():
    with pytest.raises(ValueError):
        clipboard.set_clipboard({"text": 123})
