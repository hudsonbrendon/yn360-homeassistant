# YN360 Integration & Library Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-channel white control, standby command, and physical-knob state feedback to the yn360-ble library, and make the Home Assistant integration's BLE connections robust via `bleak-retry-connector`'s `establish_connection`.

**Architecture:** Protocol additions land in the pure `protocol.py` (no I/O), get exposed through `YN360Light`, then the HA integration consumes them. The integration also starts injecting connections built by `establish_connection` (connection-slot management for ESPHome proxies, cached services) instead of raw `BleakClient.connect()`. Hardware-uncertain features are gated behind a scripted validation phase.

**Tech Stack:** Python 3.13, bleak, bleak-retry-connector, pytest, pytest-homeassistant-custom-component. Two repos: `~/Github/yn360-ble` (library) and `~/Github/yn360-homeassistant` (integration).

**Spec:** The "Research Findings" section below is the spec — findings were validated live against the physical YN360 III Pro on 2026-08-20.

## Research Findings (spec)

Validated live on 2026-08-20 against the physical light near this Mac (macOS address `6AF33AAF-16F6-93C7-D939-EECC8680C454`, advertised name `YN360III_Pro`, RSSI −67):

1. **Advertisement**: the light DOES advertise service UUID `f000aa60-0451-4000-b000-000000000000` (previously unconfirmed in HARDWARE.md). Config-flow service-UUID matching works.
2. **GATT**: single service `f000aa60`, exactly two characteristics — write `f000aa61` (`write`, `write-without-response`) and notify `f000aa63` (`notify`). No battery service. MTU 23.
3. **Notify is silent for app-sent commands**: subscribed to `f000aa63` and sent white/RGB/off/0xEE frames — zero notifications. Prior art (pinchies/YN360_webbtle README errata) says the wand "only reports back when changing white tones", i.e. notifications likely fire when the **physical knobs** are turned. Needs the user-assisted test in Task 0.
4. **Channel byte** (from pinchies/YN360_webbtle, YN360-II): the white frame is `[0xAE, 0xAA, channel, cool, warm, 0x56]` with channels 1–8 — the current lib hardcodes `0x01`. The III Pro accepted channel `0x01`; channels 2–8 need the user-assisted test in Task 0.
5. **0xEE opcode** (from pinchies/YN360_webbtle): `[0xAE, 0xEE, ch, cool, warm, 0x56]` is used as an "off that keeps the current values" (standby). Semantics on the III Pro need the user-assisted test in Task 0.
6. **Acknowledged writes required** (already known, re-confirmed): `response=True` only.
7. **HA live state**: entity `YN360III_Pro` exists in area Escritório, integration functioning.
8. **Integration gap**: `manifest.json` requires `bleak-retry-connector` but the code only imports its exception list; connections are raw `BleakClient.connect()` — no connection-slot management (matters through ESPHome BT proxies), no service cache.

