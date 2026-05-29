from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from bleak.exc import BleakError
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.yongnuo_yn360.const import (
    CONF_PERSISTENT_CONNECTION,
    DOMAIN,
)

ADDRESS = "AA:BB:CC:DD:EE:FF"


async def _setup(hass, options: dict | None = None) -> str:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={},
        options=options or {},
        title="YN360III_Pro",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ids = hass.states.async_entity_ids("light")
    assert ids, "no light entity was created"
    return ids[0]


@contextmanager
def _patched_device(device: AsyncMock | None = None):
    """Patch YN360Light, the BLE lookup, and report the device as present."""
    device = device or AsyncMock()
    with patch(
        "custom_components.yongnuo_yn360.light.YN360Light", return_value=device
    ), patch(
        "custom_components.yongnuo_yn360.light.bluetooth.async_ble_device_from_address",
        return_value=object(),
    ), patch(
        "custom_components.yongnuo_yn360.light.bluetooth.async_address_present",
        return_value=True,
    ):
        yield device


async def test_turn_on_rgb_calls_set_rgb(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "rgb_color": [255, 153, 0]},
            blocking=True,
        )
    device.set_rgb.assert_awaited_once()
    assert device.set_rgb.await_args.args[:3] == (255, 153, 0)
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["rgb_color"] == (255, 153, 0)


async def test_turn_on_color_temp_calls_set_white(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "color_temp_kelvin": 4500},
            blocking=True,
        )
    device.set_white.assert_awaited_once()
    assert device.set_white.await_args.args[0] == 4500


async def test_turn_off_calls_turn_off(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    device.turn_off.assert_awaited_once()
    assert hass.states.get(entity_id).state == "off"


async def test_default_disconnects_after_command(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    device.disconnect.assert_awaited()


async def test_persistent_connection_keeps_link_open(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_PERSISTENT_CONNECTION: True})
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    device.disconnect.assert_not_awaited()


async def test_command_retries_on_transient_error(hass):
    device = AsyncMock()
    device.set_rgb.side_effect = [BleakError("boom"), BleakError("boom"), None]
    with _patched_device(device), patch(
        "custom_components.yongnuo_yn360.light.asyncio.sleep", AsyncMock()
    ):
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "rgb_color": [10, 20, 30]},
            blocking=True,
        )
    assert device.set_rgb.await_count == 3
    assert hass.states.get(entity_id).state == "on"


async def test_command_gives_up_after_max_attempts(hass):
    device = AsyncMock()
    device.set_rgb.side_effect = BleakError("nope")
    with _patched_device(device), patch(
        "custom_components.yongnuo_yn360.light.asyncio.sleep", AsyncMock()
    ):
        entity_id = await _setup(hass)
        try:
            await hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": entity_id, "rgb_color": [10, 20, 30]},
                blocking=True,
            )
        except Exception:  # noqa: BLE001 - HomeAssistantError surfaces here
            pass
    assert device.set_rgb.await_count == 4


async def test_transition_steps_brightness(hass):
    with _patched_device() as device, patch(
        "custom_components.yongnuo_yn360.light.asyncio.sleep", AsyncMock()
    ):
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "brightness": 200, "transition": 1},
            blocking=True,
        )
    assert device.set_rgb.await_count > 1
    assert hass.states.get(entity_id).state == "on"
    assert hass.states.get(entity_id).attributes["brightness"] == 200


async def test_custom_kelvin_range_from_options(hass):
    with _patched_device():
        entity_id = await _setup(hass, {"min_kelvin": 2700, "max_kelvin": 6500})
        state = hass.states.get(entity_id)
    assert state.attributes["min_color_temp_kelvin"] == 2700
    assert state.attributes["max_color_temp_kelvin"] == 6500


async def test_restores_last_state(hass):
    mock_restore_cache(
        hass,
        (
            State(
                "light.yn360iii_pro",
                "on",
                {
                    "brightness": 120,
                    "rgb_color": (12, 34, 56),
                    "color_mode": "rgb",
                },
            ),
        ),
    )
    with _patched_device() as device:
        entity_id = await _setup(hass)
        state = hass.states.get(entity_id)
        assert state.state == "on"
        assert state.attributes["brightness"] == 120
        assert state.attributes["rgb_color"] == (12, 34, 56)

        # Turning on without args re-sends the restored colour/brightness.
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    device.set_rgb.assert_awaited_once()
    assert device.set_rgb.await_args.args[:3] == (12, 34, 56)
