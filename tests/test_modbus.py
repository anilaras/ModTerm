from __future__ import annotations

import pytest

from modterm.core.modbus import (
    ModbusRequest,
    build_ascii_frame,
    build_rtu_frame,
    parse_ascii_frame,
    parse_coil_values,
    parse_register_values,
    parse_rtu_frame,
)


def test_read_holding_registers_frames() -> None:
    request = ModbusRequest(slave_id=1, function_code=3, start_address=0, quantity=2)
    assert build_rtu_frame(request) == bytes.fromhex("01 03 00 00 00 02 C4 0B")
    assert build_ascii_frame(request) == b":010300000002FA\r\n"


def test_write_single_register_frame_is_valid() -> None:
    frame = build_rtu_frame(
        ModbusRequest(slave_id=1, function_code=6, start_address=1, register_value=3)
    )
    parsed = parse_rtu_frame(frame)
    assert parsed.valid
    assert parsed.function_code == 6
    assert "Write Single Register" in parsed.summary


def test_multiple_register_and_coil_frames() -> None:
    registers = build_rtu_frame(
        ModbusRequest(
            slave_id=1,
            function_code=0x10,
            start_address=10,
            values=(1, 2, 0x1234),
        )
    )
    coils = build_rtu_frame(
        ModbusRequest(
            slave_id=1,
            function_code=0x0F,
            start_address=0,
            coil_values=(True, False, True, True),
        )
    )
    assert parse_rtu_frame(registers).valid
    assert parse_rtu_frame(coils).valid


def test_ascii_parser_detects_bad_lrc() -> None:
    parsed = parse_ascii_frame(b":01030000000200\r\n")
    assert not parsed.valid
    assert parsed.error == "LRC mismatch"


def test_rtu_parser_detects_bad_crc() -> None:
    parsed = parse_rtu_frame(bytes.fromhex("01 03 02 00 01 00 00"))
    assert not parsed.valid
    assert parsed.error == "CRC mismatch"


def test_value_parsers() -> None:
    assert parse_register_values("10, 0x20 30") == (10, 32, 30)
    assert parse_coil_values("1 0 on off true false") == (
        True,
        False,
        True,
        False,
        True,
        False,
    )
    with pytest.raises(ValueError):
        parse_coil_values("maybe")


def test_selectable_rtu_checksum_and_byte_order() -> None:
    request = ModbusRequest(slave_id=1, function_code=3, start_address=0, quantity=2)
    frame = build_rtu_frame(request, "CRC-16 CCITT", "big")

    assert frame == bytes.fromhex("01 03 00 00 00 02 85 20")
    assert parse_rtu_frame(frame, "CRC-16 CCITT", "big").valid
    assert not parse_rtu_frame(frame, "CRC-16 CCITT", "little").valid


def test_selectable_ascii_checksum_and_no_checksum() -> None:
    request = ModbusRequest(slave_id=1, function_code=6, start_address=1, register_value=3)
    xor_frame = build_ascii_frame(request, "XOR")
    plain_frame = build_ascii_frame(request, "None")

    assert xor_frame == b":01060001000305\r\n"
    assert plain_frame == b":010600010003\r\n"
    assert parse_ascii_frame(xor_frame, "XOR").valid
    assert parse_ascii_frame(plain_frame, "None").valid
