<p align="center">
  <img src="assets/yongnuo-logo.png" alt="Yongnuo" width="420">
</p>

# Yongnuo YN360 for Home Assistant

[![Tests](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/test.yml/badge.svg)](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/test.yml)
[![Validate](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/yn360-homeassistant)](https://github.com/hudsonbrendon/yn360-homeassistant/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Auto-discovers a **Yongnuo YN360 / YN360 III Pro** LED light over Bluetooth and
exposes it as a Home Assistant `light` — on/off, brightness, RGB colour, and
white colour temperature.

The Bluetooth protocol and device control live in a separate Python library,
[**`yn360-ble`**](https://github.com/hudsonbrendon/yn360-ble)
([PyPI](https://pypi.org/project/yn360-ble/)), which this integration pulls in
automatically via `manifest.json` `requirements`.

## Features

- 🔍 **Automatic discovery** — power the light near Home Assistant and it shows up
  as a discovered device (no MAC address or YAML required).
- 💡 **On / off**
- 🔆 **Brightness** (0–100%)
- 🎨 **RGB colour**
- 🌡️ **White colour temperature** — 3200 K (warm) to 5500 K (cool), the light's
  bi-colour range.
- 📡 **Works through ESPHome Bluetooth proxies** — it uses Home Assistant's shared
  Bluetooth stack, so the light doesn't need to be near the HA host, only near a
  proxy.

## Requirements

- Home Assistant **2024.12** or newer.
- A Bluetooth adapter on the Home Assistant host **or** an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)
  within range of the light.
- A Yongnuo YN360 III Pro (other YN360 models using the same BLE protocol may
  also work).

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add the repository URL `https://github.com/hudsonbrendon/yn360-homeassistant`
   and choose the **Integration** category.
3. Search for **Yongnuo YN360** in HACS, install it, and **restart Home Assistant**.

### Manual

1. Copy `custom_components/yongnuo_yn360/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Power on the light within range of Home Assistant (or a Bluetooth proxy).
2. Home Assistant discovers it automatically — go to
   **Settings → Devices & Services** and you'll see a **Yongnuo YN360**
   *Discovered* card. Click **Configure → Submit**.
3. If it isn't auto-discovered, add it manually: **Settings → Devices & Services
   → Add Integration → Yongnuo YN360**, then pick the device from the list.

There is nothing else to configure — the light entity appears immediately.

## Usage

The integration creates a single `light` entity per device. From the entity (UI,
automations, scripts, or the `light.turn_on` / `light.turn_off` services) you can:

| Capability | Detail |
|---|---|
| Power | On / off |
| Brightness | `brightness` / `brightness_pct` |
| Colour | `rgb_color` |
| Colour temperature | `color_temp_kelvin` (3200–5500 K) |

Example automation:

```yaml
service: light.turn_on
target:
  entity_id: light.yn360iii_pro
data:
  rgb_color: [255, 153, 0]
  brightness_pct: 80
```

## How it works

This repository ships **only** the Home Assistant integration. All Bluetooth
work — connecting, building the command frames, RGB/white conversions — lives in
the [`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) Python library and
is pulled in as a dependency. The light is controlled with the 6-byte BLE command
frames documented in that library, using acknowledged writes (the YN360 III Pro
ignores write-without-response).

## Limitations

- The light has **no state feedback** over Bluetooth, so the entity is
  `assumed_state` — Home Assistant shows the last commanded state, which may drift
  if the light is changed by its physical buttons or another app.
- Bluetooth LE allows **one client at a time** — close the official Yongnuo app
  while Home Assistant is controlling the light.
- RGB and white are mutually exclusive modes; setting one switches the active mode.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Protocol/decoding changes belong in the
[`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library, not here.

## License

[MIT](LICENSE) © Hudson Brendon
