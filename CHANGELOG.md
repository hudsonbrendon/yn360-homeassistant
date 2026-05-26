# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-25

### Added
- Initial release: Bluetooth auto-discovery + config flow and a `light` entity
  (on/off, brightness, RGB colour, and 3200–5500 K white colour temperature) for
  the Yongnuo YN360 / YN360 III Pro, backed by the
  [`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library.
- GitHub Actions: `pytest` on every push/PR, plus `hassfest` and HACS validation.
- English, Portuguese (pt-BR, pt), and Spanish (es) translations.

[Unreleased]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hudsonbrendon/yn360-homeassistant/releases/tag/v0.1.0
