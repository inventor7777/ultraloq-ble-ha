"""U-tec protocol conversion helpers."""

import logging


LOGGER = logging.getLogger("custom_components.ultraloq_ble.utecio")


def bytes_to_int2(byte_array: bytes) -> int:
    """Decode a two-byte little-endian integer."""

    return int.from_bytes(byte_array[:2], "little")


def to_byte_array(value: int, size: int) -> bytes:
    """Encode an integer as little-endian bytes."""

    return value.to_bytes(size, "little")

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
