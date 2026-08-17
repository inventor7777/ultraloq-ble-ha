"""Regression check for atomic Ultraloq command sequences."""

import ast
from pathlib import Path


source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/device.py"
).read_text()
module = ast.parse(source)
device = next(
    node
    for node in module.body
    if isinstance(node, ast.ClassDef) and node.name == "UtecBleDevice"
)
execute = next(
    node
    for node in device.body
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute_requests"
)

implementation = ast.unparse(execute)

assert "wait_for" in implementation
assert "COMMAND_LOCK_TIMEOUT_SECONDS" in implementation
assert "send_requests" in implementation
