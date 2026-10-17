import sqlite3
import subprocess

import pytest

from apple_bridge import runner


def test_run_applescript_passes_args_via_argv(monkeypatch):
    captured = {}

    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = runner.run_applescript("on run argv\nend run", "arg1", "arg2")
    assert out == "ok\n"
    assert captured["argv"] == [runner.OSASCRIPT, "-e", "on run argv\nend run", "arg1", "arg2"]


def test_run_jxa_uses_javascript_flag(monkeypatch):
    captured = {}

    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = runner.run_jxa("function run(argv) {}", "x")
    assert out == "[]"
    assert captured["argv"][:3] == [runner.OSASCRIPT, "-l", "JavaScript"]


def test_run_cli_passes_stdin(monkeypatch):
    captured = {}

    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        captured["input"] = input
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner.run_cli(["/usr/bin/pbcopy"], input_text="hello")
    assert captured["input"] == "hello"


def test_nonzero_exit_raises_runner_error(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError, match="boom"):
        runner.run_cli(["/usr/bin/false"])


def test_timeout_raises_runner_error(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError, match="timed out"):
        runner.run_cli(["/usr/bin/sleep", "100"], timeout=1)


def test_osascript_timeout_hints_at_automation_prompt_with_app_name(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError) as excinfo:
        runner.run_applescript('tell application "Contacts"\nend tell', timeout=1)
    message = str(excinfo.value)
    assert "timed out after 1s" in message
    assert "Automation" in message
    assert "Contacts" in message
    assert "sshd" in message and "launchd" in message


def test_osascript_timeout_hints_generically_when_app_name_unknown(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError) as excinfo:
        runner.run_jxa("1 + 1", timeout=1)
    message = str(excinfo.value)
    assert "timed out after 1s" in message
    assert "Automation" in message


def test_non_osascript_timeout_keeps_plain_message(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError) as excinfo:
        runner.run_cli(["/usr/bin/sleep", "100"], timeout=1)
    message = str(excinfo.value)
    assert message == "/usr/bin/sleep timed out after 1s"


def test_osascript_not_authorized_exit_code_gives_permission_hint(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        stderr = "execution error: Not authorized to send Apple events to Contacts. (-1743)"
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError, match="Automation permission denied"):
        runner.run_applescript('tell application "Contacts"\nend tell')


def test_missing_binary_raises_runner_error(monkeypatch):
    def fake_run(argv, input=None, check=False, capture_output=False, text=False, timeout=None):
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(runner.RunnerError, match="not found"):
        runner.run_cli(["/no/such/binary"])


def test_query_sqlite_readonly_missing_db(tmp_path):
    with pytest.raises(runner.RunnerError, match="not found"):
        runner.query_sqlite_readonly(tmp_path / "missing.db", "SELECT 1")


def test_query_sqlite_readonly_happy_path(tmp_path):
    db_path = tmp_path / "test.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    connection.execute("INSERT INTO t VALUES (1, 'a')")
    connection.commit()
    connection.close()

    rows = runner.query_sqlite_readonly(db_path, "SELECT id, name FROM t WHERE id = ?", (1,))
    assert rows == [(1, "a")]
