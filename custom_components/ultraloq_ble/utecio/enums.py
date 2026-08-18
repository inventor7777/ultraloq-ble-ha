from enum import Enum


class DeviceBatteryLevel(Enum):
    NOTSET = -1
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    CRITICAL = 0


class DeviceLockWorkMode(Enum):
    NOTSET = -1
    NORMAL = 0
    PASSAGE = 1
    LOCKOUT = 2


class DeviceLockStatus(Enum):
    NOTSET = -1
    UNAVAILABLE = 0
    UNLOCKED = 1
    LOCKED = 2
    JAMMED = 3
    NOTAVAILABLE = 255


class BLECommandCode(Enum):
    LOCK_STATUS = 80
    GET_LOCK_STATUS = 81
    GET_BATTERY = 67
    UNLOCK = 85
    BOLT_LOCK = 86
    SET_LOCK_STATUS = 82
    GET_AUTOLOCK = 90
    SET_AUTOLOCK = 89
    SET_WORK_MODE = 160
    ADMIN_LOGIN = 32


class BleResponseCode(Enum):
    LOCK_STATUS = 208
    GET_LOCK_STATUS = 209
    GET_BATTERY = 195
    UNLOCK = 213
    BOLT_LOCK = 214
    SET_LOCK_STATUS = 210
    SET_AUTOLOCK = 217
    GET_AUTOLOCK = 218
    SET_WORK_MODE = 32
    ADMIN_LOGIN = 160


class DeviceServiceUUID(Enum):
    DATA = "00007201-0000-1000-8000-00805f9b34fb"


class DeviceKeyUUID(Enum):
    STATIC = "00007220-0000-1000-8000-00805f9b34fb"
    MD5 = "00007223-0000-1000-8000-00805f9b34fb"
    ECC = "00007221-0000-1000-8000-00805f9b34fb"
