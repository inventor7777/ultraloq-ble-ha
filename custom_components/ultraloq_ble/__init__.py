"""Ultraloq BLE component."""

from __future__ import annotations

from dataclasses import asdict
import datetime
from enum import Enum
from functools import partial
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_DEVICES,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    SERVICE_GET_DEVICE_INFORMATION,
    SERVICE_REFRESH_LOCKS,
    SERVICE_SET_DEVICE_AUTOLOCK,
    SERVICE_SET_DEVICE_TIME,
    UPDATE_LISTENER,
    UTEC_LOCKDATA,
)
from .utecio.api import build_ble_devices
from .utecio.ble.device import UtecBleDeviceError, UtecBleNotFoundError
from .utecio.ble.lock import UtecBleLock, build_autolock_payload, parse_autolock_hex
from .utecio.const import DOOR_STATUS
from .utecio.enums import DeviceBatteryLevel, DeviceLockStatus, DeviceLockWorkMode
from .util import async_fetch_api_devices

DEVICE_ID = "device_id"
DEVICE_TIME = "datetime"
AUTOLOCK_DURATION = "duration"
AUTOLOCK_DOOR_SENSOR = "door_sensor"
AUTOLOCK_ENABLED = "enabled"
AUTOLOCK_MANUAL = "manual"
GET_DEVICE_INFORMATION_SCHEMA = vol.Schema({vol.Required(DEVICE_ID): cv.string})
SET_DEVICE_TIME_SCHEMA = vol.Schema(
    {vol.Required(DEVICE_ID): cv.string, vol.Optional(DEVICE_TIME): cv.string}
)
SET_DEVICE_AUTOLOCK_SCHEMA = vol.Schema(
    {
        vol.Required(DEVICE_ID): cv.string,
        vol.Optional(AUTOLOCK_DURATION, default={"minutes": 1}): (
            cv.positive_time_period_dict
        ),
        vol.Optional(AUTOLOCK_DOOR_SENSOR, default=False): cv.boolean,
        vol.Optional(AUTOLOCK_ENABLED, default=True): cv.boolean,
        vol.Optional(AUTOLOCK_MANUAL): cv.string,
    }
)


def _enum_name(enum_type: type[Enum], value: int) -> str:
    """Return a stable YAML-friendly enum name."""

    try:
        return enum_type(value).name.lower()
    except ValueError:
        return f"unknown_{value}"


def _find_lock(hass: HomeAssistant, device_id: str) -> UtecBleLock:
    """Find a loaded lock from its Home Assistant device ID."""

    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device {device_id} was not found.")
    identifier = next(
        (value for domain, value in device.identifiers if domain == DOMAIN), None
    )
    if identifier is None:
        raise ServiceValidationError("Selected device is not an Ultraloq BLE lock.")
    for entry_data in hass.data.get(DOMAIN, {}).values():
        for lock in entry_data.get(UTEC_LOCKDATA, []):
            if lock.mac_uuid == identifier:
                return lock
    raise ServiceValidationError("Selected Ultraloq BLE lock is not loaded.")


