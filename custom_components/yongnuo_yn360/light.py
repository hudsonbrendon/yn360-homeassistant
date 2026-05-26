"""Light platform for Yongnuo YN360."""

from __future__ import annotations

from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from yn360 import YN360Light

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yongnuo YN360 light from a config entry."""
    async_add_entities([YN360LightEntity(entry.unique_id, entry.title)])


class YN360LightEntity(LightEntity):
    """A Yongnuo YN360 RGB / bi-colour BLE light.

    The light has no state feedback over BLE, so it is an ``assumed_state``
    entity. Each command opens a short-lived connection (Home Assistant manages
    the shared Bluetooth stack, so this also works through ESPHome BT proxies)
    and disconnects afterwards.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = 3200
    _attr_max_color_temp_kelvin = 5500

    def __init__(self, address: str, title: str) -> None:
        self._address = address
        self._attr_unique_id = address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={("bluetooth", address)},
            name=title,
            manufacturer="Yongnuo",
            model="YN360 III Pro",
        )
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_color_temp_kelvin = 4350
        self._attr_color_mode = ColorMode.RGB

    def _make_device(self) -> YN360Light:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )
        if ble_device is None:
            raise HomeAssistantError(f"YN360 {self._address} is not in range")
        return YN360Light(ble_device)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on, optionally setting colour, colour temperature, or brightness."""
        device = self._make_device()
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)
        ratio = brightness / 255
        try:
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
                await device.set_white(kelvin, ratio)
                self._attr_color_mode = ColorMode.COLOR_TEMP
                self._attr_color_temp_kelvin = kelvin
            elif ATTR_RGB_COLOR in kwargs:
                rgb = kwargs[ATTR_RGB_COLOR]
                await device.set_rgb(*rgb, brightness=ratio)
                self._attr_color_mode = ColorMode.RGB
                self._attr_rgb_color = rgb
            elif self._attr_color_mode == ColorMode.COLOR_TEMP:
                await device.set_white(self._attr_color_temp_kelvin, ratio)
            else:
                await device.set_rgb(*self._attr_rgb_color, brightness=ratio)
        finally:
            await device.disconnect()
        self._attr_brightness = brightness
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        device = self._make_device()
        try:
            await device.turn_off()
        finally:
            await device.disconnect()
        self._attr_is_on = False
        self.async_write_ha_state()
