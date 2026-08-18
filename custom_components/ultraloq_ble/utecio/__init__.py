"""U-tec device capability definitions."""

import logging
from dataclasses import asdict, dataclass, field
from typing import ClassVar

logger = logging.getLogger("custom_components.ultraloq_ble.utecio")


@dataclass
class DeviceDefinition:
    """Capabilities reported for one U-tec device model."""

    model: str = ""
    lock: bool = False
    door: bool = False
    keypad: bool = False
    fingprinter: bool = False
    doublefp: bool = False
    bluetooth: bool = False
    rfid: bool = False
    rfid_once: bool = False
    rfid_twice: bool = False
    autobolt: bool = False
    autolock: bool = False
    autounlock: bool = False
    direction: bool = False
    update_ota: bool = False
    update_oad: bool = False
    update_wifi: bool = False
    alerts: bool = False
    mutemode: bool = False
    passage: bool = False
    lockout: bool = False
    manual: bool = False
    shakeopen: bool = False
    moreadmin: bool = False
    morepwd: bool = False
    timelimit: bool = False
    morelanguage: bool = False
    needregristerpwd: bool = False
    locklocal: bool = False
    havesn: bool = False
    clone: bool = False
    customuserid: bool = False
    bt264: bool = False
    keepalive: bool = False
    passageautolock: bool = False
    doorsensor: bool = False
    zwave: bool = False
    needreadmodel: bool = False
    needsycbuser: bool = False
    bt_close: bool = False
    singlelatchboltmortic: bool = False
    smartphone_nfc: bool = False
    update_2642: bool = False
    isautodirection: bool = False
    ishomekit: bool = False
    isyeeuu: bool = False
    secondsarray: list = field(default_factory=list)
    mtimearray: list = field(default_factory=list)
    adduserremovenum: int = 4


def _capabilities(*enabled: str, adduserremovenum: int = 4) -> DeviceDefinition:
    """Build a checked capability record from enabled field names."""

    return DeviceDefinition(
        **dict.fromkeys(enabled, True), adduserremovenum=adduserremovenum
    )


known_devices: dict[str, DeviceDefinition] = {
    "Latch-5-F": _capabilities(
        "bluetooth", "autolock", "update_wifi", "alerts", "mutemode",
        "doublefp", "keypad", "fingprinter", "needregristerpwd", "havesn",
        "moreadmin", "timelimit", "passage", "lockout", "bt264", "keepalive",
        "passageautolock", "singlelatchboltmortic", "smartphone_nfc", "bt_close",
    ),
    "Latch-5-NFC": _capabilities(
        "bluetooth", "autolock", "update_wifi", "alerts", "mutemode", "rfid",
        "rfid_twice", "keypad", "needregristerpwd", "havesn", "moreadmin",
        "timelimit", "passage", "lockout", "bt264", "keepalive",
        "passageautolock", "singlelatchboltmortic", "smartphone_nfc", "bt_close",
    ),
    "UL1-BT": _capabilities(
        "bluetooth", "rfid", "rfid_twice", "fingprinter", "autobolt",
        "update_ota", "update_oad", "alerts", "shakeopen", "mutemode",
        "passage", "lockout", "havesn", "direction", "keepalive",
        "singlelatchboltmortic",
    ),
    "Bolt-NFC": _capabilities(
        "lock", "bluetooth", "autolock", "update_ota", "update_wifi",
        "direction", "alerts", "mutemode", "manual", "shakeopen", "havesn",
        "rfid", "keypad", "needregristerpwd", "timelimit", "moreadmin",
        "lockout", "bt264", "doorsensor", "keepalive", "autounlock",
        "smartphone_nfc", "update_2642", "isautodirection", "ishomekit",
    ),
    "LEVER": _capabilities(
        "bluetooth", "autolock", "update_ota", "alerts", "mutemode",
        "shakeopen", "fingprinter", "keypad", "doublefp", "needregristerpwd",
        "havesn", "moreadmin", "timelimit", "passage", "lockout", "bt264",
        "keepalive", "passageautolock", "singlelatchboltmortic",
    ),
    "U-Bolt": _capabilities(
        "lock", "bluetooth", "autolock", "autounlock", "update_ota",
        "direction", "alerts", "mutemode", "manual", "shakeopen", "havesn",
        "moreadmin", "needreadmodel", "keypad", "lockout", "timelimit",
        "needregristerpwd", "bt264", "keepalive",
    ),
    "U-Bolt-Pro": _capabilities(
        "lock", "bluetooth", "autolock", "autounlock", "update_ota",
        "direction", "alerts", "mutemode", "manual", "shakeopen", "havesn",
        "moreadmin", "needreadmodel", "keypad", "fingprinter", "lockout",
        "timelimit", "needregristerpwd", "bt264", "keepalive",
    ),
    "U-Bolt-WiFi": _capabilities(
        "lock", "bluetooth", "autolock", "update_ota", "update_wifi",
        "direction", "alerts", "mutemode", "manual", "shakeopen", "havesn",
        "needreadmodel", "keypad", "needregristerpwd", "timelimit", "moreadmin",
        "lockout", "bt264", "doorsensor", "keepalive", "autounlock",
    ),
    "U-Bolt-Pro-WiFi": _capabilities(
        "lock", "bluetooth", "autolock", "autounlock", "update_ota",
        "update_wifi", "direction", "alerts", "mutemode", "manual",
        "shakeopen", "havesn", "moreadmin", "needreadmodel", "keypad",
        "fingprinter", "needregristerpwd", "timelimit", "lockout", "bt264",
        "doorsensor", "keepalive",
    ),
    "U-Bolt-ZWave": _capabilities(
        "lock", "bluetooth", "autolock", "update_ota", "direction", "alerts",
        "mutemode", "manual", "shakeopen", "havesn", "needreadmodel",
        "keypad", "needregristerpwd", "timelimit", "moreadmin", "lockout",
        "bt264", "doorsensor", "keepalive", "autounlock", "zwave",
    ),
    "U-Bolt-Pro-ZWave": _capabilities(
        "lock", "bluetooth", "autolock", "autounlock", "update_ota",
        "direction", "alerts", "mutemode", "manual", "shakeopen", "havesn",
        "moreadmin", "needreadmodel", "keypad", "fingprinter",
        "needregristerpwd", "timelimit", "lockout", "bt264", "doorsensor",
        "keepalive", "zwave",
    ),
    "SmartLockByBle": _capabilities(
        "bluetooth", "keypad", "fingprinter", "shakeopen", "morepwd",
        "passage", "lockout", "locklocal", "needsycbuser", "clone",
        "customuserid", "singlelatchboltmortic", "keepalive",
    ),
    "UL3-2ND": _capabilities(
        "bluetooth", "autolock", "update_ota", "alerts", "mutemode",
        "shakeopen", "fingprinter", "keypad", "doublefp", "needregristerpwd",
        "havesn", "locklocal", "needsycbuser", "moreadmin", "customuserid",
        "timelimit", "passage", "lockout", "bt264", "keepalive",
        "passageautolock", "singlelatchboltmortic",
    ),
    "UL300": _capabilities(
        "bluetooth", "rfid", "rfid_once", "keypad", "fingprinter",
        "update_ota", "update_oad", "alerts", "shakeopen", "mutemode",
        "moreadmin", "timelimit", "passage", "lockout", "morelanguage",
        "locklocal", "needsycbuser", "havesn", "keepalive",
        "singlelatchboltmortic", adduserremovenum=5,
    ),
}
for _model, _definition in known_devices.items():
    _definition.model = _model

