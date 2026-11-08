"""Mute control for Ultraloq locks."""

from homeassistant.components.switch import SwitchEntity
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
    """Set up mute switches for models declaring mute support."""

    async_add_entities(
        UltraloqMuteSwitch(lock)
        for lock in hass.data[DOMAIN][entry.entry_id][UTEC_LOCKDATA]
        if lock.capabilities.mutemode
    )


class UltraloqMuteSwitch(UltraloqEntity, SwitchEntity):
    """Switch on to mute lock sounds."""

    _attr_name = "Mute"
    _attr_icon = "mdi:volume-mute"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, lock: UtecBleLock) -> None:
        super().__init__(lock, "mute")

    @property
    def is_on(self) -> bool:
        return self.lock.mute

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_mute(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_mute(False)

    async def _async_set_mute(self, muted: bool) -> None:
        try:
            await self.lock.async_set_mute(muted)
        except (UtecBleDeviceError, UtecBleNotFoundError, ValueError) as err:
            raise HomeAssistantError(
                f"Failed to set mute on {self.lock.name}: {err}"
            ) from err
        for callback_func in list(self.lock._ha_state_callbacks):
            callback_func()
