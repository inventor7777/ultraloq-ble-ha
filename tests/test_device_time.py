"""Regression checks for Ultraloq's packed device timestamp."""

import ast
import datetime
import importlib.util
from pathlib import Path

path = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/util.py"
)
spec = importlib.util.spec_from_file_location("utecio_util", path)
util = importlib.util.module_from_spec(spec)
spec.loader.exec_module(util)

device_time = datetime.datetime(2018, 10, 21, 18, 17, 42)
read_payload = bytes.fromhex("4aab246a")
assert util.date_from_4bytes(read_payload) == device_time
assert util.date_to_4bytes(device_time).hex() == "6a24ab4a"
assert (
    util.date_to_4bytes(datetime.datetime(2026, 8, 18, 11, 7, 47)).hex()
    == "efb1246a"
)

try:
    util.date_to_4bytes(datetime.datetime(1999, 1, 1))
except ValueError:
    pass
else:
    raise AssertionError("Out-of-range years must be rejected")

device_source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/device.py"
).read_text()
device_module = ast.parse(device_source)
request = next(
    node
    for node in device_module.body
    if isinstance(node, ast.ClassDef) and node.name == "UtecBleRequest"
)
request_init = next(
    node
    for node in request.body
    if isinstance(node, ast.FunctionDef) and node.name == "__init__"
)
assert "WRITE_TIME" in ast.unparse(request_init)
assert "{BLECommandCode.REBOOT, BLECommandCode.WRITE_TIME}" in device_source
