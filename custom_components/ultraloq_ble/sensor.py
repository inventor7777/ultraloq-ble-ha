"""Sensor platform for Ultraloq integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .entity import UltraloqEntity
from .utecio.ble.lock import UtecBleLock
from .utecio.enums import DeviceBatteryLevel


@dataclass(frozen=True, kw_only=True)
class UltraloqSensorDescription(SensorEntityDescription):
    """Description for an Ultraloq sensor."""

    value_fn: Callable[[UtecBleLock], object]


def _battery_level(lock: UtecBleLock) -> str | None:
    """Return a known battery level without rejecting new firmware values."""

    if lock.battery == DeviceBatteryLevel.NOTSET.value:
        return None
    try:
        return DeviceBatteryLevel(lock.battery).name
    except ValueError:
        return None


SENSORS: tuple[UltraloqSensorDescription, ...] = (
    UltraloqSensorDescription(
        key="battery_level",
        device_class=SensorDeviceClass.ENUM,
        options=[level.name for level in DeviceBatteryLevel if level.name != "NOTSET"],
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-bluetooth-variant",
        value_fn=_battery_level,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ultraloq sensors for a config entry."""

    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    entities: list[UltraloqSensor] = []

    for lock in locks:
        entities.extend(UltraloqSensor(lock, description) for description in SENSORS)

    async_add_entities(entities)


class UltraloqSensor(UltraloqEntity, SensorEntity):
    """Representation of an Ultraloq sensor."""

    entity_description: UltraloqSensorDescription

    def __init__(
        self, lock: UtecBleLock, description: UltraloqSensorDescription
    ) -> None:
        """Initialize the sensor."""

        super().__init__(lock, description.key)
        self.entity_description = description
        self._attr_name = self.entity_description.key.replace("_", " ").title()

    @property
    def native_value(self):
        """Return the sensor value."""

        return self.entity_description.value_fn(self.lock)
