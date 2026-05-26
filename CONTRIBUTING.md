# Contributing

Thanks for helping improve the Yongnuo YN360 Home Assistant integration!

## Development setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest
```

Requires Python 3.12+. This repo ships only the Home Assistant integration
(`custom_components/yongnuo_yn360`); the BLE protocol lives in the
[`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library (PyPI), pulled
in via `manifest.json` `requirements`.

## Guidelines

- Keep `pytest` green and add tests for new behaviour. Integration tests use
  `pytest-homeassistant-custom-component`; the bluetooth stack is mocked in
  `tests/integration/conftest.py`.
- Protocol/decoding changes belong in the `yn360-ble` library, not here.
- The light is write-only over BLE (no state feedback); the entity is
  `assumed_state` by design.

## Releasing

1. Bump `version` in `custom_components/yongnuo_yn360/manifest.json` and update
   `CHANGELOG.md`.
2. Tag and push: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.
3. Create a GitHub release for the tag — HACS offers it as an update.
