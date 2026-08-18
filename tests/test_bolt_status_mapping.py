"""Regression check for the legacy bolt-status debug mapping."""

from pathlib import Path


sensor_source = (Path(__file__).parents[1] / "custom_components/ultraloq_ble/sensor.py").read_text()
lock_source = (Path(__file__).parents[1] / "custom_components/ultraloq_ble/lock.py").read_text()

assert "DeviceLockStatus(lock.bolt_status).name" in sensor_source
assert '"bolt_status": DeviceLockStatus(self.lock.bolt_status).name' in lock_source
