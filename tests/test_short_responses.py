"""Regression checks for locks that send short LOCK_STATUS and GET_AUTOLOCK data."""

import ast
from pathlib import Path

source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/ble/device.py"
).read_text()
module = ast.parse(source)
response_source = ast.unparse(
    next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "UtecBleResponse"
    )
)

# GET_AUTOLOCK may be only the 2-byte time; enabled falls back to time > 0.
assert "expected at least 2" in response_source
assert "self.device.autolock_enabled = self.device.autolock_time > 0" in response_source

# LOCK_STATUS may stop after battery and lock mode.
assert "if len(data) >= 3:" in response_source
assert "self.device.lock_status_has_mute = len(data) >= 5" in response_source
