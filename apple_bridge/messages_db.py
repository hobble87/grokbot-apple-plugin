"""Read-only access to the local Messages database (~/Library/Messages/chat.db).

Requires Full Disk Access for the process (Terminal, python3, or the launchd job).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_REAL_MESSAGE = """
  AND COALESCE(m.is_system_message, 0) = 0
  AND COALESCE(m.item_type, 0) = 0
  AND COALESCE(m.associated_message_type, 0) = 0
"""


def open_messages(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Messages database not found: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    connection.execute("PRAGMA query_only = ON")
    return connection


def private_chat_id(connection: sqlite3.Connection, address: str) -> int:
    """Return the most recent one-to-one chat with `address`."""
    rows = connection.execute(
        """
        SELECT c.ROWID, MAX(m.ROWID) AS latest_message
        FROM chat AS c
        JOIN chat_handle_join AS chj ON chj.chat_id = c.ROWID
        JOIN handle AS h ON h.ROWID = chj.handle_id
        LEFT JOIN chat_message_join AS cmj ON cmj.chat_id = c.ROWID
        LEFT JOIN message AS m ON m.ROWID = cmj.message_id
        WHERE lower(h.id) = lower(?)
          AND (SELECT COUNT(*) FROM chat_handle_join WHERE chat_id = c.ROWID) = 1
        GROUP BY c.ROWID
        ORDER BY latest_message DESC
        """,
        (address,),
    ).fetchall()
    if not rows:
        raise LookupError(f"No one-to-one iMessage chat with {address}. Exchange one message first.")
    return int(rows[0][0])


def latest_rowid(connection: sqlite3.Connection, chat_id: int) -> int:
    row = connection.execute(
        """SELECT COALESCE(MAX(m.ROWID), 0) FROM message AS m
           JOIN chat_message_join AS cmj ON cmj.message_id = m.ROWID
           WHERE cmj.chat_id = ?""",
        (chat_id,),
    ).fetchone()
    return int(row[0])


def incoming_messages(connection: sqlite3.Connection, chat_id: int, after_rowid: int) -> list[dict]:
    """New inbound iMessages (not sent by you, not tapbacks/system items).

    Note: on recent macOS versions some messages store their body only in
    `attributedBody`; those come back with empty text here.
    """
    rows = connection.execute(
        f"""
        SELECT m.ROWID, m.guid, m.text, m.date
        FROM message AS m
        JOIN chat_message_join AS cmj ON cmj.message_id = m.ROWID
        WHERE cmj.chat_id = ? AND m.ROWID > ? AND m.is_from_me = 0
          AND lower(COALESCE(m.service, '')) = 'imessage'
          {_REAL_MESSAGE}
        ORDER BY m.ROWID
        """,
        (chat_id, after_rowid),
    ).fetchall()
    return [
        {"rowid": int(r), "guid": g, "text": (t or "").strip(), "apple_date": d}
        for r, g, t, d in rows
    ]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_messages(connection: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Search message text across all chats (most recent first)."""
    rows = connection.execute(
        f"""
        SELECT m.ROWID, m.guid, m.text, m.date, m.is_from_me, h.id
        FROM message AS m
        LEFT JOIN handle AS h ON h.ROWID = m.handle_id
        WHERE m.text LIKE ? ESCAPE '\\'
          {_REAL_MESSAGE}
        ORDER BY m.ROWID DESC LIMIT ?
        """,
        (f"%{_escape_like(query)}%", limit),
    ).fetchall()
    return [
        {"rowid": int(r), "guid": g, "text": (t or "").strip(), "apple_date": d, "from_me": bool(fm), "handle": h}
        for r, g, t, d, fm, h in rows
    ]


def conversation_history(connection: sqlite3.Connection, chat_id: int, through_rowid: int, limit: int = 8) -> list[dict]:
    rows = connection.execute(
        f"""
        SELECT m.is_from_me, m.text
        FROM message AS m
        JOIN chat_message_join AS cmj ON cmj.message_id = m.ROWID
        WHERE cmj.chat_id = ? AND m.ROWID <= ? AND m.text IS NOT NULL
          {_REAL_MESSAGE}
        ORDER BY m.ROWID DESC LIMIT ?
        """,
        (chat_id, through_rowid, limit),
    ).fetchall()
    return [
        {"role": "assistant" if mine else "user", "content": text.strip()}
        for mine, text in reversed(rows) if text and text.strip()
    ]
