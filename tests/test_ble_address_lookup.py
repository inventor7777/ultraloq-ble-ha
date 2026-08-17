"""Regression check for rejecting the wake receiver as the main lock."""

import ast
from pathlib import Path


module = ast.parse(
    (
        Path(__file__).parents[1]
        / "custom_components/ultraloq_ble/utecio/ble/device.py"
    ).read_text()
)
device = next(
    node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "UtecBleDevice"
)
lookup = next(
    node for node in device.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "_get_bledevice"
)

assert any(
    isinstance(node, ast.If)
    and "device.address" in ast.unparse(node.test)
    and any(
        isinstance(child, ast.Return)
        and isinstance(child.value, ast.Constant)
        and child.value.value is None
        for child in node.body
    )
    for node in ast.walk(lookup)
)
