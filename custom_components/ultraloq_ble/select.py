"""Select platform for Ultraloq integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .utecio.ble.device import UtecBleDeviceError, UtecBleNotFoundError
from .utecio.ble.lock import UtecBleLock
from .utecio.enums import DeviceLockStatus, DeviceLockWorkMode


def _lock_mode_label(mode: DeviceLockWorkMode) -> str:
    """Return the Home Assistant label for a lock mode."""

    return mode.name.replace("_", " ").title()


def _supported_lock_mode_options(lock: UtecBleLock) -> list[str]:
    """Return the supported lock-mode options for a specific lock."""

    options = [_lock_mode_label(DeviceLockWorkMode.NORMAL)]
    if getattr(lock.capabilities, "passage", False):
        options.append(_lock_mode_label(DeviceLockWorkMode.PASSAGE))
    if getattr(lock.capabilities, "lockout", False):
        options.append(_lock_mode_label(DeviceLockWorkMode.LOCKOUT))
    return options


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ultraloq select entities for a config entry."""
    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    entities: list[UltraloqLockModeSelect] = []

    for lock in locks:
        if not (
            getattr(lock.capabilities, "passage", False)
            or getattr(lock.capabilities, "lockout", False)
        ):
            continue
        if not hasattr(lock, "_ha_state_callbacks"):
            lock._ha_state_callbacks = []
        entities.append(UltraloqLockModeSelect(lock))

    async_add_entities(entities)


class UltraloqLockModeSelect(SelectEntity):
    """Select entity for the Ultraloq lock work mode."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Lock Mode"
    _attr_icon = "mdi:lock-smart"

    def __init__(self, lock: UtecBleLock) -> None:
        """Initialize the lock-mode select entity."""
        self.lock = lock
        self._attr_unique_id = f"ul_{self.lock.mac_uuid}_lock_mode_select"
        self._attr_options = _supported_lock_mode_options(lock)

    @property
    def available(self) -> bool:
        """Return availability."""
        return (
            getattr(self.lock, "_ha_available", True)
            and self.lock.lock_status != DeviceLockStatus.NOTSET.value
        )

    @property
    def current_option(self) -> str | None:
        """Return the current lock mode."""
        try:
            mode = DeviceLockWorkMode(self.lock.lock_mode)
        except ValueError:
            return None
        return None if mode is DeviceLockWorkMode.NOTSET else _lock_mode_label(mode)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this lock."""
        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self.lock.mac_uuid)},
            "connections": {
                (
                    CONNECTION_BLUETOOTH,
                    device_registry.format_mac(self.lock.mac_uuid),
                )
            },
            "name": self.lock.name,
            "manufacturer": "U-tec",
            "model": self.lock.model or "Ultraloq Lock",
        }
        if self.lock.sn:
            info["serial_number"] = self.lock.sn
        return info

    async def async_select_option(self, option: str) -> None:
        """Set the lock work mode."""
        mode = DeviceLockWorkMode[option.upper().replace(" ", "_")]
        try:
            await self.lock.async_set_workmode(mode)
        except (UtecBleDeviceError, UtecBleNotFoundError):
            raise

        # Keep all entities in sync immediately after a successful command.
        self.lock.lock_mode = mode.value
        for callback_func in list(self.lock._ha_state_callbacks):
            callback_func()

    async def async_added_to_hass(self) -> None:
        """Register shared state callback."""
        self.lock._ha_state_callbacks.append(self._handle_lock_state_update)
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister shared state callback."""
        if self._handle_lock_state_update in self.lock._ha_state_callbacks:
            self.lock._ha_state_callbacks.remove(self._handle_lock_state_update)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_lock_state_update(self) -> None:
        """Handle a shared lock state update."""
        self.async_write_ha_state()
