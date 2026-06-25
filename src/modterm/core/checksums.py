from __future__ import annotations


def modbus_crc16(data: bytes) -> int:
    """Return Modbus CRC-16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def append_modbus_crc(data: bytes) -> bytes:
    crc = modbus_crc16(data)
    return data + crc.to_bytes(2, "little")


def verify_modbus_crc(frame: bytes) -> bool:
    return len(frame) >= 3 and modbus_crc16(frame[:-2]) == int.from_bytes(frame[-2:], "little")


def modbus_lrc(data: bytes) -> int:
    """Return Modbus ASCII LRC."""
    return (-sum(data)) & 0xFF


def append_lrc(data: bytes) -> bytes:
    return data + bytes([modbus_lrc(data)])


def verify_lrc(data_with_lrc: bytes) -> bool:
    return len(data_with_lrc) >= 2 and (sum(data_with_lrc) & 0xFF) == 0


def xor_checksum(data: bytes) -> int:
    result = 0
    for byte in data:
        result ^= byte
    return result


def sum8(data: bytes) -> int:
    return sum(data) & 0xFF


def crc8(data: bytes, polynomial: int = 0x07, initial: int = 0x00) -> int:
    crc = initial & 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ polynomial) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def crc16_ibm(data: bytes, initial: int = 0x0000) -> int:
    crc = initial & 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial & 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


CHECKSUMS = {
    "Modbus CRC16": (modbus_crc16, 4),
    "Modbus ASCII LRC": (modbus_lrc, 2),
    "XOR": (xor_checksum, 2),
    "SUM8": (sum8, 2),
    "CRC-8": (crc8, 2),
    "CRC-16 IBM": (crc16_ibm, 4),
    "CRC-16 CCITT": (crc16_ccitt, 4),
}

CHECKSUM_METHODS = ("None", *CHECKSUMS)
CHECKSUM_SIZES = {
    "None": 0,
    "Modbus CRC16": 2,
    "Modbus ASCII LRC": 1,
    "XOR": 1,
    "SUM8": 1,
    "CRC-8": 1,
    "CRC-16 IBM": 2,
    "CRC-16 CCITT": 2,
}


def calculate_checksum(name: str, data: bytes) -> tuple[int, str]:
    try:
        function, width = CHECKSUMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown checksum method: {name}") from exc
    value = function(data)
    return value, f"{value:0{width}X}"


def checksum_size(name: str) -> int:
    try:
        return CHECKSUM_SIZES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown checksum method: {name}") from exc


def checksum_bytes(name: str, data: bytes, byte_order: str | None = None) -> bytes:
    size = checksum_size(name)
    if size == 0:
        return b""
    value, _ = calculate_checksum(name, data)
    if size == 1:
        return bytes([value])
    order = byte_order or ("little" if name == "Modbus CRC16" else "big")
    if order not in {"little", "big"}:
        raise ValueError("Checksum byte order must be 'little' or 'big'.")
    return value.to_bytes(size, order)


def append_checksum(
    data: bytes,
    method: str,
    byte_order: str | None = None,
) -> bytes:
    return data + checksum_bytes(method, data, byte_order)


def verify_checksum(
    frame: bytes,
    method: str,
    byte_order: str | None = None,
) -> bool:
    size = checksum_size(method)
    if size == 0:
        return True
    if len(frame) <= size:
        return False
    data = frame[:-size]
    return frame[-size:] == checksum_bytes(method, data, byte_order)
