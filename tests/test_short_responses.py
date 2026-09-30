"""Regression checks for locks that send short LOCK_STATUS and GET_AUTOLOCK data."""

import ast
from pathlib import Path
import runpy

root = Path(__file__).parents[1]
source = (root / "custom_components/ultraloq_ble/utecio/ble/device.py").read_text()
module = ast.parse(source)
response_source = ast.unparse(
    next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "UtecBleResponse"
    )
)

# GET_AUTOLOCK may contain only time, or append enabled and mode independently.
parse_autolock_response = runpy.run_path(
    root / "custom_components/ultraloq_ble/utecio/util.py"
)["parse_autolock_response"]
assert parse_autolock_response(bytes.fromhex("0000")) == (0, False, -1)
assert parse_autolock_response(bytes.fromhex("1e00")) == (30, True, -1)
assert parse_autolock_response(bytes.fromhex("1e0000")) == (30, False, -1)
assert parse_autolock_response(bytes.fromhex("1e000001")) == (30, False, 1)
try:
    parse_autolock_response(bytes.fromhex("00"))
except ValueError:
    pass
else:
    raise AssertionError("GET_AUTOLOCK must reject responses shorter than 2 bytes")

# LOCK_STATUS may stop after battery and lock mode.
assert "if len(data) >= 3:" in response_source
assert "self.device.lock_status_has_mute = len(data) >= 5" in response_source
