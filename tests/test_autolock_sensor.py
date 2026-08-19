"""Regression check for the read-only auto-lock sensor."""

from pathlib import Path

source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/sensor.py"
).read_text()
binary_source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/binary_sensor.py"
).read_text()

assert 'key="autolock_time"' in source
assert "SensorDeviceClass.DURATION" in source
assert "UnitOfTime.SECONDS" in source
assert "suggested_display_precision=0" in source
assert (
    'if description.key == "autolock_time" and not lock.capabilities.autolock' in source
)
assert "class UltraloqAutolockSensor" in binary_source
assert 'super().__init__(lock, "autolock")' in binary_source
assert "self.lock.autolock_enabled is not None" in binary_source
assert "bool(self.lock.autolock_enabled)" in binary_source
