# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2026-10-25

### Fixed
- The entity was also polled by Home Assistant's default 30 s timer on top of
  its own status poll, doubling Bluetooth connections. It now polls only on the
  configured interval. Each status reply is logged at debug level.

## [0.4.0] - 2026-10-25

### Added
- **Real state from the light.** The entity polls the light's status (every
  60 s by default) and adopts it when it differs from what Home Assistant last
  sent — so changes made on the light's knobs show up. RGB isn't reported by the
  light and is kept as last commanded. The entity is no longer `assumed_state`
  (unless polling is turned off).
- Options: **group channel** (1–8; the light ignores other channels) and **status
  poll interval** (0 disables polling).

### Changed
- Turning off now sends standby (`0xEE`) instead of off (`0xA3`): it also blacks
  out RGB and is reported back as off.
- Requires `yn360-ble` 0.3.0 (status query, standby, 0–99 white scale), whose
  protocol was verified by reverse-engineering the official YONGNUO app.
- `iot_class` is now `local_polling`.

## [0.3.0] - 2026-08-20

### Changed
- **Connections now go through `bleak-retry-connector`'s `establish_connection`.**
  Previously the integration only borrowed that library's exception list while
  opening connections itself. Going through `establish_connection` adds
  connection-slot management and GATT service caching, which matter most when
  the light is reached through an ESPHome Bluetooth proxy rather than a local
  adapter.
- **Discovery also matches the advertised service UUID**, not just the device
  name, so a unit advertising an unexpected name is still discovered. The
  YN360 III Pro was confirmed to advertise `f000aa60-…` in its advertisement
  packet.
- Requires `yn360-ble` 0.2.0.

### Notes
- The device was verified to emit **no** BLE notifications — not for app-sent
  commands, and not when its physical knobs are turned. There is no state
  feedback to read, so the light stays an `assumed_state` entity. It also has
  no battery GATT service, so a battery level sensor is not possible.

## [0.2.0] - 2026-05-28

### Added
- **Connection resilience** — each BLE command is now retried with a backoff on
  transient Bluetooth errors instead of failing on the first hiccup.
- **Availability tracking** — the light is marked unavailable when it stops
  advertising and recovers automatically when it is seen again.
- **State restore** — the last commanded on/off, brightness, colour and colour
  temperature survive a Home Assistant restart.
- **Transitions** — `light.turn_on` / `light.turn_off` honour `transition` via a
  software brightness fade.
- **Options flow** — choose a persistent vs per-command Bluetooth connection and
  customise the colour-temperature range.
- **Signal-strength sensor** — a diagnostic (disabled-by-default) RSSI sensor.
- **Diagnostics** — downloadable config-entry diagnostics.

### Changed
- Default white range widened to the device's full 3200–5600 K (was 3200–5500 K).

## [0.1.0] - 2026-05-25

### Added
- Initial release: Bluetooth auto-discovery + config flow and a `light` entity
  (on/off, brightness, RGB colour, and 3200–5500 K white colour temperature) for
  the Yongnuo YN360 / YN360 III Pro, backed by the
  [`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library.
- GitHub Actions: `pytest` on every push/PR, plus `hassfest` and HACS validation.
- English, Portuguese (pt-BR, pt), and Spanish (es) translations.

[Unreleased]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hudsonbrendon/yn360-homeassistant/releases/tag/v0.1.0
