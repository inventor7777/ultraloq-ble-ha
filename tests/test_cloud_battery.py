"""Behavior checks for optional cloud polling without a Home Assistant install."""

import __future__

import ast
import asyncio
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).parents[1] / "custom_components/ultraloq_ble"


def load_definitions(filename, namespace, names=None):
    module = ast.parse((ROOT / filename).read_text())
    nodes = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and (names is None or node.name in names)
    ]
    exec(
        compile(
            ast.Module(nodes, []),
            filename,
            "exec",
            flags=__future__.annotations.compiler_flag,
        ),
        namespace,
    )


class UpdateFailed(Exception):
    """Stand-in for the coordinator's recoverable update exception."""


class InvalidCredentials(Exception):
    """Stand-in for the cloud client's authentication exception."""


class Coordinator:
    """Minimal HA coordinator boundary; scheduling is left to Home Assistant."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.update_interval = kwargs["update_interval"]
        self.listeners = []
        self.last_update_success = True

    async def async_refresh(self):
        try:
            self.data = await self._async_update_data()
        except (UpdateFailed, TimeoutError):
            self.last_update_success = False
        else:
            self.last_update_success = True

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)


class Entity:
    """Capture listener cleanup and state writes at the HA entity boundary."""

    async def async_added_to_hass(self):
        self.cleanup = []
        self.writes = 0

    def async_on_remove(self, callback):
        self.cleanup.append(callback)

    def async_write_ha_state(self):
        self.writes += 1


namespace = {
    "asyncio": asyncio,
    "UTC": UTC,
    "datetime": datetime,
    "timedelta": timedelta,
    "LOGGER": logging.getLogger(__name__),
    "DataUpdateCoordinator": Coordinator,
    "UpdateFailed": UpdateFailed,
    "InvalidCredentials": InvalidCredentials,
    "CONF_EMAIL": "email",
    "CONF_PASSWORD": "password",
    "Entity": Entity,
    "callback": lambda function: function,
    "SensorEntity": Entity,
    "SensorDeviceClass": SimpleNamespace(BATTERY="battery"),
    "EntityCategory": SimpleNamespace(DIAGNOSTIC="diagnostic"),
    "PERCENTAGE": "%",
}
constants = ast.parse((ROOT / "const.py").read_text())
for node in constants.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name.startswith(("CONF_", "DEFAULT_")) or name in (
            "DOMAIN",
            "UTEC_LOCKDATA",
        ):
            namespace[name] = ast.literal_eval(node.value)
load_definitions("coordinator.py", namespace)
load_definitions("entity.py", namespace)
load_definitions(
    "sensor.py", namespace, {"UltraloqCloudBatterySensor", "async_setup_entry"}
)
parse = namespace["_battery_percent"]
for value in (0, 1, 52.5, 100, "75", "0"):
    assert parse(value) == float(value)
for value in (None, -99, -1, 101, "", "bad", "nan", "inf", True, False, {}, []):
    assert parse(value) is None, value


async def check_cloud_battery():
    fetch = AsyncMock(
        return_value=[
            {"uuid": "aa:01", "params": {"battery_percent": "75"}},
            {"uuid": "aa:02", "params": {"battery_percent": 0}},
            {"uuid": "aa:03", "params": {"battery_percent": -99}},
            {"uuid": "aa:04", "params": None},
            {"name": "Smart plug", "model": "UP01"},
            None,
        ]
    )
    namespace["async_fetch_api_devices"] = fetch
    entry = SimpleNamespace(data={"email": "test", "password": "fixture"}, options={})
    cloud = namespace["CloudBatteryCoordinator"](object(), entry)
    assert cloud.update_interval == timedelta(hours=12)
    await cloud.async_refresh()
    assert fetch.await_count == 1
    assert cloud.data == {"AA:01": 75, "AA:02": 0, "AA:03": None, "AA:04": None}
    assert cloud.battery_status == {
        "AA:01": "percentage_valid",
        "AA:02": "percentage_valid",
        "AA:03": "percentage_invalid",
        "AA:04": "percentage_missing",
    }
    timestamp = cloud.last_successful_fetch
    assert timestamp.tzinfo is UTC

    lock = SimpleNamespace(mac_uuid="aa:01", lock_status=-1, _ha_available=False)
    sensor = namespace["UltraloqCloudBatterySensor"](lock, cloud)
    assert sensor._attr_name == "Cloud Battery Level"
    assert sensor._attr_icon == "mdi:battery-plus-variant"
    assert sensor._attr_unique_id == "ul_aa:01_cloud_battery_level"
    assert sensor.available and sensor.native_value == 75
    assert sensor.extra_state_attributes["cloud_battery_status"] == "percentage_valid"
    await sensor.async_added_to_hass()
    assert not lock._ha_state_callbacks
    assert len(cloud.listeners) == 1
    cloud.listeners[0]()
    assert sensor.writes == 1

    for failure in (ConnectionError(), InvalidCredentials(), TimeoutError()):
        fetch.side_effect = failure
        await cloud.async_refresh()
        assert sensor.available and sensor.native_value == 75
        assert cloud.last_successful_fetch == timestamp
        assert sensor.extra_state_attributes["cloud_update_success"] is False
        assert (
            sensor.extra_state_attributes["cloud_battery_status"] == "percentage_valid"
        )
        assert lock.lock_status == -1 and lock._ha_available is False
    fetch.side_effect = None
    fetch.return_value = {"unexpected": "response"}
    await cloud.async_refresh()
    assert not cloud.last_update_success and sensor.native_value == 75
    fetch.return_value = [{"uuid": "aa:01", "params": {"battery_percent": -99}}]
    await cloud.async_refresh()
    assert cloud.last_update_success and sensor.native_value is None
    assert sensor.extra_state_attributes["cloud_battery_status"] == "percentage_invalid"
    fetch.return_value = [{"uuid": "aa:01", "params": {}}]
    await cloud.async_refresh()
    assert sensor.extra_state_attributes["cloud_battery_status"] == "percentage_missing"
    fetch.return_value = []
    await cloud.async_refresh()
    assert (
        sensor.extra_state_attributes["cloud_battery_status"] == "device_not_returned"
    )
    sensor.cleanup[0]()
    assert not cloud.listeners

    # Both the default opt-out and an explicit local-only entry make no requests.
    namespace["SENSORS"] = (SimpleNamespace(key="battery_level"),)
    namespace["UltraloqSensor"] = lambda lock, description: SimpleNamespace(lock=lock)
    hass = SimpleNamespace(data={"ultraloq_ble": {"test": {"utec_data": [lock, lock]}}})
    entry.entry_id = "test"
    background_tasks = []

    def create_background_task(hass, coroutine, name):
        task = asyncio.create_task(coroutine, name=name)
        background_tasks.append(task)
        return task

    entry.async_create_background_task = create_background_task
    setup = namespace["async_setup_entry"]
    for data, options in (
        (entry.data, {}),
        ({**entry.data, "cloud_access": False}, {"cloud_battery": True}),
    ):
        fetch.reset_mock()
        entry.data, entry.options = data, options
        entities = []
        await setup(hass, entry, entities.extend)
        assert len(entities) == 2
        fetch.assert_not_awaited()

    entry.data = {"email": "test", "password": "fixture"}
    entry.options = {"cloud_battery": True, "cloud_battery_interval": 24}
    fetch.side_effect = ConnectionError()
    entities = []
    await setup(hass, entry, entities.extend)
    assert len(entities) == 4  # BLE and cloud battery for both locks, despite outage.
    fetch.assert_not_awaited()
    await asyncio.gather(*background_tasks)
    fetch.assert_awaited_once()
    assert entities[1].coordinator is entities[3].coordinator
    assert entities[1].coordinator.update_interval == timedelta(hours=24)
    assert entities[1].native_value is None and entities[1].available

    fetch.reset_mock()
    hass.data["ultraloq_ble"]["test"]["utec_data"] = []
    entities = []
    await setup(hass, entry, entities.extend)
    assert not entities
    fetch.assert_not_awaited()


asyncio.run(check_cloud_battery())


class OptionsFlow:
    """Capture the options schema without the Home Assistant UI."""

    def async_show_form(self, **kwargs):
        return kwargs["data_schema"]

    def async_create_entry(self, **kwargs):
        return kwargs["data"]


namespace["config_entries"] = SimpleNamespace(OptionsFlow=OptionsFlow)
namespace["CONF_SCAN_INTERVAL"] = "scan_interval"
namespace["cv"] = SimpleNamespace(boolean=bool)
namespace["vol"] = SimpleNamespace(
    Optional=lambda key, default: key,
    All=lambda *validators: validators,
    Coerce=lambda validator: validator,
    Range=lambda **kwargs: kwargs,
    In=lambda choices: choices,
    Schema=lambda schema: schema,
)
load_definitions("config_flow.py", namespace, {"UltraloqOptionsFlowHandler"})


async def check_options():
    entry = SimpleNamespace(data={}, options={})
    flow = namespace["UltraloqOptionsFlowHandler"](entry)
    schema = await flow.async_step_init()
    assert schema["cloud_battery"] is bool
    assert schema["cloud_battery_interval"][1] == [6, 12, 24]
    entry.data["cloud_access"] = False
    schema = await flow.async_step_init()
    assert "cloud_battery" not in schema
    assert "cloud_battery_interval" not in schema


asyncio.run(check_options())
