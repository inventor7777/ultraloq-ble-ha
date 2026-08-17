"""Regression check for non-fatal BLE notification cleanup."""

import ast
from pathlib import Path


source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/device.py"
).read_text()
module = ast.parse(source)
request = next(
    node
    for node in module.body
    if isinstance(node, ast.ClassDef) and node.name == "UtecBleRequest"
)
get_response = next(
    node
    for node in request.body
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "_get_response"
)
cleanup = next(
    node for node in get_response.body[-1].finalbody if isinstance(node, ast.Try)
)

assert isinstance(cleanup, ast.Try)
assert cleanup.handlers
assert "Stopping notifications for %s" in source
assert "Could not stop notifications for %s" in source
assert "Notifications stopped for %s" in source
