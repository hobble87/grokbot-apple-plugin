import json

import pytest

from apple_bridge.apps import findmy


def _cache_dir(isolated_config):
    path = isolated_config / "fmipcore"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_list_devices_parses_cache_json(isolated_config):
    cache_dir = _cache_dir(isolated_config)
    data = [{"name": "MacBook Pro", "deviceModel": "MacBookPro18,1", "batteryLevel": 0.82, "location": {"latitude": 0, "longitude": 0}}]
    (cache_dir / "Devices.data").write_text(json.dumps(data))
    result = json.loads(findmy.list_devices({}))
    assert result == [{"name": "MacBook Pro", "deviceModel": "MacBookPro18,1", "batteryLevel": 0.82, "location": {"latitude": 0, "longitude": 0}}]


def test_list_items_parses_cache_json(isolated_config):
    cache_dir = _cache_dir(isolated_config)
    data = [{"name": "Keys", "productType": {"name": "AirTag"}, "batteryStatus": "full", "location": None}]
    (cache_dir / "Items.data").write_text(json.dumps(data))
    result = json.loads(findmy.list_items({}))
    assert result == [{"name": "Keys", "productType": "AirTag", "batteryStatus": "full", "location": None}]


def test_list_devices_raises_clear_error_when_missing():
    with pytest.raises(RuntimeError, match="not found"):
        findmy.list_devices({})


def test_list_items_raises_clear_error_when_unparseable(isolated_config):
    cache_dir = _cache_dir(isolated_config)
    (cache_dir / "Items.data").write_bytes(b"\x00\x01\x02not-json-or-encrypted")
    with pytest.raises(RuntimeError, match="encrypt"):
        findmy.list_items({})


def test_list_devices_raises_error_for_unexpected_format(isolated_config):
    cache_dir = _cache_dir(isolated_config)
    (cache_dir / "Devices.data").write_text(json.dumps({"not": "a list"}))
    with pytest.raises(RuntimeError, match="unexpected format"):
        findmy.list_devices({})
