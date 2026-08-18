"""Select platform for Ultraloq integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .entity import UltraloqEntity
from .utecio.ble.lock import UtecBleLock
from .utecio.enums import DeviceLockWorkMode


def _lock_mode_label(mode: DeviceLockWorkMode) -> str:
    """Return the Home Assistant label for a lock mode."""

    return mode.name.replace("_", " ").title()


def _supported_lock_mode_options(lock: UtecBleLock) -> list[str]:
    """Return the supported lock-mode options for a specific lock."""

    options = [_lock_mode_label(DeviceLockWorkMode.NORMAL)]
    if lock.capabilities.passage:
        options.append(_lock_mode_label(DeviceLockWorkMode.PASSAGE))
    if lock.capabilities.lockout:
        options.append(_lock_mode_label(DeviceLockWorkMode.LOCKOUT))
    return options


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ultraloq select entities for a config entry."""
    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    entities: list[UltraloqLockModeSelect] = []

    for lock in locks:
        if not (lock.capabilities.passage or lock.capabilities.lockout):
            continue
        entities.append(UltraloqLockModeSelect(lock))

    async_add_entities(entities)


class UltraloqLockModeSelect(UltraloqEntity, SelectEntity):
    """Select entity for the Ultraloq lock work mode."""

    _attr_name = "Lock Mode"
    _attr_icon = "mdi:lock-smart"

    def __init__(self, lock: UtecBleLock) -> None:
        """Initialize the lock-mode select entity."""
        super().__init__(lock, "lock_mode_select")
        self._attr_options = _supported_lock_mode_options(lock)

    @property
    def current_option(self) -> str | None:
        """Return the current lock mode."""
        try:
            mode = DeviceLockWorkMode(self.lock.lock_mode)
        except ValueError:
            return None
        return None if mode is DeviceLockWorkMode.NOTSET else _lock_mode_label(mode)

    async def async_select_option(self, option: str) -> None:
        """Set the lock work mode."""
        mode = DeviceLockWorkMode[option.upper().replace(" ", "_")]
        await self.lock.async_set_workmode(mode)

        # Keep all entities in sync immediately after a successful command.
        self.lock.lock_mode = mode.value
        for callback_func in list(self.lock._ha_state_callbacks):
            callback_func()
