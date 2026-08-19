"""Constants for Ultraloq BLE."""

import asyncio
import logging

from aiohttp.client_exceptions import ClientConnectionError

from homeassistant.const import Platform

LOGGER = logging.getLogger(__package__)

DEFAULT_SCAN_INTERVAL = 300
DEFAULT_STAGGER_DELAY = 10
DOMAIN = "ultraloq_ble"
PLATFORMS = [
    Platform.LOCK,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
]

DEFAULT_NAME = "Ultraloq BLE"
TIMEOUT = 20
CONF_API_DEVICES = "api_devices"
CONF_STAGGER_DELAY = "stagger_delay"
SERVICE_REFRESH_LOCKS = "refresh_locks"
SERVICE_GET_DEVICE_INFORMATION = "get_device_information"
SERVICE_SET_DEVICE_TIME = "set_device_time"
SERVICE_SET_DEVICE_AUTOLOCK = "set_device_autolock"

UL_ERRORS = (asyncio.TimeoutError, ClientConnectionError)

CONF_ZONE_METHOD = "zone_method"
DEFAULT_ZONE_METHOD = "Utec"
ZONE_METHODS = ["Utec", "Home Assistant"]

UPDATE_LISTENER = "update_listener"
UTEC_LOCKDATA = "utec_data"
