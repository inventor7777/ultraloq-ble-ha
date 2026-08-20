"""Regression checks for read-only auto-lock sensors."""

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
assert 'key="autolock_mode"' in source
assert 'AUTOLOCK_MODES = {0: "Door Sensor", 1: "Immediate"}' in source
assert "AUTOLOCK_MODES.get(lock.autolock_mode)" in source
assert 'description.key.startswith("autolock_")' in source
assert "not lock.capabilities.autolock" in source
assert "class UltraloqAutolockSensor" in binary_source
assert 'super().__init__(lock, "autolock")' in binary_source
assert "self.lock.autolock_enabled is not None" in binary_source
assert "bool(self.lock.autolock_enabled)" in binary_source
