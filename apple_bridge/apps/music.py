"""Music app: now playing/library search/playlists are read-only; transport
controls, playing a playlist, and setting the volume are writes. Driven by
JXA against Music.app."""
from __future__ import annotations

from .. import runner
from ..safety import ToolDef

_NOW_PLAYING_SCRIPT = r"""
function run(argv) {
    var Music = Application("Music");
    var state = Music.playerState();
    if (state !== "playing" && state !== "paused") {
        return JSON.stringify({state: state});
    }
    var track = Music.currentTrack();
    return JSON.stringify({state: state, name: track.name(), artist: track.artist(), album: track.album()});
}
"""

_SEARCH_SCRIPT = r"""
function run(argv) {
    var query = argv[0].toLowerCase();
    var limit = parseInt(argv[1], 10) || 20;
    var Music = Application("Music");
    var allTracks = Music.tracks();
    var out = [];
    for (var i = 0; i < allTracks.length && out.length < limit; i++) {
        var t = allTracks[i];
        var name = t.name();
        var artist = t.artist();
        var album = t.album();
        if (name.toLowerCase().indexOf(query) !== -1 || artist.toLowerCase().indexOf(query) !== -1 || album.toLowerCase().indexOf(query) !== -1) {
            out.push({name: name, artist: artist, album: album});
        }
    }
    return JSON.stringify(out);
}
"""

_PLAYLISTS_SCRIPT = r"""
function run(argv) {
    var Music = Application("Music");
    var lists = Music.playlists();
    var out = [];
    for (var i = 0; i < lists.length; i++) {
        out.push(lists[i].name());
    }
    return JSON.stringify(out);
}
"""

_PLAY_SCRIPT = r"""
function run(argv) {
    Application("Music").play();
    return JSON.stringify({status: "playing"});
}
"""

_PAUSE_SCRIPT = r"""
function run(argv) {
    Application("Music").pause();
    return JSON.stringify({status: "paused"});
}
"""

_NEXT_SCRIPT = r"""
function run(argv) {
    Application("Music").nextTrack();
    return JSON.stringify({status: "skipped"});
}
"""

_PREVIOUS_SCRIPT = r"""
function run(argv) {
    Application("Music").previousTrack();
    return JSON.stringify({status: "skipped"});
}
"""

_PLAY_PLAYLIST_SCRIPT = r"""
function run(argv) {
    var name = argv[0];
    var Music = Application("Music");
    var matches = Music.playlists.whose({name: name})();
    if (matches.length === 0) {
        throw new Error("playlist not found: " + name);
    }
    matches[0].play();
    return JSON.stringify({status: "playing", playlist: name});
}
"""

_SET_VOLUME_SCRIPT = r"""
function run(argv) {
    var level = parseInt(argv[0], 10);
    Application("Music").soundVolume = level;
    return JSON.stringify({volume: level});
}
"""


def _text(args: dict, field: str, required: bool = False, max_len: int = 200) -> str:
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


def now_playing(_args: dict) -> str:
    return runner.run_jxa(_NOW_PLAYING_SCRIPT).strip()


def search(args: dict) -> str:
    query = _text(args, "query", required=True)
    output = runner.run_jxa(_SEARCH_SCRIPT, query, str(_limit(args)))
    return output.strip() or "[]"


def playlists(_args: dict) -> str:
    output = runner.run_jxa(_PLAYLISTS_SCRIPT)
    return output.strip() or "[]"


def play(_args: dict) -> str:
    return runner.run_jxa(_PLAY_SCRIPT).strip()


def pause(_args: dict) -> str:
    return runner.run_jxa(_PAUSE_SCRIPT).strip()


def next_track(_args: dict) -> str:
    return runner.run_jxa(_NEXT_SCRIPT).strip()


def previous_track(_args: dict) -> str:
    return runner.run_jxa(_PREVIOUS_SCRIPT).strip()


def play_playlist(args: dict) -> str:
    name = _text(args, "name", required=True)
    return runner.run_jxa(_PLAY_PLAYLIST_SCRIPT, name).strip()


def set_volume(args: dict) -> str:
    level = int(args.get("level", -1))
    if not 0 <= level <= 100:
        raise ValueError("level must be between 0 and 100")
    return runner.run_jxa(_SET_VOLUME_SCRIPT, str(level)).strip()


LIMIT_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
TOOLS = [
    ToolDef(
        name="music.now_playing",
        description="Get the current Music.app player state and track info.",
        schema={},
        handler=now_playing,
        kind="read",
    ),
    ToolDef(
        name="music.search",
        description="Search the Music library by track/artist/album name.",
        schema={"query": {"type": "string"}, "limit": LIMIT_SCHEMA},
        handler=search,
        kind="read",
        required=["query"],
    ),
    ToolDef(
        name="music.playlists",
        description="List playlist names in Music.app.",
        schema={},
        handler=playlists,
        kind="read",
    ),
    ToolDef(
        name="music.play",
        description="Resume Music.app playback.",
        schema={},
        handler=play,
        kind="write",
    ),
    ToolDef(
        name="music.pause",
        description="Pause Music.app playback.",
        schema={},
        handler=pause,
        kind="write",
    ),
    ToolDef(
        name="music.next",
        description="Skip to the next track.",
        schema={},
        handler=next_track,
        kind="write",
    ),
    ToolDef(
        name="music.previous",
        description="Skip to the previous track.",
        schema={},
        handler=previous_track,
        kind="write",
    ),
    ToolDef(
        name="music.play_playlist",
        description="Play a playlist by name.",
        schema={"name": {"type": "string"}},
        handler=play_playlist,
        kind="write",
        required=["name"],
    ),
    ToolDef(
        name="music.set_volume",
        description="Set the Music.app sound volume (0-100).",
        schema={"level": {"type": "integer", "minimum": 0, "maximum": 100}},
        handler=set_volume,
        kind="write",
        required=["level"],
    ),
]


def tools() -> list[ToolDef]:
    return TOOLS
