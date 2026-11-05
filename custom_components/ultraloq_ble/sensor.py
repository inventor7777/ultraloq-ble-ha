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
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CLOUD_ACCESS, CONF_CLOUD_BATTERY, DOMAIN, UTEC_LOCKDATA
from .coordinator import CloudBatteryCoordinator
from .entity import UltraloqEntity
from .utecio.ble.lock import UtecBleLock
from .utecio.enums import DeviceBatteryLevel

AUTOLOCK_MODES = {0: "Door Sensor", 1: "Immediate"}


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
    UltraloqSensorDescription(
        key="autolock_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        icon="mdi:timer-lock-outline",
        value_fn=lambda lock: lock.autolock_time if lock.autolock_time >= 0 else None,
    ),
    UltraloqSensorDescription(
        key="autolock_mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(AUTOLOCK_MODES.values()),
        icon="mdi:timer-lock-outline",
        value_fn=lambda lock: AUTOLOCK_MODES.get(lock.autolock_mode),
    ),
    UltraloqSensorDescription(
        key="last_successful_communication",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.last_successful_communication,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ultraloq sensors for a config entry."""

    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    entities: list[SensorEntity] = []
    cloud = None
    if (
        locks
        and entry.data.get(CONF_CLOUD_ACCESS, True)
        and entry.options.get(CONF_CLOUD_BATTERY, False)
    ):
        cloud = CloudBatteryCoordinator(hass, entry)

    for lock in locks:
        for description in SENSORS:
            if (
                description.key.startswith("autolock_")
                and not lock.capabilities.autolock
            ):
                continue
            entities.append(UltraloqSensor(lock, description))
            if description.key == "battery_level" and cloud is not None:
                entities.append(UltraloqCloudBatterySensor(lock, cloud))

    async_add_entities(entities)
    if cloud is not None:
        entry.async_create_background_task(
            hass, cloud.async_refresh(), "Ultraloq initial cloud battery refresh"
        )


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

    @property
    def available(self) -> bool:
        """Keep the last communication visible while the lock is offline."""

        return (
            self.entity_description.key == "last_successful_communication"
            or super().available
        )


class UltraloqCloudBatterySensor(UltraloqEntity, SensorEntity):
    """Cloud-reported percentage, available independently of the BLE connection."""

    _attr_name = "Cloud Battery Level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery-plus-variant"
    _listen_for_updates = False

    def __init__(self, lock: UtecBleLock, coordinator: CloudBatteryCoordinator) -> None:
        super().__init__(lock, "cloud_battery_level")
        self.coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_lock_state_update)
        )

    async def async_update(self) -> None:
        """Refresh the account through HA's debounced manual-update path."""

        if self.enabled:
            await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self.lock.mac_uuid.upper())

    @property
    def extra_state_attributes(self) -> dict:
        last_fetch = self.coordinator.last_successful_fetch
        return {
            "last_successful_cloud_fetch": last_fetch.isoformat()
            if last_fetch
            else None,
            "cloud_update_success": self.coordinator.last_update_success,
            "cloud_battery_status": self.coordinator.battery_status.get(
                self.lock.mac_uuid.upper(), "device_not_returned"
            ),
        }
