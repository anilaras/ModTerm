from __future__ import annotations

import pytest

from modterm.core.parsers import (
    append_line_ending,
    format_ascii,
    format_binary,
    format_hex,
    parse_ascii_escapes,
    parse_binary,
    parse_hex,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01 03 00 00 00 02", bytes.fromhex("010300000002")),
        ("010300000002", bytes.fromhex("010300000002")),
        ("0x01 0x03 0x00", bytes.fromhex("010300")),
    ],
)
def test_hex_parser_accepts_common_formats(text: str, expected: bytes) -> None:
    assert parse_hex(text) == expected


def test_hex_parser_rejects_odd_digits() -> None:
    with pytest.raises(ValueError, match="even"):
        parse_hex("123")


def test_binary_parser_accepts_compact_and_spaced() -> None:
    expected = b"\x01\x03"
    assert parse_binary("0000000100000011") == expected
    assert parse_binary("00000001 00000011") == expected
    assert format_binary(expected) == "00000001 00000011"


def test_ascii_escape_parser() -> None:
    assert parse_ascii_escapes(r"A\r\n\t\x01\\") == b"A\r\n\t\x01\\"
    assert format_ascii(b"A\r\n\x01") == r"A\r\n\x01"


def test_format_and_line_endings() -> None:
    assert format_hex(b"\x01\xab") == "01 AB"
    assert append_line_ending(b"AT", "CRLF") == b"AT\r\n"
