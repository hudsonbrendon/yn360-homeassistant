# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