**Prior art sources:** [pinchies/YN360_webbtle](https://github.com/pinchies/YN360_webbtle), [kenkeiter/lantern](https://github.com/kenkeiter/lantern), [singularity0821/yongnuo-yn360-home-assistant](https://github.com/singularity0821/yongnuo-yn360-home-assistant), [samuelpinches.com.au write-up](https://samuelpinches.com.au/hacking/yongnuo-yn360-bluetooth-pc-mac-webble-control/) (site was unreachable on 2026-08-20).

**Deferred (decided against for now):** light effects (`LightEntityFeature.EFFECT` — no native effects on device, software emulation is BLE-chatty), battery sensor (no battery GATT service exists), replacing the software transition (device has no native fade).

## Global Constraints

- Library repo: `/Users/hudsonbrendon/Github/yn360-ble`, package `yn360`, `src/` layout, current version `0.1.0` → this plan releases `0.2.0`.
- Integration repo: `/Users/hudsonbrendon/Github/yn360-homeassistant`, domain `yongnuo_yn360`, current version `0.2.0` → this plan releases `0.3.0`.
- Integration manifest pin after release: `yn360-ble==0.2.0`.
- All BLE writes stay `response=True` (hardware drops unacknowledged writes).
- `protocol.py` stays pure — no I/O, no bleak imports.
- Library test command: `cd ~/Github/yn360-ble && python -m pytest tests/ -v` (use its venv if present).
- Integration test command: `cd ~/Github/yn360-homeassistant && .venv/bin/python -m pytest tests/integration -v`.
- Commits follow conventional commits (`feat:`, `fix:`, `test:`, `chore:`).
- Tasks 6 and 7 are **conditional** on Task 0 results; skip them (and say so) if the hardware test fails.

---

### Task 0: Hardware validation (user-assisted, ~10 minutes at the light)

**Files:**
- Create: `/Users/hudsonbrendon/Github/yn360-ble/scripts/probe_knobs.py`
- Create: `/Users/hudsonbrendon/Github/yn360-ble/scripts/probe_channels.py`
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/HARDWARE.md` (append results)

**Interfaces:**
- Produces: three recorded YES/NO facts in `HARDWARE.md` under a `## 2026-08-20 validation` heading: `KNOB_NOTIFY` (does turning physical knobs emit notify frames, and their hex), `CHANNELS_2_TO_8` (does the III Pro react to white frames on channel ≠ 1), `STANDBY_0xEE` (what 0xEE visibly does vs 0xA3). Tasks 6/7 read these.

This task needs the user physically at the light (turn knobs, watch it). It cannot run unattended — coordinate with the user before running.

- [ ] **Step 1: Write the knob-listening probe**

```python
"""Listen to the notify characteristic while the user turns the physical knobs."""
import asyncio
from bleak import BleakClient, BleakScanner

ADDR = "6AF33AAF-16F6-93C7-D939-EECC8680C454"  # macOS UUID for this Mac
NOTIFY = "f000aa63-0451-4000-b000-000000000000"

async def main() -> None:
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=10)
    if not dev:
        print("Light not found — is it on and in range?")
        return
    async with BleakClient(dev) as client:
        frames: list[str] = []

        def cb(_sender, data: bytearray) -> None:
            print("NOTIFY:", data.hex())
            frames.append(data.hex())

        await client.start_notify(NOTIFY, cb)
        print("Listening 45s — turn the physical knobs (white tone AND rgb) now...")
        await asyncio.sleep(45)
        print(f"Done. {len(frames)} frame(s) captured.")

asyncio.run(main())
```

- [ ] **Step 2: Run it with the user turning knobs**

Run: `~/Github/yn360-homeassistant/.venv/bin/python scripts/probe_knobs.py` (that venv has bleak)
Expected: either hex frames printed (record them verbatim) or 0 frames. Both are valid results.

- [ ] **Step 3: Write the channel/standby probe**

```python
"""Send white frames on channels 2 and 3, then 0xEE, with pauses for the user to observe."""
import asyncio
from bleak import BleakClient, BleakScanner

ADDR = "6AF33AAF-16F6-93C7-D939-EECC8680C454"
WRITE = "f000aa61-0451-4000-b000-000000000000"

async def main() -> None:
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=10)
    if not dev:
        print("Light not found")
        return
    async with BleakClient(dev) as client:
        async def send(label: str, frame: bytes) -> None:
            print(f"\n>>> {label}: {frame.hex()} — WATCH THE LIGHT")
            await client.write_gatt_char(WRITE, frame, response=True)
            await asyncio.sleep(4)

        await send("white ch1 50/50 (baseline, should light up)", bytes([0xAE, 0xAA, 1, 50, 50, 0x56]))
        await send("white ch2 50/50 (does it react?)", bytes([0xAE, 0xAA, 2, 50, 50, 0x56]))
        await send("white ch3 100/0 (does it react?)", bytes([0xAE, 0xAA, 3, 100, 0, 0x56]))
        await send("white ch1 50/50 (back to baseline)", bytes([0xAE, 0xAA, 1, 50, 50, 0x56]))
        await send("standby 0xEE ch1 50/50 (does it turn off? dim?)", bytes([0xAE, 0xEE, 1, 50, 50, 0x56]))
        await send("white ch1 50/50 (does it come back?)", bytes([0xAE, 0xAA, 1, 50, 50, 0x56]))
        await send("off 0xA3 (restore off)", bytes([0xAE, 0xA3, 0, 0, 0, 0x56]))

asyncio.run(main())
```

- [ ] **Step 4: Run it with the user watching the light**

Run: `~/Github/yn360-homeassistant/.venv/bin/python scripts/probe_channels.py`
Expected: user narrates what the light does at each step. Record answers.

- [ ] **Step 5: Append results to HARDWARE.md and commit**

Append a `## 2026-08-20 validation` section recording `KNOB_NOTIFY: YES/NO (+frames)`, `CHANNELS_2_TO_8: YES/NO`, `STANDBY_0xEE: <observed behavior>`, plus the newly confirmed fact that the service UUID IS advertised.

```bash
git -C ~/Github/yn360-ble add scripts/ HARDWARE.md
git -C ~/Github/yn360-ble commit -m "docs: record knob-notify, channel, and 0xEE hardware validation"
```

---

### Task 1: Protocol additions (library, pure functions)

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/src/yn360/protocol.py`
- Test: `/Users/hudsonbrendon/Github/yn360-ble/tests/test_protocol.py`

**Interfaces:**
- Consumes: existing `HEADER`, `FOOTER`, `CMD_WHITE`, `WHITE_CHANNEL`, `_require_range`, `WHITE_MIN_KELVIN`, `WHITE_MAX_KELVIN`.
- Produces (Task 2 and Task 6 rely on these exact signatures):
  - `build_white_command(cool: int, warm: int, channel: int = 1) -> bytes` (channel param added, default keeps old behavior)
  - `build_standby_command(cool: int, warm: int, channel: int = 1) -> bytes` (new, opcode `0xEE`)
  - `WhiteState` — `NamedTuple` with fields `channel: int, cool: int, warm: int`
  - `parse_white_notification(data: bytes) -> WhiteState | None`
  - `cool_warm_to_kelvin(cool: int, warm: int) -> tuple[int, float] | None` — inverse of `kelvin_to_cool_warm`; `None` when both are 0 (off)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_protocol.py`)

