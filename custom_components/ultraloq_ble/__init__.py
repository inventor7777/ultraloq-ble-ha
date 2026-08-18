"""Ultraloq BLE component."""
from __future__ import annotations
from functools import partial
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_API_DEVICES,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    SERVICE_REFRESH_LOCKS,
    UPDATE_LISTENER,
    UTEC_LOCKDATA,
)
from .util import async_fetch_api_devices
from .utecio.api import build_ble_devices
from .utecio.ble.lock import UtecBleLock


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
        hass,
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_API_DEVICES: api_devices},
    )
    return api_devices


async def _async_handle_refresh_locks(
    hass: HomeAssistant, call: ServiceCall
) -> None:
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
            DOMAIN,
            SERVICE_REFRESH_LOCKS,
            partial(_async_handle_refresh_locks, hass),
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
