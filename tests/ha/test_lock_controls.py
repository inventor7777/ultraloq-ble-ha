"""Firmware-derived protocol fixtures and HA mute/identification entities."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from custom_components.ultraloq_ble.binary_sensor import UltraloqAutolockSensor
from custom_components.ultraloq_ble.const import CONF_API_DEVICES, DOMAIN
from custom_components.ultraloq_ble.sensor import SENSORS, UltraloqSensor
from custom_components.ultraloq_ble.utecio import known_devices
from custom_components.ultraloq_ble.utecio.ble.device import (
    UtecBleDeviceError,
    UtecBleRequest,
    UtecBleResponse,
)
from custom_components.ultraloq_ble.utecio.ble.lock import UtecBleLock
from custom_components.ultraloq_ble.utecio.enums import (
    BLECommandCode,
    DeviceLockWorkMode,
)
from custom_components.ultraloq_ble.utecio.util import (
    parse_autolock_response,
    parse_model_response,
)
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def make_lock(model="U-Bolt-PRO"):
    lock = UtecBleLock(
        "4026531840", "123456", "AA:BB:CC:DD:EE:01", "Front Door", device_model=model
    )
    lock.lock_status = 2
    return lock


def response(lock, command, payload=b"", status=0):
    request = UtecBleRequest(command, data=b"\x01")
    parsed = UtecBleResponse(request, lock)
    # Payload includes status; the final placeholder is CRC, never parser data.
    length = len(payload) + 3
    parsed.buffer = bytearray(
        b"\x7f"
        + length.to_bytes(2, "little")
        + bytes([command.value ^ 0x80, status])
        + payload
        + b"\0\0"
    )
    return parsed


@pytest.mark.parametrize("model", [*known_devices, "U-Bolt-PRO", "Unknown Model"])
async def test_work_mode_framing_and_status_only_ack(model):
    lock = make_lock(model)
    packets = []

    async def send(continue_on_error=False):
        packets.extend(lock._requests)
        return True

    lock.send_requests = AsyncMock(side_effect=send)
    await lock.async_set_workmode(DeviceLockWorkMode.PASSAGE)
    assert packets[0].command is BLECommandCode.ADMIN_LOGIN
    assert len(packets[0].package[4:-1]) == 8
    write = packets[1]
    assert write.command is (
        BLECommandCode.SET_LOCK_STATUS
        if lock.capabilities.bt264
        else BLECommandCode.SET_WORK_MODE
    )
    assert len(write.package[4:-1]) == (1 if lock.capabilities.bt264 else 9)
    assert write.package[-2] == 1
    if lock.capabilities.bt264:
        parsed = response(lock, BLECommandCode.SET_LOCK_STATUS)
        await parsed._read_response()
        assert lock.lock_mode == 1
    for command in (BLECommandCode.UNLOCK, BLECommandCode.BOLT_LOCK):
        request = UtecBleRequest(command)
        lock.add_request(request)
        assert len(request.package[4:-1]) == 8


@pytest.mark.parametrize(
    "payload,expected",
    [
        ("3c000001", (60, None, 0)),
        ("3c000100", (60, None, 1)),
        ("00000001", (0, None, 0)),
        ("3c00", (60, None, -1)),
    ],
)
def test_bt264_autolock_fields(payload, expected):
    assert parse_autolock_response(bytes.fromhex(payload), bt264=True) == expected
    # Preserve non-bt264 models' existing response layout.
    assert parse_autolock_response(bytes.fromhex("3c000001")) == (60, False, 1)


async def test_identification_and_autolock_responses():
    lock = make_lock()
    await response(
        lock, BLECommandCode.GET_MODEL, b"U-Bolt\0\0" + b"02.28.0020"
    )._read_response()
    assert (lock.reported_model, lock.firmware_version) == ("U-Bolt", "02.28.0020")
    assert lock.model == "U-Bolt-PRO"  # Keep the canonical capability identity.
    await response(
        lock, BLECommandCode.GET_AUTOLOCK, bytes.fromhex("3c000001")
    )._read_response()
    assert (lock.autolock_time, lock.autolock_enabled, lock.autolock_mode) == (
        60,
        None,
        0,
    )
    assert not UltraloqAutolockSensor(lock).available
    lock._ha_available = False
    for description in SENSORS:
        if description.key in {"model", "firmware_version"}:
            assert UltraloqSensor(lock, description).available


@pytest.mark.parametrize("model", [*known_devices, "U-Bolt-PRO", "Unknown Model"])
async def test_autolock_response_layout_by_capability(model):
    lock = make_lock(model)
    await response(
        lock, BLECommandCode.GET_AUTOLOCK, bytes.fromhex("3c000001")
    )._read_response()
    expected = (60, None, 0) if lock.capabilities.bt264 else (60, False, 1)
    assert (lock.autolock_time, lock.autolock_enabled, lock.autolock_mode) == expected


@pytest.mark.parametrize(
    "payload", [b"", b"U-Bolt\0\0", b"U-Bolt\0\0nonsense!!", b"\xff" * 18]
)
def test_invalid_identification(payload):
    with pytest.raises(ValueError):
        parse_model_response(payload)


async def test_mute_sequence_and_confirmation():
    lock = make_lock()
    packets = []

    async def send(continue_on_error=False):
        packets.extend(lock._requests)
        await response(lock, BLECommandCode.GET_MUTE, b"\x01")._read_response()
        return True

    lock.send_requests = AsyncMock(side_effect=send)
    await lock.async_set_mute(True)
    assert [p.command for p in packets] == [
        BLECommandCode.ADMIN_LOGIN,
        BLECommandCode.SET_MUTE,
        BLECommandCode.GET_MUTE,
    ]
    assert packets[1].package[4:-1] == b"\x01"
    assert lock.mute
    with pytest.raises(UtecBleDeviceError, match="confirm"):
        await lock.async_set_mute(False)


async def test_identification_failure_does_not_fail_status_poll():
    lock = make_lock()
    lock.execute_requests = AsyncMock(
        side_effect=[True, UtecBleDeviceError("unsupported"), True]
    )
    assert await lock.async_update_status()
    assert await lock.async_update_status()
    assert lock.execute_requests.await_count == 3


async def test_ha_entities_and_mute_failure(hass):
    lock = make_lock()
    lock.reported_model = "U-Bolt"
    lock.firmware_version = "02.28.0020"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"email": "fixture", "password": "fixture", CONF_API_DEVICES: []},
    )
    entry.add_to_hass(hass)
    mock_integration(
        hass, MockModule("bluetooth_adapters", async_setup=AsyncMock(return_value=True))
    )
    with (
        patch(
            "custom_components.ultraloq_ble.PLATFORMS",
            [Platform.SENSOR, Platform.SWITCH],
        ),
        patch("custom_components.ultraloq_ble._build_ble_devices", return_value=[lock]),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.front_door_model").state == "U-Bolt"
        assert (
            hass.states.get("sensor.front_door_firmware_version").state == "02.28.0020"
        )
        assert (
            hass.states.get("switch.front_door_mute").attributes["icon"]
            == "mdi:volume-mute"
        )

        async def set_mute(value):
            lock.mute = value

        lock.async_set_mute = AsyncMock(side_effect=set_mute)
        for service, expected in [("turn_on", "on"), ("turn_off", "off")]:
            await hass.services.async_call(
                "switch",
                service,
                {"entity_id": "switch.front_door_mute"},
                blocking=True,
            )
            assert hass.states.get("switch.front_door_mute").state == expected
        lock.async_set_mute.side_effect = UtecBleDeviceError("rejected")
        with pytest.raises(HomeAssistantError, match="Failed to set mute"):
            await hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": "switch.front_door_mute"},
                blocking=True,
            )
        assert hass.states.get("switch.front_door_mute").state == "off"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert lock._ha_state_callbacks == []
