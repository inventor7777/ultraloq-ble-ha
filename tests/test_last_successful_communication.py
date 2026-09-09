"""Regression check for the last successful communication sensor."""

from pathlib import Path

root = Path(__file__).parents[1] / "custom_components/ultraloq_ble"
device_source = (root / "utecio/ble/device.py").read_text()
sensor_source = (root / "sensor.py").read_text()

assert "self.last_successful_communication: datetime.datetime | None = None" in device_source
assert "datetime.datetime.now(\n                datetime.UTC\n            )" in device_source
assert 'key="last_successful_communication"' in sensor_source
assert "SensorDeviceClass.TIMESTAMP" in sensor_source
assert "entity_category=EntityCategory.DIAGNOSTIC" in sensor_source
assert "value_fn=lambda lock: lock.last_successful_communication" in sensor_source
assert 'self.entity_description.key == "last_successful_communication"' in sensor_source
