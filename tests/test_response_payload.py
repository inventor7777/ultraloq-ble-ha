"""Regression check that response payloads exclude CRC and AES padding."""

import ast
from pathlib import Path

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
