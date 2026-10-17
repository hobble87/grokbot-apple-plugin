import json

import pytest

from apple_bridge import runner
from apple_bridge.apps import music


def test_now_playing_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '{"state": "playing", "name": "Song"}')
    assert json.loads(music.now_playing({})) == {"state": "playing", "name": "Song"}


def test_search_passes_query_and_limit(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '[{"name": "Song", "artist": "Artist", "album": "Album"}]'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = music.search({"query": "Song", "limit": 5})
    assert captured["args"] == ("Song", "5")
    assert json.loads(result) == [{"name": "Song", "artist": "Artist", "album": "Album"}]


def test_search_requires_query():
    with pytest.raises(ValueError):
        music.search({"query": ""})


def test_playlists_returns_jxa_output(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '["Chill", "Workout"]')
    assert json.loads(music.playlists({})) == ["Chill", "Workout"]


def test_play_pause_next_previous(monkeypatch):
    monkeypatch.setattr(runner, "run_jxa", lambda script, *a, **k: '{"status": "ok"}')
    assert json.loads(music.play({})) == {"status": "ok"}
    assert json.loads(music.pause({})) == {"status": "ok"}
    assert json.loads(music.next_track({})) == {"status": "ok"}
    assert json.loads(music.previous_track({})) == {"status": "ok"}


def test_play_playlist_passes_name(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"status": "playing", "playlist": "Chill"}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = music.play_playlist({"name": "Chill"})
    assert captured["args"] == ("Chill",)
    assert json.loads(result) == {"status": "playing", "playlist": "Chill"}


def test_play_playlist_requires_name():
    with pytest.raises(ValueError):
        music.play_playlist({"name": ""})


def test_set_volume_passes_level(monkeypatch):
    captured = {}

    def fake_run_jxa(script, *args, timeout=runner.DEFAULT_TIMEOUT):
        captured["args"] = args
        return '{"volume": 42}'

    monkeypatch.setattr(runner, "run_jxa", fake_run_jxa)
    result = music.set_volume({"level": 42})
    assert captured["args"] == ("42",)
    assert json.loads(result) == {"volume": 42}


def test_set_volume_rejects_out_of_range():
    with pytest.raises(ValueError):
        music.set_volume({"level": 101})
