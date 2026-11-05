"""Cloud 0% is unknown only when the same response's level contradicts it."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from custom_components.ultraloq_ble.const import (
    CONF_API_DEVICES,
    CONF_CLOUD_BATTERY,
    CONF_CLOUD_BATTERY_INTERVAL,
    DOMAIN,
)
from homeassistant.const import Platform

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

# suffix: (cloud battery_percent, cloud categorical "battery" level or None if absent)
CASES = {
    "01": (0, 3),    # High contradicts 0
    "02": (0, 2),    # Medium contradicts 0
    "03": (0, 1),    # Low agrees
    "04": (0, 0),    # Critical agrees
    "05": (0, None), # level missing: keep the zero
    "06": (54, 3),   # non-zero passes through
    "07": (0, "3"),  # numeric-string level still contradicts
}
EXPECTED = {
    "01": ("unknown", "percentage_zero_contradicted"),
    "02": ("unknown", "percentage_zero_contradicted"),
    "03": ("0.0", "percentage_valid"),
    "04": ("0.0", "percentage_valid"),
    "05": ("0.0", "percentage_valid"),
    "06": ("54.0", "percentage_valid"),
    "07": ("unknown", "percentage_zero_contradicted"),
}


def _record(suffix):
    percent, level = CASES[suffix]
    params = {"battery_percent": percent}
    if level is not None:
        params["battery"] = level
    return {"uuid": f"AA:BB:CC:DD:EE:{suffix}", "params": params}


async def test_cloud_level_decides_zero(hass):
    """BLE level is unset and BLE is offline: the outcome must not depend on it."""
    locks = [
        SimpleNamespace(
            name=f"Door {suffix}",
            model="U-Bolt-Pro",
            sn="",
            mac_uuid=f"AA:BB:CC:DD:EE:{suffix}",
            lock_status=2,
            battery=-1,
            _ha_available=False,
            last_successful_communication=None,
            capabilities=SimpleNamespace(autolock=False),
        )
        for suffix in CASES
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"email": "fixture", "password": "fixture", CONF_API_DEVICES: []},
        options={CONF_CLOUD_BATTERY: True, CONF_CLOUD_BATTERY_INTERVAL: 6},
    )
    entry.add_to_hass(hass)
    mock_integration(
        hass, MockModule("bluetooth_adapters", async_setup=AsyncMock(return_value=True))
    )
    with (
        patch("custom_components.ultraloq_ble.PLATFORMS", [Platform.SENSOR]),
        patch("custom_components.ultraloq_ble._build_ble_devices", return_value=locks),
        patch(
            "custom_components.ultraloq_ble.coordinator.async_fetch_api_devices",
            new_callable=AsyncMock,
            return_value=[_record(suffix) for suffix in CASES],
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

        for suffix, (state, status) in EXPECTED.items():
            sensor = hass.states.get(f"sensor.door_{suffix}_cloud_battery_level")
            assert sensor is not None, suffix
            assert sensor.state == state, (suffix, sensor.state)
            assert sensor.attributes["cloud_battery_status"] == status, suffix

        assert await hass.config_entries.async_unload(entry.entry_id)
