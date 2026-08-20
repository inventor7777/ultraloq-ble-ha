"""Regression check for the lock-status settle delay."""

from pathlib import Path

root = Path(__file__).parents[1] / "custom_components/ultraloq_ble"
assert "STATUS_SETTLE_SECONDS = 2" in (root / "utecio/ble/lock.py").read_text()

lock_source = (root / "lock.py").read_text()
assert "was_available = self.lock._ha_available" in lock_source
assert "if not was_available:" in lock_source
assert "self._unavailable_callback, address, connectable=True" in lock_source
