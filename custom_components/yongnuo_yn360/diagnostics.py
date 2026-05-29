"""Diagnostics support for Yongnuo YN360."""

from __future__ import annotations

from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    address = entry.unique_id
    info = (
        bluetooth.async_last_service_info(hass, address, connectable=True)
        if address
        else None
    )

    return {
        "entry": {
            "title": entry.title,
            "options": dict(entry.options),
            "source": entry.source,
        },
        "bluetooth": {
            "present": bool(address)
            and bluetooth.async_address_present(hass, address, connectable=True),
            "rssi": info.rssi if info else None,
            "name": info.name if info else None,
            "source": info.source if info else None,
            "service_uuids": list(info.service_uuids) if info else None,
        },
    }
