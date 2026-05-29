"""Constants for the Yongnuo YN360 integration."""

from __future__ import annotations

import logging

DOMAIN = "yongnuo_yn360"

LOGGER = logging.getLogger(__package__)

MANUFACTURER = "Yongnuo"
MODEL = "YN360 III Pro"

# Bi-colour range of the YN360 III Pro. The official spec is 3200–5600 K; the
# defaults below are used unless overridden in the options flow.
DEFAULT_MIN_KELVIN = 3200
DEFAULT_MAX_KELVIN = 5600

# Options-flow keys.
CONF_PERSISTENT_CONNECTION = "persistent_connection"
CONF_MIN_KELVIN = "min_kelvin"
CONF_MAX_KELVIN = "max_kelvin"

DEFAULT_PERSISTENT_CONNECTION = False

# Connection retry policy. Each BLE command opens a short-lived connection
# (unless persistent), which can fail transiently when the light is busy or the
# proxy link is congested, so commands are retried with a linear backoff.
CONNECT_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 0.5

# Software transition: the YN360 has no native fade, so a requested transition is
# emulated by stepping the brightness over the duration while holding a single
# connection. Steps are capped to keep the BLE traffic sane.
TRANSITION_STEP_SECONDS = 0.2
TRANSITION_MAX_STEPS = 30
