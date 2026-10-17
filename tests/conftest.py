import pytest


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point every test at a scratch config file/state dir so nothing touches
    a real config.json or ~/Library paths."""
    monkeypatch.setenv("APPLE_BRIDGE_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("APPLE_BRIDGE_STATE_DIR", str(tmp_path / "work"))
    monkeypatch.setenv("APPLE_BRIDGE_MESSAGES_DB", str(tmp_path / "chat.db"))
    monkeypatch.setenv("APPLE_BRIDGE_SAFARI_BOOKMARKS_PLIST", str(tmp_path / "Bookmarks.plist"))
    monkeypatch.setenv("APPLE_BRIDGE_FINDMY_CACHE_DIR", str(tmp_path / "fmipcore"))
    monkeypatch.delenv("APPLE_BRIDGE_ALLOWED_CONTACTS", raising=False)
    monkeypatch.delenv("APPLE_BRIDGE_ALLOW_WRITE_TOOLS", raising=False)
    monkeypatch.delenv("APPLE_BRIDGE_DISABLED_APPS", raising=False)
    yield tmp_path
