from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from bleak.exc import BleakError
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from yn360 import WhiteState

from custom_components.yongnuo_yn360.const import (
    CONF_CHANNEL,
    CONF_PERSISTENT_CONNECTION,
    CONF_POLL_INTERVAL,
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
    """Patch YN360Light, the BLE lookup, and report the device as present.

    The status query answers None (no reply) unless the test configures it.
    """
    device = device or AsyncMock()
    if not isinstance(device.query_status.return_value, (WhiteState, type(None))):
        device.query_status.return_value = None
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


async def test_make_device_supplies_a_client_factory(hass):
    """The entity hands YN360Light a factory so connections go through
    bleak_retry_connector.establish_connection (connection-slot aware, and it
    caches GATT services -- both matter through an ESPHome Bluetooth proxy)."""
    with _patched_device():
        entity_id = await _setup(hass)
    entity = hass.data["entity_components"]["light"].get_entity(entity_id)

    captured: dict = {}

    def fake_light(device, client_factory=None):
        captured["device"] = device
        captured["factory"] = client_factory
        return AsyncMock()

    with patch(
        "custom_components.yongnuo_yn360.light.YN360Light", side_effect=fake_light
    ), patch(
        "custom_components.yongnuo_yn360.light.bluetooth.async_ble_device_from_address",
        return_value=object(),
    ):
        entity._make_device()

    assert captured["factory"] is not None


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


async def test_turn_off_uses_standby_on_configured_channel(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_CHANNEL: 3})
        await hass.services.async_call(
            "light", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    device.standby.assert_awaited_once_with(3)
    device.turn_off.assert_not_awaited()
    assert hass.states.get(entity_id).state == "off"


async def test_white_uses_configured_channel(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_CHANNEL: 2})
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "color_temp_kelvin": 4500},
            blocking=True,
        )
    assert device.set_white.await_args.kwargs["channel"] == 2


async def test_poll_adopts_knob_change(hass):
    """A status reply that differs from what was sent (knobs turned) wins."""
    device = AsyncMock()
    device.query_status.return_value = WhiteState(1, 0x51, 0x63, on=True)
    with _patched_device(device):
        entity_id = await _setup(hass)
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["color_mode"] == "color_temp"
    assert state.attributes["brightness"] == 255
    assert 4200 < state.attributes["color_temp_kelvin"] < 4300
    assert state.attributes.get("assumed_state") is None


async def test_poll_reports_standby_as_off(hass):
    mock_restore_cache(hass, (State("light.yn360iii_pro", "on", {}),))
    device = AsyncMock()
    device.query_status.return_value = WhiteState(1, 50, 50, on=False)
    with _patched_device(device):
        entity_id = await _setup(hass)
    assert hass.states.get(entity_id).state == "off"


async def test_poll_matching_last_command_keeps_rgb(hass):
    """RGB is never reported, so a reply equal to the last white frame sent
    must not flip an RGB light back to white."""
    device = AsyncMock()
    with _patched_device(device):
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "color_temp_kelvin": 5500, "brightness": 255},
            blocking=True,
        )
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "rgb_color": [255, 0, 0]},
            blocking=True,
        )
        device.query_status.return_value = WhiteState(1, 99, 0, on=True)
        entity = hass.data["entity_components"]["light"].get_entity(entity_id)
        await entity._async_poll()
        device.query_status.assert_awaited()
    state = hass.states.get(entity_id)
    assert state.attributes["color_mode"] == "rgb"
    assert state.attributes["rgb_color"] == (255, 0, 0)


async def test_polling_disabled_is_assumed_state(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_POLL_INTERVAL: 0})
    device.query_status.assert_not_awaited()
    assert hass.states.get(entity_id).attributes["assumed_state"] is True


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
