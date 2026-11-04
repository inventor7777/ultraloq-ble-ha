"""Zero percent is only trusted when BLE reports Low or Critical."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ultraloq_ble.sensor import UltraloqCloudBatterySensor
from custom_components.ultraloq_ble.utecio.enums import DeviceBatteryLevel as L


def make(pct, ble):
    lock = SimpleNamespace(mac_uuid="aa:01", name="Crawl", model="U-Bolt-PRO", sn="1",
                           battery=ble, lock_status=2, _ha_available=True, _ha_state_callbacks=[])
    coord = MagicMock()
    coord.data = {"AA:01": pct}
    coord.battery_status = {"AA:01": "percentage_valid"}
    coord.last_successful_fetch = None
    coord.last_update_success = True
    return UltraloqCloudBatterySensor(lock, coord)


def test_zero_rule():
    for ble in (L.HIGH.value, L.MEDIUM.value, L.NOTSET.value):
        s = make(0.0, ble)
        assert s.native_value is None
        assert s.extra_state_attributes["cloud_battery_status"] == "percentage_zero_unconfirmed"
    for ble in (L.LOW.value, L.CRITICAL.value):
        s = make(0.0, ble)
        assert s.native_value == 0.0
        assert s.extra_state_attributes["cloud_battery_status"] == "percentage_valid"
    s = make(54.0, L.MEDIUM.value)
    assert s.native_value == 54.0
    assert s.extra_state_attributes["cloud_battery_status"] == "percentage_valid"
    assert not s.lock._ha_state_callbacks  # still no BLE subscription
