"""Binary sensor platform for Ultraloq door status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .entity import UltraloqEntity
from .utecio.ble.lock import UtecBleLock


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up door sensors for locks that report bolt status."""

    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    async_add_entities(
        UltraloqDoorSensor(lock)
        for lock in locks
        if lock.capabilities.doorsensor
    )


class UltraloqDoorSensor(UltraloqEntity, BinarySensorEntity):
    """Door contact reported in the lock-status payload."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    def __init__(self, lock: UtecBleLock) -> None:
        """Initialize the sensor."""

        super().__init__(lock, "door")

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
