"""Shared Ultraloq entity behavior."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .utecio.ble.lock import UtecBleLock
from .utecio.enums import DeviceLockStatus


class UltraloqEntity(Entity):
    """Base entity for one Ultraloq lock."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _listen_for_updates = True

    def __init__(self, lock: UtecBleLock, unique_id_suffix: str | None = None) -> None:
        """Initialize shared lock state."""

        self.lock = lock
        self.lock._ha_state_callbacks = getattr(lock, "_ha_state_callbacks", [])
        self._attr_unique_id = f"ul_{lock.mac_uuid}"
        if unique_id_suffix:
            self._attr_unique_id += f"_{unique_id_suffix}"

    @property
    def available(self) -> bool:
        """Return whether BLE and lock state are available."""

        return (
            getattr(self.lock, "_ha_available", True)
            and self.lock.lock_status != DeviceLockStatus.NOTSET.value
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return shared device registry information."""

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

    async def async_added_to_hass(self) -> None:
        """Register for shared lock updates."""

        if self._listen_for_updates:
            self.lock._ha_state_callbacks.append(self._handle_lock_state_update)
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from shared lock updates."""

        if (
            self._listen_for_updates
            and self._handle_lock_state_update in self.lock._ha_state_callbacks
        ):
            self.lock._ha_state_callbacks.remove(self._handle_lock_state_update)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_lock_state_update(self) -> None:
        self.async_write_ha_state()
