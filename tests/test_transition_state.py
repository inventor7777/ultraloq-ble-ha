"""Regression check for the lock-status settle delay."""

from pathlib import Path

assert (
    "STATUS_SETTLE_SECONDS = 2"
    in (
        Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/lock.py"
    ).read_text()
)
