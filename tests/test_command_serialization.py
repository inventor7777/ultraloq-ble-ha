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

request = next(
    node
    for node in module.body
    if isinstance(node, ast.ClassDef) and node.name == "UtecBleRequest"
)
request_init = next(
    node
    for node in request.body
    if isinstance(node, ast.FunctionDef) and node.name == "__init__"
)
auth_commands = next(
    node
    for node in ast.walk(request_init)
    if isinstance(node, ast.Set)
    and any("ADMIN_LOGIN" in ast.unparse(item) for item in node.elts)
)
assert all("SET_AUTOLOCK" not in ast.unparse(item) for item in auth_commands.elts)

lock_source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/lock.py"
).read_text()
assert "\n                if self.capabilities.mutemode:\n" in lock_source
assert "UtecBleRequest(BLECommandCode.GET_AUTOLOCK)" in lock_source

response_source = ast.unparse(
    next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "UtecBleResponse"
    )
)
assert "self.device.autolock_enabled = bool(data[2])" in response_source
assert "self.device.autolock_mode = int(data[3])" in response_source
assert "if len(data) >= 5" in response_source
