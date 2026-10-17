import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import photos


def test_list_albums_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '[{"name": "Vacation", "id": "1"}]')
    assert json.loads(photos.list_albums({})) == [{"name": "Vacation", "id": "1"}]


def test_list_albums_defaults_to_empty_list(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: "")
    assert photos.list_albums({}) == "[]"


def test_search_passes_album_keyword_dates_and_limit(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '[{"filename": "IMG_0001.jpg", "date": "2026-01-01T00:00:00.000Z", "width": 4032, "height": 3024, "favorite": true}]'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = photos.search({
        "album": "Vacation", "keyword": "beach", "start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 10,
    })
    assert captured["args"] == ("Vacation", "beach", "2026-01-01", "2026-01-31", "10")
    assert json.loads(result) == [
        {"filename": "IMG_0001.jpg", "date": "2026-01-01T00:00:00.000Z", "width": 4032, "height": 3024, "favorite": True},
    ]


def test_search_with_no_filters_passes_empty_strings(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return "[]"

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    photos.search({})
    assert captured["args"] == ("", "", "", "", "20")


def test_search_rejects_bad_limit():
    with pytest.raises(ValueError):
        photos.search({"limit": 0})
