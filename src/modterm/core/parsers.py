from __future__ import annotations

import re

_HEX_PREFIX = re.compile(r"(?i)0x")
_HEX_SEPARATOR = re.compile(r"[\s,;:_-]+")
_BINARY_SEPARATOR = re.compile(r"[\s,;:_-]+")


def parse_hex(text: str) -> bytes:
    cleaned = _HEX_PREFIX.sub("", text.strip())
    cleaned = _HEX_SEPARATOR.sub("", cleaned)
    if not cleaned:
        return b""
    if len(cleaned) % 2:
        raise ValueError("HEX input must contain an even number of digits.")
    if not re.fullmatch(r"[0-9a-fA-F]+", cleaned):
        raise ValueError("HEX input contains invalid characters.")
    return bytes.fromhex(cleaned)


def parse_binary(text: str) -> bytes:
    stripped = text.strip()
    if not stripped:
        return b""

    tokens = [token for token in _BINARY_SEPARATOR.split(stripped) if token]
    if len(tokens) == 1:
        compact = tokens[0]
        if compact.lower().startswith("0b"):
            compact = compact[2:]
        if not re.fullmatch(r"[01]+", compact):
            raise ValueError("Binary input may only contain 0 and 1.")
        if len(compact) % 8:
            raise ValueError("Binary input must contain complete 8-bit bytes.")
        tokens = [compact[index : index + 8] for index in range(0, len(compact), 8)]

    result = bytearray()
    for token in tokens:
        token = token[2:] if token.lower().startswith("0b") else token
        if not re.fullmatch(r"[01]{8}", token):
            raise ValueError("Each binary byte must contain exactly 8 bits.")
        result.append(int(token, 2))
    return bytes(result)


def parse_ascii_escapes(text: str, encoding: str = "utf-8") -> bytes:
    result = bytearray()
    index = 0
    escapes = {
        "r": b"\r",
        "n": b"\n",
        "t": b"\t",
        "\\": b"\\",
        "0": b"\0",
    }
    literal = []

    def flush_literal() -> None:
        if literal:
            result.extend("".join(literal).encode(encoding))
            literal.clear()

    while index < len(text):
        character = text[index]
        if character != "\\":
            literal.append(character)
            index += 1
            continue

        flush_literal()
        if index + 1 >= len(text):
            raise ValueError("ASCII input ends with an incomplete escape sequence.")
        escape = text[index + 1]
        if escape in escapes:
            result.extend(escapes[escape])
            index += 2
        elif escape == "x":
            digits = text[index + 2 : index + 4]
            if len(digits) != 2 or not re.fullmatch(r"[0-9a-fA-F]{2}", digits):
                raise ValueError(r"\x escape must be followed by two HEX digits.")
            result.append(int(digits, 16))
            index += 4
        else:
            raise ValueError(f"Unsupported escape sequence: \\{escape}")

    flush_literal()
    return bytes(result)


def parse_payload(text: str, mode: str) -> bytes:
    normalized = mode.strip().lower()
    if normalized in {"ascii", "raw ascii"}:
        return parse_ascii_escapes(text)
    if normalized in {"hex", "raw hex"}:
        return parse_hex(text)
    if normalized in {"binary", "raw binary"}:
        return parse_binary(text)
    raise ValueError(f"Unsupported payload mode: {mode}")


def format_ascii(data: bytes) -> str:
    parts: list[str] = []
    for byte in data:
        if byte == 0x0D:
            parts.append(r"\r")
        elif byte == 0x0A:
            parts.append(r"\n")
        elif byte == 0x09:
            parts.append(r"\t")
        elif 32 <= byte <= 126:
            parts.append(chr(byte))
        else:
            parts.append(f"\\x{byte:02X}")
    return "".join(parts)


def format_hex(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def format_binary(data: bytes) -> str:
    return " ".join(f"{byte:08b}" for byte in data)


def format_mixed(data: bytes) -> str:
    return f"{format_hex(data)}  |  {format_ascii(data)}"


def format_payload(data: bytes, mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized == "ascii":
        return format_ascii(data)
    if normalized == "hex":
        return format_hex(data)
    if normalized == "binary":
        return format_binary(data)
    if normalized == "mixed":
        return format_mixed(data)
    raise ValueError(f"Unsupported display mode: {mode}")


LINE_ENDINGS = {
    "None": b"",
    "CR": b"\r",
    "LF": b"\n",
    "CRLF": b"\r\n",
}


def append_line_ending(data: bytes, ending: str) -> bytes:
    try:
        return data + LINE_ENDINGS[ending]
    except KeyError as exc:
        raise ValueError(f"Unsupported line ending: {ending}") from exc
