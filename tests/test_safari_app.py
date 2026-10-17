import json
import plistlib

import pytest

from apple_bridge import runner
from apple_bridge.apps import safari

_SAMPLE_PLIST = {
    "Children": [
        {
            "Title": "BookmarksBar",
            "WebBookmarkType": "WebBookmarkTypeList",
            "Children": [
                {
                    "WebBookmarkType": "WebBookmarkTypeLeaf",
                    "URLString": "https://example.com",
                    "URIDictionary": {"title": "Example"},
                },
            ],
        },
        {
            "Title": "com.apple.ReadingList",
            "WebBookmarkType": "WebBookmarkTypeList",
            "Children": [
                {
                    "WebBookmarkType": "WebBookmarkTypeLeaf",
                    "URLString": "https://news.example.com",
                    "URIDictionary": {"title": "News"},
                    "ReadingList": {"DateAdded": "2026-01-01"},
                },
            ],
        },
    ],
}


def _write_plist(isolated_config) -> None:
    path = isolated_config / "Bookmarks.plist"
    with path.open("wb") as handle:
        plistlib.dump(_SAMPLE_PLIST, handle)


def test_list_tabs_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '[{"window": 1, "index": 1, "title": "Example", "url": "https://example.com"}]')
    result = json.loads(safari.list_tabs({}))
    assert result == [{"window": 1, "index": 1, "title": "Example", "url": "https://example.com"}]


def test_bookmarks_excludes_reading_list(isolated_config):
    _write_plist(isolated_config)
    result = json.loads(safari.bookmarks({}))
    assert result == [{"title": "Example", "url": "https://example.com", "folder": "BookmarksBar", "reading_list": False}]


def test_reading_list_only_includes_reading_list_items(isolated_config):
    _write_plist(isolated_config)
    result = json.loads(safari.reading_list({}))
    assert result == [{"title": "News", "url": "https://news.example.com", "folder": "com.apple.ReadingList", "reading_list": True}]


def test_bookmarks_raises_clear_error_when_plist_missing():
    with pytest.raises(RuntimeError, match="not found"):
        safari.bookmarks({})


def test_bookmarks_respects_limit(isolated_config):
    _write_plist(isolated_config)
    result = json.loads(safari.bookmarks({"limit": 1}))
    assert len(result) == 1


def test_open_url_requires_http_scheme():
    with pytest.raises(ValueError):
        safari.open_url({"url": "file:///etc/passwd"})


def test_open_url_passes_url(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"status": "opened", "url": "https://example.com"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = safari.open_url({"url": "https://example.com"})
    assert captured["args"] == ("https://example.com",)
    assert json.loads(result) == {"status": "opened", "url": "https://example.com"}


def test_open_url_requires_url():
    with pytest.raises(ValueError):
        safari.open_url({"url": ""})
