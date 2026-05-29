from types import SimpleNamespace
from unittest.mock import patch

from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yongnuo_yn360.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:FF"
SENSOR_ID = "sensor.yn360iii_pro_signal_strength"


async def _setup(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={}, title="YN360III_Pro"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_rssi_sensor_registered_and_diagnostic(hass):
    await _setup(hass)
    registry = er.async_get(hass)
    entry = registry.async_get(SENSOR_ID)
    assert entry is not None
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
    # Disabled by default → no state object until enabled.
    assert entry.disabled_by is not None


async def test_rssi_sensor_reports_value_when_enabled(hass):
    entry = await _setup(hass)
    registry = er.async_get(hass)
    registry.async_update_entity(SENSOR_ID, disabled_by=None)

    with patch(
        "custom_components.yongnuo_yn360.sensor.bluetooth.async_address_present",
        return_value=True,
    ), patch(
        "custom_components.yongnuo_yn360.sensor.bluetooth.async_last_service_info",
        return_value=SimpleNamespace(rssi=-57),
    ):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        state = hass.states.get(SENSOR_ID)

    assert state is not None
    assert state.state == "-57"
