"""Thin wrapper around subprocess for AppleScript/JXA and Apple CLIs.

All new app modules call through here (not `subprocess` directly) so tests
can mock Apple automation on non-macOS systems. Existing modules
(apple_events, imessage_send, messages_db) predate this and are left as-is.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 30
OSASCRIPT = "/usr/bin/osascript"

# Matches the first `tell application "X"` (AppleScript) or `Application("X")`
# (JXA) in a script, used only to make error hints more specific.
_APP_NAME_RE = re.compile(r'(?:tell application|Application)\s*\(\s*"([^"]+)"|tell application "([^"]+)"')

# macOS osascript error code for "not authorized to send Apple events".
_NOT_AUTHORIZED_CODE = "-1743"


class RunnerError(RuntimeError):
    """An osascript/CLI invocation failed."""


def run_applescript(script: str, *args: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run an AppleScript `on run argv` handler, passing args via argv (not
    string interpolation)."""
    return _run([OSASCRIPT, "-e", script, *args], timeout=timeout, script=script)


def run_jxa(script: str, *args: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run a JavaScript-for-Automation `run(argv)` function."""
    return _run([OSASCRIPT, "-l", "JavaScript", "-e", script, *args], timeout=timeout, script=script)


def run_cli(argv: list[str], input_text: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run an arbitrary CLI (shortcuts, pbcopy/pbpaste, mdfind, ...)."""
    return _run(argv, input_text=input_text, timeout=timeout)


def _extract_app_name(script: str) -> str | None:
    match = _APP_NAME_RE.search(script)
    if not match:
        return None
    return match.group(1) or match.group(2)


def _automation_prompt_hint(script: str | None) -> str:
    app = _extract_app_name(script) if script else None
    target = f"for {app} " if app else ""
    return (
        f" (macOS may be showing an Automation permission prompt {target}on the Mac "
        "screen for the process running python3 -- System Settings > Privacy & Security "
        "> Automation. Over ssh/launchd, that prompt may be attributed to sshd or "
        "launchd instead of python3, so check those entries too.)"
    )


def _run(
    argv: list[str], input_text: str | None = None, timeout: int = DEFAULT_TIMEOUT, script: str | None = None
) -> str:
    is_osascript = argv[0] == OSASCRIPT
    try:
        result = subprocess.run(
            argv, input=input_text, check=False, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        message = f"{argv[0]} timed out after {timeout}s"
        if is_osascript:
            message += _automation_prompt_hint(script)
        raise RunnerError(message) from error
    except FileNotFoundError as error:
        raise RunnerError(f"{argv[0]} not found: {error}") from error
    if result.returncode:
        message = f"{Path(argv[0]).name} failed (exit {result.returncode})"
        if result.stderr.strip():
            message += f": {result.stderr.strip()}"
        if is_osascript and _NOT_AUTHORIZED_CODE in result.stderr:
            message += (
                " -- Automation permission denied: macOS blocked this Apple Event. Check "
                "System Settings > Privacy & Security > Automation for the process running "
                "python3 (over ssh/launchd this may show up as sshd or launchd) and allow "
                "automating the target app."
            )
        raise RunnerError(message)
    return result.stdout


def query_sqlite_readonly(path: str | Path, sql: str, params: tuple = ()) -> list[tuple]:
    """Run a read-only query against a sqlite database (e.g. chat.db)."""
    path = Path(path)
    if not path.is_file():
        raise RunnerError(f"database not found: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    try:
        connection.execute("PRAGMA query_only = ON")
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()
