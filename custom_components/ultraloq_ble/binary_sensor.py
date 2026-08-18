"""Binary sensor platform for Ultraloq door status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .utecio.ble.lock import UtecBleLock
from .utecio.const import NO_BOLT_STATUS_MODELS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up door sensors for locks that report bolt status."""

    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    async_add_entities(
        UltraloqDoorSensor(lock)
        for lock in locks
        if lock.model not in NO_BOLT_STATUS_MODELS
    )


class UltraloqDoorSensor(BinarySensorEntity):
    """Door contact reported in the lock-status payload."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, lock: UtecBleLock) -> None:
        """Initialize the sensor."""

        self.lock = lock
        self._attr_unique_id = f"ul_{self.lock.mac_uuid}_door"

    @property
    def available(self) -> bool:
        """Return availability when the lock reports a door state."""

        return (
            getattr(self.lock, "_ha_available", True)
            and self.lock.bolt_status in (0, 1)
        )

    @property
    def is_on(self) -> bool | None:
        """Return true when the door is open."""

        if self.lock.bolt_status not in (0, 1):
            return None
        return self.lock.bolt_status == 0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this lock."""

        info: DeviceInfo = {
            "identifiers": {(DOMAIN, self.lock.mac_uuid)},
            "connections": {
                (CONNECTION_BLUETOOTH, device_registry.format_mac(self.lock.mac_uuid))
            },
            "name": self.lock.name,
            "manufacturer": "U-tec",
            "model": self.lock.model or "Ultraloq Lock",
        }
        if self.lock.sn:
            info["serial_number"] = self.lock.sn
        return info

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