```python
from yn360.protocol import (
    WhiteState,
    build_standby_command,
    cool_warm_to_kelvin,
    parse_white_notification,
)


def test_build_white_command_channel():
    assert build_white_command(100, 0, channel=3) == b"\xae\xaa\x03\x64\x00\x56"


def test_build_white_command_rejects_bad_channel():
    with pytest.raises(ValueError):
        build_white_command(50, 50, channel=0)
    with pytest.raises(ValueError):
        build_white_command(50, 50, channel=9)


def test_build_standby_command():
    assert build_standby_command(50, 50) == b"\xae\xee\x01\x32\x32\x56"


def test_parse_white_notification_roundtrip():
    assert parse_white_notification(b"\xae\xaa\x01\x32\x32\x56") == WhiteState(1, 50, 50)


def test_parse_white_notification_rejects_garbage():
    assert parse_white_notification(b"") is None
    assert parse_white_notification(b"\xae\xa1\x0a\x00\x00\x56") is None  # rgb frame
    assert parse_white_notification(b"\xae\xaa\x01\xff\x32\x56") is None  # cool > 100


def test_cool_warm_to_kelvin_inverts_kelvin_to_cool_warm():
    for kelvin, brightness in [(3200, 1.0), (5500, 1.0), (4350, 1.0), (5500, 0.5)]:
        cool, warm = kelvin_to_cool_warm(kelvin, brightness)
        result = cool_warm_to_kelvin(cool, warm)
        assert result is not None
        got_kelvin, got_brightness = result
        assert abs(got_kelvin - kelvin) <= 25
        assert abs(got_brightness - brightness) <= 0.02


def test_cool_warm_to_kelvin_zero_is_none():
    assert cool_warm_to_kelvin(0, 0) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/test_protocol.py -v`
Expected: FAIL with `ImportError` on the new names.

- [ ] **Step 3: Implement in `protocol.py`**

