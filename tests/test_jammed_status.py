"""Regression check for the observed Ultraloq jammed status."""

from pathlib import Path

root = Path(__file__).parents[1]
assert (
    "JAMMED = 3"
    in (root / "custom_components/ultraloq_ble/utecio/enums.py").read_text()
)
assert (
    "self._attr_is_jammed = True"
    in (root / "custom_components/ultraloq_ble/lock.py").read_text()
)
