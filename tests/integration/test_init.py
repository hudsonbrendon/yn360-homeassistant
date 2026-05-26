from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yongnuo_yn360.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:FF"


async def test_setup_and_unload_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={}, title="YN360III_Pro"
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
