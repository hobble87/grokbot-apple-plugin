"""Mail app: listing accounts/mailboxes/messages and searching are read-only;
creating a draft and sending mail are writes. Driven by JXA against
Mail.app. Requires the Mail Automation permission."""
from __future__ import annotations

from .. import runner
from ..safety import ToolDef

_FIND_MAILBOX_HELPER = r"""
function findMailbox(Mail, mailboxName, accountName) {
    var accounts = accountName ? Mail.accounts.whose({name: accountName})() : Mail.accounts();
    for (var i = 0; i < accounts.length; i++) {
        var matches = accounts[i].mailboxes.whose({name: mailboxName})();
        if (matches.length > 0) return matches[0];
    }
    throw new Error("mailbox not found: " + mailboxName);
}
"""

_LIST_ACCOUNTS_SCRIPT = r"""
function run(argv) {
    var Mail = Application("Mail");
    var accounts = Mail.accounts();
    var out = [];
    for (var i = 0; i < accounts.length; i++) {
        out.push({name: accounts[i].name(), emailAddresses: accounts[i].emailAddresses()});
    }
    return JSON.stringify(out);
}
"""

_LIST_MAILBOXES_SCRIPT = _FIND_MAILBOX_HELPER + r"""
function run(argv) {
    var accountName = argv[0];
    var Mail = Application("Mail");
    var accounts = accountName ? Mail.accounts.whose({name: accountName})() : Mail.accounts();
    var out = [];
    for (var i = 0; i < accounts.length; i++) {
        var boxes = accounts[i].mailboxes();
        var names = [];
        for (var j = 0; j < boxes.length; j++) names.push(boxes[j].name());
        out.push({account: accounts[i].name(), mailboxes: names});
    }
    return JSON.stringify(out);
}
"""

_LIST_MESSAGES_SCRIPT = _FIND_MAILBOX_HELPER + r"""
function run(argv) {
    var mailboxName = argv[0];
    var accountName = argv[1];
    var limit = parseInt(argv[2], 10) || 20;
    var Mail = Application("Mail");
    var mailbox = findMailbox(Mail, mailboxName, accountName);
    var messages = mailbox.messages();
    var out = [];
    for (var i = 0; i < messages.length && out.length < limit; i++) {
        var m = messages[i];
        out.push({id: m.id(), subject: m.subject(), sender: m.sender(), dateReceived: m.dateReceived().toISOString(), readStatus: m.readStatus()});
    }
    return JSON.stringify(out);
}
"""

_SEARCH_SCRIPT = r"""
function run(argv) {
    var query = argv[0].toLowerCase();
    var field = argv[1];
    var mailboxName = argv[2];
    var accountName = argv[3];
    var limit = parseInt(argv[4], 10) || 20;
    var Mail = Application("Mail");
    var mailboxes = [];
    if (mailboxName) {
        var accounts = accountName ? Mail.accounts.whose({name: accountName})() : Mail.accounts();
        for (var i = 0; i < accounts.length; i++) {
            var matches = accounts[i].mailboxes.whose({name: mailboxName})();
            for (var j = 0; j < matches.length; j++) mailboxes.push(matches[j]);
        }
    } else {
        var accounts2 = accountName ? Mail.accounts.whose({name: accountName})() : Mail.accounts();
        for (var i = 0; i < accounts2.length; i++) {
            var boxes = accounts2[i].mailboxes();
            for (var j = 0; j < boxes.length; j++) mailboxes.push(boxes[j]);
        }
    }
    var out = [];
    for (var b = 0; b < mailboxes.length && out.length < limit; b++) {
        var messages = mailboxes[b].messages();
        for (var i = 0; i < messages.length && out.length < limit; i++) {
            var m = messages[i];
            var subject = m.subject();
            var sender = m.sender();
            var subjectMatch = field !== "sender" && subject.toLowerCase().indexOf(query) !== -1;
            var senderMatch = field !== "subject" && sender.toLowerCase().indexOf(query) !== -1;
            if (subjectMatch || senderMatch) {
                out.push({id: m.id(), subject: subject, sender: sender, mailbox: mailboxes[b].name(), dateReceived: m.dateReceived().toISOString()});
            }
        }
    }
    return JSON.stringify(out);
}
"""

_READ_MESSAGE_SCRIPT = _FIND_MAILBOX_HELPER + r"""
function run(argv) {
    var mailboxName = argv[0];
    var accountName = argv[1];
    var messageId = parseInt(argv[2], 10);
    var Mail = Application("Mail");
    var mailbox = findMailbox(Mail, mailboxName, accountName);
    var matches = mailbox.messages.whose({id: messageId})();
    if (matches.length === 0) throw new Error("message not found: " + messageId);
    var m = matches[0];
    return JSON.stringify({
        id: m.id(), subject: m.subject(), sender: m.sender(),
        dateReceived: m.dateReceived().toISOString(), content: m.content(),
    });
}
"""

_SEND_RECIPIENTS_HELPER = r"""
function splitAddresses(value) {
    if (!value) return [];
    return value.split(",").map(function (s) { return s.trim(); }).filter(function (s) { return s; });
}
"""

_CREATE_DRAFT_SCRIPT = _SEND_RECIPIENTS_HELPER + r"""
function run(argv) {
    var to = splitAddresses(argv[0]);
    var subject = argv[1];
    var body = argv[2];
    var cc = splitAddresses(argv[3]);
    var Mail = Application("Mail");
    var draft = Mail.OutgoingMessage({subject: subject, content: body, visible: true});
    Mail.outgoingMessages.push(draft);
    for (var i = 0; i < to.length; i++) draft.toRecipients.push(Mail.ToRecipient({address: to[i]}));
    for (var i = 0; i < cc.length; i++) draft.ccRecipients.push(Mail.CcRecipient({address: cc[i]}));
    draft.save();
    return JSON.stringify({status: "draft_created", subject: subject, to: to});
}
"""