```python
from typing import NamedTuple

CMD_STANDBY = 0xEE  # near CMD_OFF


class WhiteState(NamedTuple):
    """A white-mode state as carried in a 0xAA frame."""

    channel: int
    cool: int
    warm: int


def build_white_command(cool: int, warm: int, channel: int = WHITE_CHANNEL) -> bytes:
    """Frame for white mode: [0xAE, 0xAA, channel, cool, warm, 0x56].

    cool/warm 0-100; channel 1-8 (YN360-II supports 8 group channels; the
    III Pro is confirmed on channel 1 — see HARDWARE.md).
    """
    _require_range("channel", channel, 1, 8)
    _require_range("cool", cool, 0, 100)
    _require_range("warm", warm, 0, 100)
    return bytes([HEADER, CMD_WHITE, channel, cool, warm, FOOTER])


def build_standby_command(cool: int, warm: int, channel: int = WHITE_CHANNEL) -> bytes:
    """Frame for standby-off: [0xAE, 0xEE, channel, cool, warm, 0x56].

    Observed in pinchies/YN360_webbtle as an off that keeps the current
    values loaded. See HARDWARE.md for III Pro behavior.
    """
    _require_range("channel", channel, 1, 8)
    _require_range("cool", cool, 0, 100)
    _require_range("warm", warm, 0, 100)
    return bytes([HEADER, CMD_STANDBY, channel, cool, warm, FOOTER])


def parse_white_notification(data: bytes) -> WhiteState | None:
    """Parse a 6-byte notify frame into a WhiteState, or None if not one."""
    if len(data) != 6 or data[0] != HEADER or data[5] != FOOTER:
        return None
    if data[1] != CMD_WHITE:
        return None
    channel, cool, warm = data[2], data[3], data[4]
    if not (0 <= cool <= 100 and 0 <= warm <= 100):
        return None
    return WhiteState(channel, cool, warm)


def cool_warm_to_kelvin(cool: int, warm: int) -> tuple[int, float] | None:
    """Inverse of kelvin_to_cool_warm: (cool, warm) -> (kelvin, brightness).

    Returns None when both channels are 0 (light off).
    """
    _require_range("cool", cool, 0, 100)
    _require_range("warm", warm, 0, 100)
    total = cool + warm
    if total == 0:
        return None
    percent_cool = cool / total
    kelvin = round(WHITE_MIN_KELVIN + percent_cool * (WHITE_MAX_KELVIN - WHITE_MIN_KELVIN))
    brightness = min(1.0, total / 100)
    return kelvin, brightness
```

Note: the existing `WHITE_CHANNEL = 0x01` constant stays and becomes the channel default.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/test_protocol.py -v`
Expected: all PASS (existing tests too — `build_white_command(100, 0)` still yields channel `0x01`).

- [ ] **Step 5: Commit**

```bash
git -C ~/Github/yn360-ble add src/yn360/protocol.py tests/test_protocol.py
git -C ~/Github/yn360-ble commit -m "feat: channel-aware white frames, 0xEE standby, notify parsing, kelvin inverse"
```

---

### Task 2: YN360Light additions (library, I/O layer)

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/src/yn360/light.py`
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/src/yn360/__init__.py` (export `WhiteState`, `cool_warm_to_kelvin`)
- Test: `/Users/hudsonbrendon/Github/yn360-ble/tests/test_light.py`

**Interfaces:**
- Consumes: Task 1's `build_white_command(cool, warm, channel)`, `parse_white_notification`, `WhiteState`; `NOTIFY_CHAR_UUID` from `const.py`.
- Produces (Tasks 5 and 6 rely on these exact signatures):
  - `YN360Light.__init__(self, device: BLEDevice | str, client_factory: Callable[[], Awaitable[BleakClient]] | None = None)`
  - `YN360Light.set_white(self, kelvin: int, brightness: float = 1.0, channel: int = 1) -> None` (async)
  - `YN360Light.start_notify(self, callback: Callable[[WhiteState], None]) -> None` (async)
  - `YN360Light.stop_notify(self) -> None` (async)

- [ ] **Step 1: Read the existing `tests/test_light.py` mock style, then write failing tests in that style**

The existing tests patch `yn360.light.BleakClient`. Add:

```python
import pytest
from unittest.mock import AsyncMock, patch

from yn360.light import YN360Light
from yn360.protocol import WhiteState


@pytest.mark.asyncio
async def test_set_white_passes_channel():
    with patch("yn360.light.BleakClient") as client_cls:
        client = client_cls.return_value
        client.is_connected = False
        client.connect = AsyncMock()
        client.write_gatt_char = AsyncMock()
        light = YN360Light("AA:BB")
        await light.set_white(5500, 1.0, channel=3)
        payload = client.write_gatt_char.await_args.args[1]
        assert payload[2] == 3