MODEL_ALIASES = {
    "U-Bolt Pro": "U-Bolt-Pro",
    "U-Bolt-PRO": "U-Bolt-Pro",
    "U-Bolt Pro WiFi": "U-Bolt-Pro-WiFi",
    "U-Bolt Pro ZWave": "U-Bolt-Pro-ZWave",
}

GENERIC_LOCK_CAPABILITIES = _capabilities(
    "bluetooth", "autolock", "mutemode", "havesn", "timelimit", "passage",
    "lockout", "bt264", "keepalive", "bt_close",
)


class _KnownDeviceDefinition(DeviceDefinition):
    """Compatibility constructor backed by the canonical capability table."""

    model: ClassVar[str]

    def __init__(self) -> None:
        super().__init__(**asdict(known_devices[self.model]))


class DeviceLockLatch5Finger(_KnownDeviceDefinition):
    model = "Latch-5-F"


class DeviceLockLatch5NFC(_KnownDeviceDefinition):
    model = "Latch-5-NFC"


class DeviceLockUL1(_KnownDeviceDefinition):
    model = "UL1-BT"


class DeviceLockBoltNFC(_KnownDeviceDefinition):
    model = "Bolt-NFC"


class DeviceLockLever(_KnownDeviceDefinition):
    model = "LEVER"


class DeviceLockUBolt(_KnownDeviceDefinition):
    model = "U-Bolt"


class DeviceLockUBoltPro(_KnownDeviceDefinition):
    model = "U-Bolt-Pro"


class DeviceLockUboltWiFi(_KnownDeviceDefinition):
    model = "U-Bolt-WiFi"


class DeviceLockUBoltProWiFi(_KnownDeviceDefinition):
    model = "U-Bolt-Pro-WiFi"


class DeviceLockUBoltZwave(_KnownDeviceDefinition):
    model = "U-Bolt-ZWave"


class DeviceLockUBoltProZwave(_KnownDeviceDefinition):
    model = "U-Bolt-Pro-ZWave"


class DeviceLockUL3(_KnownDeviceDefinition):
    model = "SmartLockByBle"


class DeviceLockUL32ND(_KnownDeviceDefinition):
    model = "UL3-2ND"


class DeviceLockUL300(_KnownDeviceDefinition):
    model = "UL300"


class GenericLock(DeviceDefinition):
    """Compatibility constructor for unknown lock models."""

    def __init__(self) -> None:
        super().__init__(**asdict(GENERIC_LOCK_CAPABILITIES))


def canonical_model(model: str) -> str:
    """Return the canonical API model name."""

    return MODEL_ALIASES.get(model, model)
