import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import mail


def test_list_accounts_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '[{"name": "iCloud", "emailAddresses": ["you@example.com"]}]')
    assert json.loads(mail.list_accounts({})) == [{"name": "iCloud", "emailAddresses": ["you@example.com"]}]


def test_list_mailboxes_passes_account(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '[{"account": "iCloud", "mailboxes": ["INBOX"]}]'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = mail.list_mailboxes({"account": "iCloud"})
    assert captured["args"] == ("iCloud",)
    assert json.loads(result) == [{"account": "iCloud", "mailboxes": ["INBOX"]}]


def test_list_messages_passes_mailbox_account_and_limit(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '[{"id": 1, "subject": "Hi"}]'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = mail.list_messages({"mailbox": "INBOX", "account": "iCloud", "limit": 5})
    assert captured["args"] == ("INBOX", "iCloud", "5")
    assert json.loads(result) == [{"id": 1, "subject": "Hi"}]


def test_list_messages_requires_mailbox():
    with pytest.raises(ValueError):
        mail.list_messages({"mailbox": ""})


def test_search_passes_query_field_and_scope(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return "[]"

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    mail.search({"query": "invoice", "field": "sender", "mailbox": "INBOX", "account": "iCloud", "limit": 10})
    assert captured["args"] == ("invoice", "sender", "INBOX", "iCloud", "10")


def test_search_rejects_invalid_field():
    with pytest.raises(ValueError):
        mail.search({"query": "invoice", "field": "bogus"})


def test_search_requires_query():
    with pytest.raises(ValueError):
        mail.search({"query": ""})


def test_read_message_requires_integer_message_id():
    with pytest.raises(ValueError):
        mail.read_message({"mailbox": "INBOX", "message_id": "not-an-int"})


def test_read_message_passes_args(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"id": 42, "subject": "Hi", "content": "body"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = mail.read_message({"mailbox": "INBOX", "account": "iCloud", "message_id": 42})
    assert captured["args"] == ("INBOX", "iCloud", "42")
    assert json.loads(result) == {"id": 42, "subject": "Hi", "content": "body"}


def test_create_draft_passes_recipients(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"status": "draft_created"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = mail.create_draft({"to": "a@example.com, b@example.com", "subject": "Hi", "body": "Hello", "cc": "c@example.com"})
    assert captured["args"] == ("a@example.com, b@example.com", "Hi", "Hello", "c@example.com")
    assert json.loads(result) == {"status": "draft_created"}


def test_create_draft_requires_to():
    with pytest.raises(ValueError):
        mail.create_draft({"to": ""})


def test_send_passes_recipients(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"status": "sent"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = mail.send({"to": "a@example.com", "subject": "Hi", "body": "Hello"})
    assert captured["args"] == ("a@example.com", "Hi", "Hello", "")
    assert json.loads(result) == {"status": "sent"}


def test_send_requires_to():
    with pytest.raises(ValueError):
        mail.send({"to": "  "})