@pytest.mark.asyncio
async def test_client_factory_used_for_connection():
    factory_client = AsyncMock()
    factory_client.is_connected = True

    async def factory():
        return factory_client

    with patch("yn360.light.BleakClient") as client_cls:
        client_cls.return_value.is_connected = False
        light = YN360Light("AA:BB", client_factory=factory)
        await light.connect()
        assert light._client is factory_client


@pytest.mark.asyncio
async def test_start_notify_filters_and_parses():
    with patch("yn360.light.BleakClient") as client_cls:
        client = client_cls.return_value
        client.is_connected = True
        client.start_notify = AsyncMock()
        light = YN360Light("AA:BB")
        seen: list[WhiteState] = []
        await light.start_notify(seen.append)
        raw_cb = client.start_notify.await_args.args[1]
        raw_cb(None, bytearray(b"\xae\xaa\x01\x32\x32\x56"))  # white frame
        raw_cb(None, bytearray(b"\xff\xff"))  # garbage
        assert seen == [WhiteState(1, 50, 50)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/test_light.py -v`
Expected: FAIL (`TypeError: unexpected keyword argument` / `AttributeError: start_notify`).

- [ ] **Step 3: Implement in `light.py`**

```python
from collections.abc import Awaitable, Callable

from .const import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID
from .protocol import (
    WhiteState,
    build_off_command,
    build_rgb_command,
    build_white_command,
    kelvin_to_cool_warm,
    parse_white_notification,
    scale_rgb,
)


class YN360Light:
    def __init__(
        self,
        device: BLEDevice | str,
        client_factory: Callable[[], Awaitable[BleakClient]] | None = None,
    ) -> None:
        self._device = device
        self._client_factory = client_factory
        self._client = BleakClient(device)
        self._is_on = False
        self._rgb: tuple[int, int, int] = (255, 255, 255)
        self._brightness = 1.0

    async def connect(self) -> None:
        if self._client.is_connected:
            return
        _LOGGER.debug("Connecting to YN360 %s", self._device)
        if self._client_factory is not None:
            # The factory (e.g. bleak-retry-connector's establish_connection)
            # returns an already-connected client.
            self._client = await self._client_factory()
        else:
            await self._client.connect()

    async def set_white(
        self, kelvin: int, brightness: float = 1.0, channel: int = 1
    ) -> None:
        cool, warm = kelvin_to_cool_warm(kelvin, brightness)
        await self._write(build_white_command(cool, warm, channel))
        self._brightness = brightness
        self._is_on = True

    async def start_notify(self, callback: Callable[[WhiteState], None]) -> None:
        """Subscribe to device notifications, delivering parsed white states.

        The YN360 III Pro does not echo app-sent commands; frames arrive when
        the physical knobs are turned (see HARDWARE.md).
        """
        await self.connect()

        def _on_notify(_sender: object, data: bytearray) -> None:
            state = parse_white_notification(bytes(data))
            if state is not None:
                callback(state)

        await self._client.start_notify(NOTIFY_CHAR_UUID, _on_notify)

    async def stop_notify(self) -> None:
        if self._client.is_connected:
            await self._client.stop_notify(NOTIFY_CHAR_UUID)
```

(`disconnect`/`_write`/`set_rgb`/`turn_off` otherwise unchanged.) Export in `__init__.py`:

```python
from .light import YN360Light
from .protocol import WhiteState, cool_warm_to_kelvin
from .scanner import discover

__version__ = "0.2.0"
__all__ = ["YN360Light", "WhiteState", "cool_warm_to_kelvin", "discover"]
```

- [ ] **Step 4: Run the full library suite**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git -C ~/Github/yn360-ble add src/yn360/ tests/test_light.py
git -C ~/Github/yn360-ble commit -m "feat: channel param, notify subscription, injectable connection factory"
```

---

### Task 3: CLI channel support (library)

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/src/yn360/__main__.py`
- Test: `/Users/hudsonbrendon/Github/yn360-ble/tests/test_cli.py`

**Interfaces:**
- Consumes: Task 2's `set_white(kelvin, brightness, channel)`.
- Produces: `python -m yn360 white <address> <kelvin> --channel N`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_cli.py`, matching its existing parser-test style)

```python
def test_white_accepts_channel():
    parser = build_parser()
    args = parser.parse_args(["white", "AA:BB", "5500", "--channel", "3"])
    assert args.channel == 3


def test_white_channel_defaults_to_1():
    parser = build_parser()
    args = parser.parse_args(["white", "AA:BB", "5500"])
    assert args.channel == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/test_cli.py -v`
