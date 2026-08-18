"""Number platform for Ultraloq integration."""
from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .entity import UltraloqEntity
from .utecio.ble.lock import UtecBleLock


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ultraloq number entities for a config entry."""

    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    entities: list[UltraloqAutolockNumber] = []

    for lock in locks:
        if not lock.capabilities.autolock:
            continue
        entities.append(UltraloqAutolockNumber(lock))

    async_add_entities(entities)


class UltraloqAutolockNumber(UltraloqEntity, NumberEntity):
    """Number entity for the Ultraloq auto-lock timer."""

    _attr_name = "Autolock Time"
    _attr_native_min_value = 0
    _attr_native_max_value = 300
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-lock-outline"

    def __init__(self, lock: UtecBleLock) -> None:
        """Initialize the number entity."""

        super().__init__(lock, "autolock_time")

    @property
    def native_value(self) -> float | None:
        """Return the current auto-lock timer."""

        return self.lock.autolock_time if self.lock.autolock_time >= 0 else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the auto-lock timer in seconds."""

        seconds = int(value)
        await self.lock.async_set_autolock(seconds)
        for callback_func in list(self.lock._ha_state_callbacks):
            callback_func()
