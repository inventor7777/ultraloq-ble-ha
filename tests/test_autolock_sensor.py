"""Regression check for the read-only auto-lock sensor."""

from pathlib import Path

source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/sensor.py"
).read_text()

assert 'key="autolock_time"' in source
assert "SensorDeviceClass.DURATION" in source
assert "UnitOfTime.SECONDS" in source
assert (
    'if description.key == "autolock_time" and not lock.capabilities.autolock' in source
)