Expected: FAIL with `AttributeError: channel` / argparse error.

- [ ] **Step 3: Implement**

In `build_parser()` add to the white subparser: `p_white.add_argument("--channel", type=int, default=1)`.
In `_run()` change the white branch to `await light.set_white(args.kelvin, channel=args.channel)`.

- [ ] **Step 4: Run to verify pass, then commit**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/ -v` — all PASS.

```bash
git -C ~/Github/yn360-ble add src/yn360/__main__.py tests/test_cli.py
git -C ~/Github/yn360-ble commit -m "feat(cli): --channel option for white command"
```

---

### Task 4: Release yn360-ble 0.2.0

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/pyproject.toml` (version = "0.2.0")
- Modify: `/Users/hudsonbrendon/Github/yn360-ble/README.md` (document channel, standby, notify APIs)

**Interfaces:**
- Produces: `yn360-ble==0.2.0` on PyPI. Task 5's manifest pin depends on it.

- [ ] **Step 1: Bump version in `pyproject.toml` and `src/yn360/__init__.py` to 0.2.0** (Task 2 already set `__init__.py`; verify both agree)

- [ ] **Step 2: Update README with the new APIs** (channel arg, `start_notify`, `cool_warm_to_kelvin`, `client_factory`)

- [ ] **Step 3: Full suite + build**

Run: `cd ~/Github/yn360-ble && python -m pytest tests/ -v && python -m build`
Expected: tests PASS, wheel + sdist built.

- [ ] **Step 4: Commit, tag, release**

```bash
git -C ~/Github/yn360-ble add pyproject.toml README.md
git -C ~/Github/yn360-ble commit -m "chore: release 0.2.0"
git -C ~/Github/yn360-ble tag v0.2.0
git -C ~/Github/yn360-ble push origin main v0.2.0
```

Publishing: use the repo's existing release workflow (`.github/workflows/`) if it publishes on tag; otherwise `python -m twine upload dist/*`. Verify with `pip index versions yn360-ble` (or `pip install yn360-ble==0.2.0` in a scratch venv) before starting Task 5.

---

### Task 5: Integration uses establish_connection (robust connections)

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/light.py` (`_make_device`, imports)
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/manifest.json` (`yn360-ble==0.2.0`, version `0.3.0`)
- Test: `/Users/hudsonbrendon/Github/yn360-homeassistant/tests/integration/test_light.py`

**Interfaces:**
- Consumes: Task 2's `YN360Light(device, client_factory=...)`; `establish_connection` from `bleak_retry_connector`.
- Produces: `_make_device` returns a `YN360Light` wired with a factory that calls `establish_connection(BleakClient, ble_device, self._address, max_attempts=2)`.

- [ ] **Step 0: Install the new lib in the dev venv**

Run: `cd ~/Github/yn360-homeassistant && .venv/bin/pip install -U yn360-ble==0.2.0` (or `.venv/bin/pip install -e ~/Github/yn360-ble` while iterating).

- [ ] **Step 1: Write the failing test** (append to `tests/integration/test_light.py`, reusing its `_setup`/`_patched_device` helpers)

```python
async def test_make_device_wires_client_factory(hass):
    """_make_device builds a YN360Light with a client factory (establish_connection)."""
    with _patched_device():
        entity_id = await _setup(hass)
        entity = hass.data["entity_components"]["light"].get_entity(entity_id)
    captured = {}

    def fake_light(dev, client_factory=None):
        captured["device"] = dev
        captured["factory"] = client_factory
        return AsyncMock()

    with patch(
        "custom_components.yongnuo_yn360.light.YN360Light", side_effect=fake_light
    ), patch(
        "custom_components.yongnuo_yn360.light.bluetooth.async_ble_device_from_address",
        return_value=object(),
    ):
        entity._make_device()
    assert captured["factory"] is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/Github/yn360-homeassistant && .venv/bin/python -m pytest tests/integration/test_light.py -v`
Expected: new test FAILS (`YN360Light` called without `client_factory`, so `captured["factory"]` is None).

- [ ] **Step 3: Implement in `light.py`**

