"""Regression checks for Ultraloq's packed device timestamp."""

import datetime
import importlib.util
from pathlib import Path

path = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/util.py"
)
spec = importlib.util.spec_from_file_location("utecio_util", path)
util = importlib.util.module_from_spec(spec)
spec.loader.exec_module(util)

device_time = datetime.datetime(2018, 9, 21, 18, 17, 42)
payload = util.date_to_4bytes(device_time)
assert payload.hex() == "4aab246a"
assert util.date_from_4bytes(payload) == device_time

try:
    util.date_to_4bytes(datetime.datetime(1999, 1, 1))
except ValueError:
    pass
else:
    raise AssertionError("Out-of-range years must be rejected")
