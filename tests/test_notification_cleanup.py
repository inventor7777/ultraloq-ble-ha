"""Regression check for one DATA notification subscription per connection."""

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
send_requests = next(
    node
    for node in device.body
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "send_requests"
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
assert "start_notify" in ast.unparse(send_requests)
assert "stop_notify" in ast.unparse(send_requests)
assert "start_notify" not in ast.unparse(get_response)
assert "stop_notify" not in ast.unparse(get_response)
assert "response=False" in ast.unparse(get_response)
assert "Could not stop data notifications" in source
