from __future__ import annotations

from modterm.core.checksums import (
    append_checksum,
    checksum_bytes,
    crc8,
    crc16_ccitt,
    crc16_ibm,
    modbus_crc16,
    modbus_lrc,
    sum8,
    verify_checksum,
    verify_lrc,
    verify_modbus_crc,
    xor_checksum,
)


def test_standard_checksum_vectors() -> None:
    data = b"123456789"
    assert crc8(data) == 0xF4
    assert crc16_ibm(data) == 0xBB3D
    assert crc16_ccitt(data) == 0x29B1


def test_modbus_crc_and_lrc_vectors() -> None:
    request = bytes.fromhex("01 03 00 00 00 02")
    assert modbus_crc16(request) == 0x0BC4
    assert verify_modbus_crc(request + bytes.fromhex("C4 0B"))
    assert modbus_lrc(request) == 0xFA
    assert verify_lrc(request + b"\xfa")


def test_simple_checksums() -> None:
    data = bytes([1, 2, 3, 4])
    assert xor_checksum(data) == 4
    assert sum8(data) == 10


def test_generic_checksum_encoding_and_verification() -> None:
    data = bytes.fromhex("01 03 00 00 00 02")
    assert checksum_bytes("Modbus CRC16", data, "little") == bytes.fromhex("C4 0B")
    assert checksum_bytes("Modbus CRC16", data, "big") == bytes.fromhex("0B C4")
    assert append_checksum(data, "XOR") == data + b"\x00"
    assert verify_checksum(data + b"\x00", "XOR")
    assert append_checksum(data, "None") == data
    assert verify_checksum(data, "None")
