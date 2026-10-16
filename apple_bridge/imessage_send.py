"""Send an iMessage through Messages.app using AppleScript."""
from __future__ import annotations

import argparse
import subprocess
import sys

_SEND_SCRIPT = """
on run argv
    set recipientAddress to item 1 of argv
    set messageText to item 2 of argv
    tell application "Messages"
        set targetService to first service whose service type = iMessage
        set targetBuddy to buddy recipientAddress of targetService
        send messageText to targetBuddy
    end tell
end run
"""


def send_imessage(recipient: str, text: str) -> None:
    """Send `text` to `recipient` (phone number or Apple ID email) as the
    account currently signed in to Messages.app."""
    if not recipient.strip():
        raise ValueError("An iMessage recipient is required")
    if not text.strip():
        raise ValueError("An iMessage body is required")
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", _SEND_SCRIPT, recipient, text],
        check=False, capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        message = f"Messages AppleScript failed (exit {result.returncode})"
        if result.stderr.strip():
            message += f": {result.stderr.strip()}"
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send an iMessage. Reads the body from stdin if --text is omitted.")
    parser.add_argument("recipient", help="phone number (+447700900000) or Apple ID email")
    parser.add_argument("--text", help="message body")
    args = parser.parse_args()
    send_imessage(args.recipient, args.text if args.text is not None else sys.stdin.read())
    print("submitted to Messages (delivery is not verified)")


if __name__ == "__main__":
    main()
