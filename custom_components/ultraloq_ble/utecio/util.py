"""U-tec protocol conversion helpers."""

import datetime
import logging
import struct


LOGGER = logging.getLogger("custom_components.ultraloq_ble.utecio")


def date_from_4bytes(byte_array: bytes):
    if byte_array is None or len(byte_array) < 4:
        return None

    value = struct.unpack(">I", byte_array[:4])[0]
    seconds = value & 63
    year = ((value >> 26) & 63) + 2000
    month = ((value >> 22) - 1) & 15
    day = (value >> 17) & 31
    hour = (value >> 12) & 31
    minute = (value >> 6) & 63
    return datetime.datetime(year, month, day, hour, minute, seconds)


def date_to_4bytes(value: datetime.datetime) -> bytes:
    """Encode a local datetime for the lock's WRITE_TIME command."""

    if not 2000 <= value.year <= 2063:
        raise ValueError("Ultraloq device time must be between 2000 and 2063")
    packed = (
        ((value.year - 2000) << 26)
        | ((value.month + 1) << 22)
        | (value.day << 17)
        | (value.hour << 12)
        | (value.minute << 6)
        | value.second
    )
    return packed.to_bytes(4, "big")


def bytes_to_int2(byte_array: bytes) -> int:
    """Decode a two-byte little-endian integer."""

    return int.from_bytes(byte_array[:2], "little")


def byte_to_int4(byte_array, index):
    if byte_array is None:
        return 0
    return int.from_bytes(byte_array[index : index + 4], "little")


def bytes_to_ascii(byte_array: bytearray):
    if not byte_array:
        return None

    substring = byte_array.split(b"\0", 1)[0]
    try:
        return substring.decode("ISO8859-1")
    except UnicodeDecodeError:
        return None


def to_byte_array(value: int, size: int) -> bytearray:
    """Encode an integer as little-endian bytes."""

    value &= (1 << (min(size, 4) * 8)) - 1
    return bytearray(value.to_bytes(size, "little"))


def decode_password(password: int) -> str:
    """Decode the password that the API returns to the Admin Password."""

    try:
        byte_array = bytearray(4)
        i3 = 0
        while i3 < 4:
            byte_array[i3] = (password >> (i3 * 8)) & 255
            i3 += 1

        str2 = ""
        length = len(byte_array) - 1
        while length >= 0:
            hex_string = format(byte_array[length] & 0xFF, "02x")
            length -= 1
            if len(hex_string) == 1:
                hex_string = "0" + hex_string
            str2 = str2 + hex_string
        parse_int = int(str2[0])
        if parse_int == 0:
            return str(password)
        str3 = str(int(str2[1:], 16))
        if parse_int != len(str3):
            str4 = str3
            count = 0
            while count < (parse_int - len(str3)):
                str4 = "0" + str4
                count += 1
            return str4
        return str3
    except Exception:
        LOGGER.exception("Failed to decode Ultraloq admin password from API response")
        raise


class DeviceNotAvailable(Exception):
    """Device not visible on Bluetooth Network."""