```python
from bleak import BleakClient
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS, establish_connection


    def _make_device(self) -> YN360Light:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )
        if ble_device is None:
            raise HomeAssistantError(f"YN360 {self._address} is not in range")

        def _connect_via_retry_connector() -> Awaitable[BleakClient]:
            # Connection-slot aware and service-caching; matters when the
            # light is reached through an ESPHome Bluetooth proxy.
            return establish_connection(
                BleakClient, ble_device, self._address, max_attempts=2
            )

        return YN360Light(ble_device, client_factory=_connect_via_retry_connector)
```

- [ ] **Step 4: Run the full integration suite**

Run: `cd ~/Github/yn360-homeassistant && .venv/bin/python -m pytest tests/integration -v`
Expected: all PASS.

- [ ] **Step 5: Bump manifest and commit**

`manifest.json`: `"requirements": ["yn360-ble==0.2.0", "bleak-retry-connector>=3.4.0"]`, `"version": "0.3.0"`.

```bash
git -C ~/Github/yn360-homeassistant add custom_components/yongnuo_yn360/ tests/integration/test_light.py
git -C ~/Github/yn360-homeassistant commit -m "feat: establish_connection-backed BLE connections; require yn360-ble 0.2.0"
```

- [ ] **Step 6: Verify on the real light**

Reload the integration in HA (Devices → Yongnuo YN360 → Reload), toggle the `YN360III_Pro` entity on/off, confirm the physical light responds and no errors in the HA log.

---

### Task 6 (CONDITIONAL on Task 0 `KNOB_NOTIFY: YES`): Physical-knob state feedback

Skip this task entirely — and note it in HARDWARE.md — if Task 0 shows the III Pro never notifies on knob turns.

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/light.py`
- Test: `/Users/hudsonbrendon/Github/yn360-homeassistant/tests/integration/test_light.py`

**Interfaces:**
- Consumes: Task 2's `start_notify(callback)`, `WhiteState`; Task 1's `cool_warm_to_kelvin` (import from `yn360`).
- Produces: while a persistent connection is held, turning the light's physical white-tone knobs updates the HA entity state (kelvin, brightness, on/off).

- [ ] **Step 1: Write the failing tests**

```python
from yn360 import WhiteState


async def test_persistent_mode_subscribes_to_notify(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_PERSISTENT_CONNECTION: True})
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    device.start_notify.assert_awaited_once()


async def test_knob_callback_updates_state(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_PERSISTENT_CONNECTION: True})
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id}, blocking=True
        )
        knob_cb = device.start_notify.await_args.args[0]
        knob_cb(WhiteState(channel=1, cool=100, warm=0))
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
    assert state.attributes["color_temp_kelvin"] == 5500
    assert state.attributes["brightness"] == 255


async def test_non_persistent_mode_does_not_subscribe(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass)
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    device.start_notify.assert_not_awaited()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/Github/yn360-homeassistant && .venv/bin/python -m pytest tests/integration/test_light.py -v`
Expected: the three new tests FAIL.

- [ ] **Step 3: Implement in `light.py`**

In `__init__` add `self._notify_started = False`. In `_async_run`'s success branch (persistent case):

```python
                    if self._persistent:
                        self._device = device
                        if not self._notify_started:
                            await device.start_notify(self._on_knob_change)
                            self._notify_started = True
```

In `_async_close`, reset `self._notify_started = False` before dropping the device. Add the callback (HA's bluetooth backend delivers notifications on the event loop, but schedule threadsafe to be robust to backend differences):

```python
    def _on_knob_change(self, state: WhiteState) -> None:
        """Handle a white-tone frame emitted when the physical knobs move."""
        result = cool_warm_to_kelvin(state.cool, state.warm)
        if result is None:
            self._attr_is_on = False
        else:
            kelvin, ratio = result
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_color_temp_kelvin = kelvin
            self._attr_brightness = round(ratio * 255)
            self._attr_is_on = True
        self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)
