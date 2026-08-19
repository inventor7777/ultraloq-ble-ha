"""Regression check that response payloads exclude CRC and AES padding."""

import ast
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/device.py"
).read_text()
module = ast.parse(source)
response = next(
    node
    for node in module.body
    if isinstance(node, ast.ClassDef) and node.name == "UtecBleResponse"
)
parameter = next(
    node
    for node in response.body
    if isinstance(node, ast.FunctionDef) and node.name == "_parameter"
)
data = next(
    node
    for node in response.body
    if isinstance(node, ast.FunctionDef) and node.name == "data"
)
is_valid = next(
    node
    for node in response.body
    if isinstance(node, ast.FunctionDef) and node.name == "is_valid"
)
read_response = next(
    node
    for node in response.body
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "_read_response"
)

namespace = {}
exec(compile(ast.Module([parameter], []), __file__, "exec"), namespace)


class Response:
    """Minimal response object for exercising payload extraction."""

    _parameter = namespace["_parameter"]


for data_len, frame, expected in (
    (4, "7f0400d30000fd0000", "00"),
    (10, "7f0a00c1004aab246a1a0002cb0000", "4aab246a1a0002"),
):
    parsed = Response()
    parsed.data_len = data_len
    parsed.buffer = bytearray.fromhex(frame)
    assert parsed._parameter(1).hex() == expected

assert "_parameter(1)" in ast.unparse(data)


class Command(Enum):
    LOCK_STATUS = 80


class ResponseCode(Enum):
    LOCK_STATUS = 208
    GET_BATTERY = 195


validation_namespace = {"BleResponseCode": ResponseCode}
exec(compile(ast.Module([is_valid], []), __file__, "exec"), validation_namespace)


class ValidationResponse:
    is_valid = validation_namespace["is_valid"]


validation = ValidationResponse()
validation.completed = True
validation.request = SimpleNamespace(command=Command.LOCK_STATUS)
validation.command = ResponseCode.LOCK_STATUS
assert validation.is_valid
validation.command = ResponseCode.GET_BATTERY
assert not validation.is_valid

failure_branch = next(
    node
    for node in ast.walk(read_response)
    if isinstance(node, ast.If) and ast.unparse(node.test) == "not self.success"
)
assert any(isinstance(node, ast.Return) for node in failure_branch.body)
assert "len(self.data) >= 2" in ast.unparse(read_response)
