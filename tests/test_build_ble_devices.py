"""Regression check for accounts containing both locks and smart plugs."""

import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

source = (
    Path(__file__).parents[1] / "custom_components/ultraloq_ble/utecio/api.py"
).read_text()
builder = next(
    node
    for node in ast.parse(source).body
    if isinstance(node, ast.FunctionDef) and node.name == "build_ble_devices"
)

lock_record = {
    "name": "Front door",
    "model": "U-Bolt-Pro",
    "user": {"uid": "1", "password": "fixture"},
}
plug_record = {"name": "Lamp", "model": "UP01"}
lock = SimpleNamespace(model="U-Bolt-Pro", capabilities=SimpleNamespace(bluetooth=True))
constructor = Mock(return_value=lock)
namespace = {
    "Any": object,
    "UtecBleLock": SimpleNamespace(from_json=constructor),
    "logger": logging.getLogger(__name__),
    "canonical_model": lambda model: model,
    "known_devices": {"U-Bolt-Pro"},
}
exec(compile(ast.Module([builder], []), __file__, "exec"), namespace)

assert namespace["build_ble_devices"]([plug_record, lock_record]) == [lock]
constructor.assert_called_once_with(lock_record)