_SEND_SCRIPT = _SEND_RECIPIENTS_HELPER + r"""
function run(argv) {
    var to = splitAddresses(argv[0]);
    var subject = argv[1];
    var body = argv[2];
    var cc = splitAddresses(argv[3]);
    var Mail = Application("Mail");
    var message = Mail.OutgoingMessage({subject: subject, content: body, visible: false});
    Mail.outgoingMessages.push(message);
    for (var i = 0; i < to.length; i++) message.toRecipients.push(Mail.ToRecipient({address: to[i]}));
    for (var i = 0; i < cc.length; i++) message.ccRecipients.push(Mail.CcRecipient({address: cc[i]}));
    message.send();
    return JSON.stringify({status: "sent", subject: subject, to: to});
}
"""


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


def _limit(args: dict, default: int = 20, maximum: int = 100) -> int:
    limit = int(args.get("limit", default))
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return limit


def list_accounts(_args: dict) -> str:
    output = runner.run_jxa(_LIST_ACCOUNTS_SCRIPT)
    return output.strip() or "[]"


def list_mailboxes(args: dict) -> str:
    account = _text(args, "account", max_len=200)
    output = runner.run_jxa(_LIST_MAILBOXES_SCRIPT, account)
    return output.strip() or "[]"


def list_messages(args: dict) -> str:
    mailbox = _text(args, "mailbox", required=True, max_len=200)
    account = _text(args, "account", max_len=200)
    output = runner.run_jxa(_LIST_MESSAGES_SCRIPT, mailbox, account, str(_limit(args)))
    return output.strip() or "[]"


def search(args: dict) -> str:
    query = _text(args, "query", required=True, max_len=200)
    field = args.get("field", "both")
    if field not in ("subject", "sender", "both"):
        raise ValueError('field must be "subject", "sender", or "both"')
    mailbox = _text(args, "mailbox", max_len=200)
    account = _text(args, "account", max_len=200)
    output = runner.run_jxa(_SEARCH_SCRIPT, query, "" if field == "both" else field, mailbox, account, str(_limit(args)))
    return output.strip() or "[]"


def read_message(args: dict) -> str:
    mailbox = _text(args, "mailbox", required=True, max_len=200)
    account = _text(args, "account", max_len=200)
    message_id = args.get("message_id")
    if not isinstance(message_id, int):
        raise ValueError("message_id is required and must be an integer")
    return runner.run_jxa(_READ_MESSAGE_SCRIPT, mailbox, account, str(message_id)).strip()


def create_draft(args: dict) -> str:
    to = _text(args, "to", required=True, max_len=2000)
    subject = _text(args, "subject", max_len=500)
    body = _text(args, "body", max_len=20000)
    cc = _text(args, "cc", max_len=2000)
    return runner.run_jxa(_CREATE_DRAFT_SCRIPT, to, subject, body, cc).strip()


def send(args: dict) -> str:
    to = _text(args, "to", required=True, max_len=2000)
    subject = _text(args, "subject", max_len=500)
    body = _text(args, "body", max_len=20000)
    cc = _text(args, "cc", max_len=2000)
    return runner.run_jxa(_SEND_SCRIPT, to, subject, body, cc).strip()


LIMIT_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
TOOLS = [
    ToolDef(
        name="mail.list_accounts",
        description="List Mail.app accounts and their email addresses.",
        schema={},
        handler=list_accounts,
        kind="read",
    ),
    ToolDef(
        name="mail.list_mailboxes",
        description="List mailboxes, optionally for a single account.",
        schema={"account": {"type": "string"}},
        handler=list_mailboxes,
        kind="read",
    ),
    ToolDef(
        name="mail.list_messages",
        description="List recent messages in a mailbox (subject, sender, date, read status).",
        schema={"mailbox": {"type": "string"}, "account": {"type": "string"}, "limit": LIMIT_SCHEMA},
        handler=list_messages,
        kind="read",
        required=["mailbox"],
    ),
    ToolDef(
        name="mail.search",
        description="Search messages by subject and/or sender, optionally scoped to one mailbox/account.",
        schema={
            "query": {"type": "string"},
            "field": {"type": "string", "enum": ["subject", "sender", "both"], "default": "both"},
            "mailbox": {"type": "string"},
            "account": {"type": "string"},
            "limit": LIMIT_SCHEMA,
        },
        handler=search,
        kind="read",
        required=["query"],
    ),
    ToolDef(
        name="mail.read_message",
        description="Read the full content of one message by id within a mailbox.",
        schema={"mailbox": {"type": "string"}, "account": {"type": "string"}, "message_id": {"type": "integer"}},
        handler=read_message,
        kind="read",
        required=["mailbox", "message_id"],
    ),
    ToolDef(
        name="mail.create_draft",
        description="Create a draft email (comma-separated recipients) without sending it.",
        schema={"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "cc": {"type": "string"}},
        handler=create_draft,
        kind="write",
        required=["to"],
    ),
    ToolDef(
        name="mail.send",
        description="Compose and immediately send an email (comma-separated recipients).",
        schema={"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "cc": {"type": "string"}},
        handler=send,
        kind="write",
        required=["to"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
