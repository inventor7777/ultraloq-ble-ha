"""Button platform for Ultraloq integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UTEC_LOCKDATA
from .entity import UltraloqEntity
from .utecio.ble.device import UtecBleDeviceError, UtecBleNotFoundError
from .utecio.ble.lock import UtecBleLock


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ultraloq buttons for a config entry."""

    locks: list[UtecBleLock] = hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
    async_add_entities(UltraloqRescanButton(lock) for lock in locks)


class UltraloqRescanButton(UltraloqEntity, ButtonEntity):
    """Button entity to force an immediate BLE refresh for one lock."""

    _attr_has_entity_name = True
    _attr_name = "Rescan"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bluetooth-connect"
    _listen_for_updates = False

    def __init__(self, lock: UtecBleLock) -> None:
        """Initialize the button entity."""

        super().__init__(lock, "rescan")

    @property
    def available(self) -> bool:
        """Keep the rescan button available even if the lock is offline."""

        return True

    async def async_press(self) -> None:
        """Force an immediate state refresh from the lock."""

        try:
            if not await self.lock.async_update_status():
                raise HomeAssistantError(
                    f"Skipped rescan for {self.lock.name}: refresh already in progress."
                )
        except (UtecBleDeviceError, UtecBleNotFoundError) as err:
            raise HomeAssistantError(
                f"Failed to rescan {self.lock.name}: {err}"
            ) from err

        for callback_func in list(getattr(self.lock, "_ha_state_callbacks", [])):
            callback_func()
