import sqlite3

from apple_bridge.messages_db import search_messages


def _make_db(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT);
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT, date INTEGER,
            is_from_me INTEGER, handle_id INTEGER, service TEXT,
            is_system_message INTEGER, item_type INTEGER, associated_message_type INTEGER
        );
        """
    )
    connection.execute("INSERT INTO handle VALUES (1, 'friend@example.com')")
    connection.execute(
        "INSERT INTO message VALUES (1, 'g1', 'lets get dinner tonight', 1000, 0, 1, 'iMessage', 0, 0, 0)"
    )
    connection.execute(
        "INSERT INTO message VALUES (2, 'g2', 'unrelated message', 2000, 1, 1, 'iMessage', 0, 0, 0)"
    )
    connection.commit()
    return connection


def test_search_messages_matches_substring(tmp_path):
    connection = _make_db(tmp_path / "chat.db")
    results = search_messages(connection, "dinner")
    assert len(results) == 1
    assert results[0]["text"] == "lets get dinner tonight"
    assert results[0]["handle"] == "friend@example.com"
    assert results[0]["from_me"] is False


def test_search_messages_escapes_like_wildcards(tmp_path):
    connection = _make_db(tmp_path / "chat.db")
    assert search_messages(connection, "%") == []
