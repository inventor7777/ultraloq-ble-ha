"""Regression check for non-fatal BLE notification cleanup."""

import ast
from pathlib import Path


module = ast.parse(
    (
        Path(__file__).parents[1]
        / "custom_components/ultraloq_ble/utecio/ble/device.py"
    ).read_text()
)
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
cleanup = get_response.body[-1].finalbody[0]

assert isinstance(cleanup, ast.Try)
assert cleanup.handlers