async def _async_handle_get_device_information(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Probe and return all information supported by one lock."""

    lock = _find_lock(hass, call.data[DEVICE_ID])
    try:
        probe = await lock.async_get_device_information()
    except (UtecBleDeviceError, UtecBleNotFoundError) as err:
        raise HomeAssistantError(f"Failed to connect to {lock.name}: {err}") from err

    capabilities = asdict(lock.capabilities)
    state: dict[str, Any] = {
        "lock_status": _enum_name(DeviceLockStatus, lock.lock_status)
    }
    state["door_status"] = DOOR_STATUS.get(
        lock.door_status, f"Unknown ({lock.door_status})"
    )
    if lock.battery != DeviceBatteryLevel.NOTSET.value:
        state["battery_level"] = _enum_name(DeviceBatteryLevel, lock.battery)
    if lock.capabilities.autolock and lock.autolock_time >= 0:
        state["autolock_seconds"] = lock.autolock_time
    if lock.autolock_enabled is not None:
        state["autolock_enabled"] = lock.autolock_enabled
    if lock.capabilities.mutemode:
        state["muted"] = lock.mute
    if lock.lock_mode != DeviceLockWorkMode.NOTSET.value:
        state["lock_mode"] = _enum_name(DeviceLockWorkMode, lock.lock_mode)
    if lock.calendar:
        state["device_time"] = lock.calendar.isoformat()
    if lock.device_time_offset is not None:
        state["device_time_offset_seconds"] = int(
            lock.device_time_offset.total_seconds()
        )

    response: ServiceResponse = {
        "device": {
            "name": lock.name,
            "model": lock.model,
            "serial_number": lock.sn or None,
            "bluetooth_address": str(lock.mac_uuid),
            "wake_address": str(lock.wurx_uuid) if lock.wurx_uuid else None,
        },
        "state": state,
        "capabilities": sorted(
            name for name, supported in capabilities.items() if supported is True
        ),
        "capability_settings": {
            "add_user_remove_count": lock.capabilities.adduserremovenum,
            "seconds": lock.capabilities.secondsarray,
            "minutes": lock.capabilities.mtimearray,
        },
        "raw_responses": probe["responses"],
    }
    if probe["errors"]:
        response["query_failures"] = probe["errors"]
    return response


async def _async_handle_set_device_time(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Set one lock's clock from an ISO timestamp or Home Assistant time."""

    lock = _find_lock(hass, call.data[DEVICE_ID])
    value = call.data.get(DEVICE_TIME)
    if value:
        try:
            device_time = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as err:
            raise ServiceValidationError(
                f"Invalid ISO 8601 date and time: {value}"
            ) from err
        if device_time.tzinfo is not None:
            device_time = dt_util.as_local(device_time)
    else:
        device_time = dt_util.now

    try:
        result = await lock.async_set_device_time(device_time)
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (UtecBleDeviceError, UtecBleNotFoundError) as err:
        raise HomeAssistantError(f"Failed to set time on {lock.name}: {err}") from err

    return {
        "device": {"name": lock.name, "bluetooth_address": str(lock.mac_uuid)},
        **result,
    }


async def _async_handle_set_device_autolock(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Set one lock's auto-lock configuration."""

    lock = _find_lock(hass, call.data[DEVICE_ID])
    manual = call.data.get(AUTOLOCK_MANUAL, "").strip()
    if manual:
        try:
            payload = parse_autolock_hex(manual)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
    else:
        duration = call.data[AUTOLOCK_DURATION]
        seconds = duration.total_seconds()
        if not seconds.is_integer():
            raise ServiceValidationError("Auto-lock duration must use whole seconds.")
        try:
            payload = build_autolock_payload(
                int(seconds),
                call.data[AUTOLOCK_DOOR_SENSOR],
                call.data[AUTOLOCK_ENABLED],
            )
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    try:
        await lock.async_set_autolock(payload)
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (UtecBleDeviceError, UtecBleNotFoundError) as err:
        raise HomeAssistantError(
            f"Failed to set auto-lock on {lock.name}: {err}"
        ) from err

    for callback_func in list(getattr(lock, "_ha_state_callbacks", [])):
        callback_func()

    return {
        "device": {"name": lock.name, "bluetooth_address": str(lock.mac_uuid)},
        "payload": payload.hex(),
    }


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register Ultraloq BLE actions."""

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DEVICE_INFORMATION,
        partial(_async_handle_get_device_information, hass),
        schema=GET_DEVICE_INFORMATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DEVICE_TIME,
        partial(_async_handle_set_device_time, hass),
        schema=SET_DEVICE_TIME_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DEVICE_AUTOLOCK,
        partial(_async_handle_set_device_autolock, hass),
        schema=SET_DEVICE_AUTOLOCK_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


def _build_ble_devices(api_devices: list[dict[str, Any]]) -> list[UtecBleLock]:
    """Build BLE lock objects from cached API metadata."""

    return build_ble_devices(api_devices)


def debug_mode() -> bool:
    """Return whether integration debug logging is enabled."""

    return LOGGER.isEnabledFor(logging.DEBUG)


async def _async_refresh_entry_devices(
    hass: HomeAssistant, entry: ConfigEntry
) -> list[dict[str, Any]]:
    """Fetch and persist fresh API device metadata for one config entry."""

    api_devices = await async_fetch_api_devices(
        hass, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
    )
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_API_DEVICES: api_devices}
    )
    return api_devices


async def _async_handle_refresh_locks(hass: HomeAssistant, call: ServiceCall) -> None:
    """Refresh cached lock metadata for all configured Ultraloq entries."""

    for entry in hass.config_entries.async_entries(DOMAIN):
        await _async_refresh_entry_devices(hass, entry)
        await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lock from a config entry."""

    api_devices = entry.data.get(CONF_API_DEVICES)
    if api_devices is None:
        api_devices = await _async_refresh_entry_devices(hass, entry)

    devices = _build_ble_devices(api_devices)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {UTEC_LOCKDATA: devices}

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_LOCKS):
        hass.services.async_register(
            DOMAIN, SERVICE_REFRESH_LOCKS, partial(_async_handle_refresh_locks, hass)
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Ultraloq config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        update_listener = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()
        del hass.data[DOMAIN][entry.entry_id]
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
            if hass.services.has_service(DOMAIN, SERVICE_REFRESH_LOCKS):
                hass.services.async_remove(DOMAIN, SERVICE_REFRESH_LOCKS)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""

    await hass.config_entries.async_reload(entry.entry_id)
