"""Thin wrapper around subprocess for AppleScript/JXA and Apple CLIs.

All new app modules call through here (not `subprocess` directly) so tests
can mock Apple automation on non-macOS systems. Existing modules
(apple_events, imessage_send, messages_db) predate this and are left as-is.
"""
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 30
OSASCRIPT = "/usr/bin/osascript"


class RunnerError(RuntimeError):
    """An osascript/CLI invocation failed."""


def run_applescript(script: str, *args: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run an AppleScript `on run argv` handler, passing args via argv (not
    string interpolation)."""
    return _run([OSASCRIPT, "-e", script, *args], timeout=timeout)


def run_jxa(script: str, *args: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run a JavaScript-for-Automation `run(argv)` function."""
    return _run([OSASCRIPT, "-l", "JavaScript", "-e", script, *args], timeout=timeout)


def run_cli(argv: list[str], input_text: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run an arbitrary CLI (shortcuts, pbcopy/pbpaste, mdfind, ...)."""
    return _run(argv, input_text=input_text, timeout=timeout)


def _run(argv: list[str], input_text: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            argv, input=input_text, check=False, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise RunnerError(f"{argv[0]} timed out after {timeout}s") from error
    except FileNotFoundError as error:
        raise RunnerError(f"{argv[0]} not found: {error}") from error
    if result.returncode:
        message = f"{Path(argv[0]).name} failed (exit {result.returncode})"
        if result.stderr.strip():
            message += f": {result.stderr.strip()}"
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
