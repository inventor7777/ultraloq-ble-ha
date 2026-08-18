"""U-tec device capability definitions."""

import logging
from dataclasses import dataclass

logger = logging.getLogger("custom_components.ultraloq_ble.utecio")


@dataclass(frozen=True)
class DeviceDefinition:
    """BLE capabilities used by the Home Assistant integration."""

    autolock: bool = False
    passage: bool = False
    lockout: bool = False
    bt264: bool = False
    doorsensor: bool = False


LATCH_CAPABILITIES = DeviceDefinition(
    autolock=True, passage=True, lockout=True, bt264=True
)
DEADBOLT_CAPABILITIES = DeviceDefinition(autolock=True, lockout=True, bt264=True)
DOOR_DEADBOLT_CAPABILITIES = DeviceDefinition(
    autolock=True, lockout=True, bt264=True, doorsensor=True
)
LEGACY_CAPABILITIES = DeviceDefinition(passage=True, lockout=True)

known_devices: dict[str, DeviceDefinition] = {
    "Latch-5-F": LATCH_CAPABILITIES,
    "Latch-5-NFC": LATCH_CAPABILITIES,
    "UL1-BT": LEGACY_CAPABILITIES,
    "Bolt-NFC": DOOR_DEADBOLT_CAPABILITIES,
    "LEVER": LATCH_CAPABILITIES,
    "U-Bolt": DEADBOLT_CAPABILITIES,
    "U-Bolt-Pro": DEADBOLT_CAPABILITIES,
    "U-Bolt-WiFi": DOOR_DEADBOLT_CAPABILITIES,
    "U-Bolt-Pro-WiFi": DOOR_DEADBOLT_CAPABILITIES,
    "U-Bolt-ZWave": DOOR_DEADBOLT_CAPABILITIES,
    "U-Bolt-Pro-ZWave": DOOR_DEADBOLT_CAPABILITIES,
    "SmartLockByBle": LEGACY_CAPABILITIES,
    "UL3-2ND": LATCH_CAPABILITIES,
    "UL300": LEGACY_CAPABILITIES,
}

MODEL_ALIASES = {
    "U-Bolt Pro": "U-Bolt-Pro",
    "U-Bolt-PRO": "U-Bolt-Pro",
    "U-Bolt Pro WiFi": "U-Bolt-Pro-WiFi",
    "U-Bolt Pro ZWave": "U-Bolt-Pro-ZWave",
}


def canonical_model(model: str) -> str:
    """Return the canonical API model name."""

    return MODEL_ALIASES.get(model, model)
