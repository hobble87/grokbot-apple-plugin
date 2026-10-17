import json

import pytest

from apple_bridge.apps import messages as messages_app


def test_send_validates_recipient_and_text(monkeypatch):
    calls = []
    monkeypatch.setattr(messages_app, "send_imessage", lambda r, t: calls.append((r, t)))
    result = messages_app.send({"recipient": "+447700900000", "text": "hello"})
    assert json.loads(result) == {"status": "sent", "recipient": "+447700900000"}
    assert calls == [("+447700900000", "hello")]


def test_send_rejects_empty_recipient(monkeypatch):
    monkeypatch.setattr(messages_app, "send_imessage", lambda r, t: None)
    with pytest.raises(ValueError):
        messages_app.send({"recipient": "  ", "text": "hi"})


def test_history_uses_messages_db_helpers(monkeypatch):
    monkeypatch.setattr(messages_app, "open_messages", lambda path: _FakeConnection())
    monkeypatch.setattr(messages_app, "private_chat_id", lambda conn, address: 42)
    monkeypatch.setattr(messages_app, "latest_rowid", lambda conn, chat_id: 99)
    monkeypatch.setattr(messages_app, "conversation_history", lambda conn, chat_id, through, limit: [{"role": "user", "content": "hi"}])

    result = messages_app.history({"address": "+447700900000", "limit": 5})
    assert json.loads(result) == [{"role": "user", "content": "hi"}]


def test_history_rejects_bad_limit():
    with pytest.raises(ValueError):
        messages_app.history({"address": "a", "limit": 0})


def test_search_uses_search_messages(monkeypatch):
    monkeypatch.setattr(messages_app, "open_messages", lambda path: _FakeConnection())
    monkeypatch.setattr(messages_app, "search_messages", lambda conn, query, limit: [{"text": query}])

    result = messages_app.search({"query": "dinner"})
    assert json.loads(result) == [{"text": "dinner"}]


def test_search_requires_query():
    with pytest.raises(ValueError):
        messages_app.search({"query": ""})


class _FakeConnection:
    def close(self):
        pass