```

Imports: `from yn360 import WhiteState, YN360Light, cool_warm_to_kelvin`.

- [ ] **Step 4: Run the full suite**

Run: `cd ~/Github/yn360-homeassistant && .venv/bin/python -m pytest tests/integration -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git -C ~/Github/yn360-homeassistant add custom_components/yongnuo_yn360/light.py tests/integration/test_light.py
git -C ~/Github/yn360-homeassistant commit -m "feat: physical-knob state feedback in persistent-connection mode"
```

- [ ] **Step 6: Verify on the real light**

Enable "persistent connection" in the integration options, turn the light on from HA, then turn the physical white-tone knobs — the entity's kelvin/brightness should follow in the HA UI.

---

### Task 7 (CONDITIONAL on Task 0 `CHANNELS_2_TO_8: YES`): Channel option in the options flow

Skip if the III Pro ignores channels ≠ 1 (the channel plumbing from Tasks 1–3 still ships in the lib for YN360-II users).

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/const.py`
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/config_flow.py`
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/light.py`
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/custom_components/yongnuo_yn360/strings.json` + files in `translations/`
- Test: `/Users/hudsonbrendon/Github/yn360-homeassistant/tests/integration/test_options_flow.py`, `test_light.py`

**Interfaces:**
- Consumes: Task 2's `set_white(kelvin, brightness, channel)`.
- Produces: `CONF_CHANNEL = "channel"`, `DEFAULT_CHANNEL = 1` in `const.py`; options-flow field validating 1–8; `light.py` passes `channel=self._channel` to `set_white`.

- [ ] **Step 1: Write the failing tests**

In `test_options_flow.py` (reuse the file's existing entry-setup helper and submit style; include the channel key alongside the existing options keys):

```python
async def test_options_flow_accepts_channel(hass):
    # follow the existing test in this file for entry setup + options init,
    # then submit with the full option set:
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERSISTENT_CONNECTION: False,
            CONF_MIN_KELVIN: 3200,
            CONF_MAX_KELVIN: 5600,
            CONF_CHANNEL: 3,
        },
    )
    assert result["type"] == "create_entry"
    assert entry.options[CONF_CHANNEL] == 3
```

In `test_light.py`:

```python
async def test_turn_on_white_passes_channel(hass):
    with _patched_device() as device:
        entity_id = await _setup(hass, {CONF_CHANNEL: 3})
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "color_temp_kelvin": 5000},
            blocking=True,
        )
    assert device.set_white.await_args.kwargs.get("channel") == 3
```

- [ ] **Step 2: Run to verify failure** — `ImportError: CONF_CHANNEL`.

- [ ] **Step 3: Implement**

`const.py`: `CONF_CHANNEL = "channel"`, `DEFAULT_CHANNEL = 1`.
`config_flow.py` schema addition: `vol.Required(CONF_CHANNEL, default=options.get(CONF_CHANNEL, DEFAULT_CHANNEL)): vol.All(vol.Coerce(int), vol.Range(min=1, max=8))`.
`light.py` `__init__`: `self._channel = entry.options.get(CONF_CHANNEL, DEFAULT_CHANNEL)`; in `async_turn_on`'s `_emit` white branch: `return device.set_white(kelvin, ratio, channel=self._channel)` (and the same in `async_turn_off`'s faded white branch).
`strings.json`/translations: add the `channel` field label ("Channel (1-8)"; pt-BR "Canal (1-8)" if a pt translation file exists).

- [ ] **Step 4: Run the full suite** — all PASS.

- [ ] **Step 5: Commit**

```bash
git -C ~/Github/yn360-homeassistant add custom_components/yongnuo_yn360/ tests/integration/
git -C ~/Github/yn360-homeassistant commit -m "feat: configurable white channel (1-8) in options flow"
```

---

### Task 8: Release integration 0.3.0

**Files:**
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/CHANGELOG.md`
- Modify: `/Users/hudsonbrendon/Github/yn360-homeassistant/README.md` (document new options/behavior)

- [ ] **Step 1: Update CHANGELOG.md** with a `## 0.3.0` section: establish_connection-backed connections, yn360-ble 0.2.0, plus knob feedback / channel option if Tasks 6/7 shipped.

- [ ] **Step 2: Full suite one last time**

Run: `cd ~/Github/yn360-homeassistant && .venv/bin/python -m pytest tests/integration -v`
Expected: all PASS.

- [ ] **Step 3: Commit and tag**

```bash
git -C ~/Github/yn360-homeassistant add CHANGELOG.md README.md
git -C ~/Github/yn360-homeassistant commit -m "chore: release 0.3.0"
git -C ~/Github/yn360-homeassistant tag v0.3.0
git -C ~/Github/yn360-homeassistant push origin main v0.3.0
```
