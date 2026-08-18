"""Regression check for the Ultraloq door contact sensor."""

from pathlib import Path


source = (Path(__file__).parents[1] / "custom_components/ultraloq_ble/binary_sensor.py").read_text()
const_source = (Path(__file__).parents[1] / "custom_components/ultraloq_ble/const.py").read_text()
sensor_source = (Path(__file__).parents[1] / "custom_components/ultraloq_ble/sensor.py").read_text()
assert "BinarySensorDeviceClass.DOOR" in source
assert "if lock.capabilities.doorsensor" in source
assert "def is_on(self) -> bool | None" in source
assert "self.lock.bolt_status == 0" in source
assert "Platform.BINARY_SENSOR" in const_source
assert 'key="bolt_status"' not in sensor_source
