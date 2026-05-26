import json
from pathlib import Path


def test_manifest_is_valid():
    path = Path("custom_components/yongnuo_yn360/manifest.json")
    data = json.loads(path.read_text())
    assert data["domain"] == "yongnuo_yn360"
    assert data["config_flow"] is True
    assert data["iot_class"] == "assumed_state"
    assert "bluetooth_adapters" in data["dependencies"]
    assert data["bluetooth"] == [{"local_name": "YN360*"}]
    assert any(r.startswith("yn360-ble") for r in data["requirements"])
