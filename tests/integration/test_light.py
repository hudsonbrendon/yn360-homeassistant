from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yongnuo_yn360.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:FF"


async def _setup(hass) -> str:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={}, title="YN360III_Pro"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ids = hass.states.async_entity_ids("light")
    assert ids, "no light entity was created"
    return ids[0]


def _patched_device():
    """Patch the light's YN360Light + BLE lookup; return the mock device."""
    device = AsyncMock()
    return patch(
        "custom_components.yongnuo_yn360.light.YN360Light", return_value=device
    ), patch(
        "custom_components.yongnuo_yn360.light.bluetooth.async_ble_device_from_address",
        return_value=object(),
    ), device


async def test_turn_on_rgb_calls_set_rgb(hass):
    p_dev, p_ble, device = _patched_device()
    with p_dev, p_ble:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "rgb_color": [255, 153, 0]},
            blocking=True,
        )
    device.set_rgb.assert_awaited_once()
    assert device.set_rgb.await_args.args[:3] == (255, 153, 0)
    assert hass.states.get(entity_id).state == "on"


async def test_turn_on_color_temp_calls_set_white(hass):
    p_dev, p_ble, device = _patched_device()
    with p_dev, p_ble:
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
    p_dev, p_ble, device = _patched_device()
    with p_dev, p_ble:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    device.turn_off.assert_awaited_once()
    assert hass.states.get(entity_id).state == "off"
