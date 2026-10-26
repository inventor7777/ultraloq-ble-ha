"""Cloud battery lifecycle tests using Home Assistant's real coordinator."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    async_fire_time_changed,
    mock_integration,
)

from custom_components.ultraloq_ble.const import (
    CONF_API_DEVICES,
    CONF_CLOUD_BATTERY,
    CONF_CLOUD_BATTERY_INTERVAL,
    DOMAIN,
)
from homeassistant.const import Platform
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture
def locks():
    """Two BLE locks whose state must survive optional cloud failures."""
    return [
        SimpleNamespace(
            name=f"Door {index}",
            model="U-Bolt-Pro",
            sn="",
            mac_uuid=f"AA:BB:CC:DD:EE:0{index}",
            lock_status=2,
            battery=3,
            _ha_available=True,
            last_successful_communication=None,
            capabilities=SimpleNamespace(autolock=False),
        )
        for index in (1, 2)
    ]


@pytest.fixture
def entry(hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"email": "fixture", "password": "fixture", CONF_API_DEVICES: []},
        options={CONF_CLOUD_BATTERY: True, CONF_CLOUD_BATTERY_INTERVAL: 6},
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture
def integration(hass, locks):
    """Load the real sensor platform without opening Bluetooth connections."""
    mock_integration(
        hass, MockModule("bluetooth_adapters", async_setup=AsyncMock(return_value=True))
    )
    with (
        patch("custom_components.ultraloq_ble.PLATFORMS", [Platform.SENSOR]),
        patch("custom_components.ultraloq_ble._build_ble_devices", return_value=locks),
    ):
        yield


@pytest.fixture
def fetch(locks):
    with patch(
        "custom_components.ultraloq_ble.coordinator.async_fetch_api_devices",
        new_callable=AsyncMock,
        return_value=[
            {"uuid": lock.mac_uuid, "params": {"battery_percent": 75}} for lock in locks
        ],
    ) as mocked:
        yield mocked


async def test_scheduled_refresh_and_unload(hass, entry, integration, fetch, freezer):
    """The shared timer refreshes both sensors and stops after entry unload."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    fetch.assert_awaited_once()
    assert hass.states.get("sensor.door_1_cloud_battery_level").state == "75.0"
    assert hass.states.get("sensor.door_2_cloud_battery_level").state == "75.0"

    fetch.return_value = [
        {"uuid": "AA:BB:CC:DD:EE:01", "params": {"battery_percent": 50}},
        {"uuid": "AA:BB:CC:DD:EE:02", "params": {"battery_percent": 60}},
    ]
    freezer.tick(timedelta(hours=6, seconds=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert fetch.await_count == 2
    assert hass.states.get("sensor.door_1_cloud_battery_level").state == "50.0"
    assert hass.states.get("sensor.door_2_cloud_battery_level").state == "60.0"

    assert await hass.config_entries.async_unload(entry.entry_id)
    freezer.tick(timedelta(hours=7))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert fetch.await_count == 2


@pytest.mark.parametrize("initial", [True, False])
async def test_inflight_refresh_is_cancelled_on_unload(
    hass, entry, integration, fetch, freezer, initial
):
    """Setup never waits for cloud; unload cancels initial and scheduled requests."""
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def pending(*args):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    if initial:
        fetch.side_effect = pending
    assert await hass.config_entries.async_setup(entry.entry_id)
    if not initial:
        await hass.async_block_till_done(wait_background_tasks=True)
        fetch.side_effect = pending
        freezer.tick(timedelta(hours=6, seconds=1))
        async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    await asyncio.wait_for(started.wait(), timeout=1)
    assert hass.states.get("sensor.door_1_battery_level").state == "HIGH"
    assert hass.states.get("sensor.door_1_cloud_battery_level").state == (
        "unknown" if initial else "75.0"
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert cancelled.is_set()
    calls = 1 if initial else 2
    assert fetch.await_count == calls
    freezer.tick(timedelta(hours=7))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert fetch.await_count == calls


async def test_overlapping_manual_refreshes(hass, entry, integration, fetch, freezer):
    """Manual updates use the real coordinator lock and shared debouncer."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    started = asyncio.Event()
    release = asyncio.Event()
    active = 0
    maximum_active = 0

    async def pending(*args):
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(active, maximum_active)
        started.set()
        try:
            await release.wait()
            return [{"uuid": "AA:BB:CC:DD:EE:01", "params": {"battery_percent": 40}}]
        finally:
            active -= 1

    fetch.side_effect = pending
    first = asyncio.create_task(
        hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": "sensor.door_1_cloud_battery_level"},
            blocking=True,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=1)
    second = asyncio.create_task(
        hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": "sensor.door_2_cloud_battery_level"},
            blocking=True,
        )
    )
    try:
        await asyncio.wait_for(asyncio.shield(second), timeout=1)
        assert maximum_active == 1
    finally:
        release.set()
        await asyncio.gather(first, second)
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert maximum_active == 1
    assert (
        fetch.await_count <= 3
    )  # Initial fetch, manual fetch, at most one queued refresh.
    assert hass.states.get("sensor.door_1_cloud_battery_level").state == "40.0"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("_get_addresses", ()),
        ("_get_rooms_at_address", ({"id": 1},)),
        ("_get_devices_in_room", ({"id": 1},)),
    ],
)
@pytest.mark.parametrize(
    "response",
    [
        {"error": "Temporarily unavailable", "data": []},
        {"success": False, "data": []},
        {"code": 503, "data": []},
        {},
        {"data": None},
        {"data": {}},
        {"data": "unexpected"},
        {"data": [None]},
    ],
)
async def test_reject_failed_or_malformed_listings(method, args, response):
    """Every account listing rejects errors, including errors with empty data."""
    from custom_components.ultraloq_ble.utecio.api import InvalidResponse, UtecClient

    client = UtecClient("fixture", "fixture")
    client._post = AsyncMock(return_value=response)
    with pytest.raises(InvalidResponse):
        await getattr(client, method)(*args)
    assert client.addresses == client.rooms == client.devices == []


async def test_partial_cloud_failure_preserves_snapshot(
    hass, entry, integration, freezer
):
    """A late room failure must not publish a partial account snapshot as success."""
    from custom_components.ultraloq_ble.utecio.api import UtecClient

    def device(index, percent):
        return {
            "uuid": f"AA:BB:CC:DD:EE:0{index}",
            "params": {"battery_percent": percent},
        }

    with (
        patch.object(UtecClient, "connect", new_callable=AsyncMock),
        patch.object(
            UtecClient,
            "_post",
            new_callable=AsyncMock,
            side_effect=[
                {"data": [{"id": 1}]},
                {"data": [{"id": 10}, {"id": 11}]},
                {"data": [device(1, 75)]},
                {"data": [device(2, 80)]},
                {"data": [{"id": 1}]},
                {"data": [{"id": 10}, {"id": 11}]},
                {"data": [device(1, 40)]},
                {"error": "Temporarily unavailable", "data": []},
            ],
        ) as post,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        first = hass.states.get("sensor.door_1_cloud_battery_level")
        assert first.state == "75.0"
        timestamp = first.attributes["last_successful_cloud_fetch"]
        freezer.tick(timedelta(hours=6, seconds=1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)
        assert post.await_count == 8
        for index, percent in ((1, "75.0"), (2, "80.0")):
            state = hass.states.get(f"sensor.door_{index}_cloud_battery_level")
            assert state.state == percent
            assert state.attributes["last_successful_cloud_fetch"] == timestamp
            assert state.attributes["cloud_update_success"] is False
            assert state.attributes["cloud_battery_status"] == "percentage_valid"
            assert hass.states.get(f"sensor.door_{index}_battery_level").state == "HIGH"
        assert await hass.config_entries.async_unload(entry.entry_id)
