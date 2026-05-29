from types import SimpleNamespace
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yongnuo_yn360.const import CONF_MIN_KELVIN, DOMAIN
from custom_components.yongnuo_yn360.diagnostics import (
    async_get_config_entry_diagnostics,
)

ADDRESS = "AA:BB:CC:DD:EE:FF"


async def test_diagnostics_payload(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={},
        options={CONF_MIN_KELVIN: 2700},
        title="YN360III_Pro",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "custom_components.yongnuo_yn360.diagnostics.bluetooth.async_address_present",
        return_value=True,
    ), patch(
        "custom_components.yongnuo_yn360.diagnostics.bluetooth.async_last_service_info",
        return_value=SimpleNamespace(
            rssi=-61,
            name="YN360III_Pro",
            source="local",
            service_uuids=["abcd"],
        ),
    ):
        data = await async_get_config_entry_diagnostics(hass, entry)

    assert data["entry"]["title"] == "YN360III_Pro"
    assert data["entry"]["options"] == {CONF_MIN_KELVIN: 2700}
    assert data["bluetooth"]["present"] is True
    assert data["bluetooth"]["rssi"] == -61
    assert data["bluetooth"]["service_uuids"] == ["abcd"]
