"""Messages app: send iMessages (imessage_send.py) and read/search the local
chat.db (messages_db.py). Reading requires Full Disk Access."""
from __future__ import annotations

import json
from contextlib import closing

from .. import config as config_module
from ..imessage_send import send_imessage
from ..messages_db import conversation_history, latest_rowid, open_messages, private_chat_id, search_messages
from ..safety import ToolDef


def _text(args: dict, field: str, required: bool = False, max_len: int = 4000) -> str:
    value = args.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer")
    return value


def _limit(args: dict, default: int = 20, maximum: int = 200) -> int:
    limit = int(args.get("limit", default))
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def send(args: dict) -> str:
    recipient = _text(args, "recipient", required=True, max_len=200)
    text = _text(args, "text", required=True)
    send_imessage(recipient, text)
    return json.dumps({"status": "sent", "recipient": recipient})


def history(args: dict) -> str:
    cfg = config_module.load()
    address = _text(args, "address", required=True, max_len=200)
    limit = _limit(args)
    with closing(open_messages(cfg["messages_db"])) as connection:
        chat_id = private_chat_id(connection, address)
        through = latest_rowid(connection, chat_id)
        return json.dumps(conversation_history(connection, chat_id, through, limit=limit), ensure_ascii=False, indent=2)


def search(args: dict) -> str:
    cfg = config_module.load()
    query = _text(args, "query", required=True, max_len=200)
    limit = _limit(args)
    with closing(open_messages(cfg["messages_db"])) as connection:
        return json.dumps(search_messages(connection, query, limit=limit), ensure_ascii=False, indent=2)


LIMIT_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 200, "default": 20}
TOOLS = [
    ToolDef(
        name="messages.send",
        description="Send an iMessage to a phone number or Apple ID email via Messages.app.",
        schema={"recipient": {"type": "string"}, "text": {"type": "string"}},
        handler=send,
        kind="write",
        required=["recipient", "text"],
    ),
    ToolDef(
        name="messages.history",
        description="Read recent messages in a one-to-one iMessage chat with an address.",
        schema={"address": {"type": "string"}, "limit": LIMIT_SCHEMA},
        handler=history,
        kind="read",
        required=["address"],
    ),
    ToolDef(
        name="messages.search",
        description="Search message text across all chats (most recent first).",
        schema={"query": {"type": "string"}, "limit": LIMIT_SCHEMA},
        handler=search,
        kind="read",
        required=["query"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
