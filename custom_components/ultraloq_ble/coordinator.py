"""Optional cloud battery polling, independent of BLE control."""

import asyncio
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_CLOUD_BATTERY_INTERVAL, DEFAULT_CLOUD_BATTERY_INTERVAL, LOGGER
from .util import InvalidCredentials, async_fetch_api_devices
from .utecio.enums import DeviceBatteryLevel

# Categorical cloud levels that contradict a reported 0%.
_LEVELS_CONTRADICTING_ZERO = {DeviceBatteryLevel.MEDIUM.value, DeviceBatteryLevel.HIGH.value}


def _battery_percent(value: object) -> float | None:
    """Accept percentages including zero, excluding missing values and sentinels."""

    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        percent = float(value)
    except (OverflowError, ValueError):
        return None
    return percent if 0 <= percent <= 100 else None


def _zero_contradicted(level: object) -> bool:
    """True when the same cloud record's categorical level is Medium or High.

    Some locks report battery_percent 0 while their level says High. A zero is
    kept when the level is missing, unparseable, or agrees (Low/Critical).
    """

    if isinstance(level, bool):
        return False
    try:
        return int(level) in _LEVELS_CONTRADICTING_ZERO
    except (TypeError, ValueError, OverflowError):
        return False


class CloudBatteryCoordinator(DataUpdateCoordinator[dict[str, float | None]]):
    """Fetch one account's battery readings without reloading BLE devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name="Ultraloq cloud battery",
            update_interval=timedelta(
                hours=entry.options.get(
                    CONF_CLOUD_BATTERY_INTERVAL, DEFAULT_CLOUD_BATTERY_INTERVAL
                )
            ),
        )
        self.entry = entry
        self.data = {}
        self.battery_status: dict[str, str] = {}
        self.last_successful_fetch: datetime | None = None

    async def _async_update_data(self) -> dict[str, float | None]:
        try:
            async with asyncio.timeout(30):
                records = await async_fetch_api_devices(
                    self.hass,
                    self.entry.data[CONF_EMAIL],
                    self.entry.data[CONF_PASSWORD],
                )
        except (ConnectionError, InvalidCredentials) as err:
            raise UpdateFailed("Could not refresh cloud battery readings") from err

        if not isinstance(records, list):
            raise UpdateFailed("Expected a cloud device list")
        readings = {}
        statuses = {}
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("uuid"), str):
                continue
            params = record.get("params")
            raw = params.get("battery_percent") if isinstance(params, dict) else None
            level = params.get("battery") if isinstance(params, dict) else None
            address = record["uuid"].upper()
            readings[address] = _battery_percent(raw)
            if raw is None:
                statuses[address] = "percentage_missing"
            elif readings[address] is None:
                statuses[address] = "percentage_invalid"
            elif readings[address] == 0 and _zero_contradicted(level):
                readings[address] = None
                statuses[address] = "percentage_zero_contradicted"
            else:
                statuses[address] = "percentage_valid"
        self.battery_status = statuses
        self.last_successful_fetch = datetime.now(UTC)
        return readings
