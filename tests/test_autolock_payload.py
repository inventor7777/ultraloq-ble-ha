"""Regression checks for auto-lock payload construction."""

import ast
from pathlib import Path

source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/lock.py"
).read_text()
module = ast.parse(source)
functions = {
    node.name: node
    for node in module.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {"build_autolock_payload", "parse_autolock_hex"}
}
namespace = {"to_byte_array": lambda value, length: value.to_bytes(length, "little")}
exec(compile(ast.Module(list(functions.values()), []), __file__, "exec"), namespace)

build = namespace["build_autolock_payload"]
parse = namespace["parse_autolock_hex"]

assert build(60, True, True).hex() == "3c0000"
assert build(300, False, True).hex() == "2c0101"
assert build(300, False, False).hex() == "000000"
assert parse("0x3c0000").hex() == "3c0000"

for invalid in ("", "not hex"):
    try:
        parse(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid manual payload: {invalid!r}")
