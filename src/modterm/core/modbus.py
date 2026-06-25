from __future__ import annotations

from dataclasses import dataclass

from modterm.core.checksums import (
    append_checksum,
    checksum_size,
    verify_checksum,
)
from modterm.core.parsers import parse_hex

FUNCTION_NAMES = {
    0x01: "Read Coils",
    0x02: "Read Discrete Inputs",
    0x03: "Read Holding Registers",
    0x04: "Read Input Registers",
    0x05: "Write Single Coil",
    0x06: "Write Single Register",
    0x0F: "Write Multiple Coils",
    0x10: "Write Multiple Registers",
}


@dataclass(frozen=True, slots=True)
class ModbusRequest:
    slave_id: int
    function_code: int
    start_address: int = 0
    quantity: int = 1
    register_value: int = 0
    coil_value: bool = False
    values: tuple[int, ...] = ()
    coil_values: tuple[bool, ...] = ()
    custom_payload: bytes = b""

    def validate_common(self) -> None:
        _validate_range("Slave ID", self.slave_id, 0, 247)
        _validate_range("Function code", self.function_code, 0, 255)
        _validate_range("Start address", self.start_address, 0, 0xFFFF)
        _validate_range("Quantity", self.quantity, 1, 2000)
        _validate_range("Register value", self.register_value, 0, 0xFFFF)


@dataclass(frozen=True, slots=True)
class ModbusFrameResult:
    raw: bytes
    valid: bool
    protocol: str
    slave_id: int | None
    function_code: int | None
    summary: str
    error: str | None = None
    data: bytes = b""


def _validate_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")


def build_pdu(request: ModbusRequest) -> bytes:
    request.validate_common()
    function = request.function_code
    address = request.start_address.to_bytes(2, "big")

    if function in {0x01, 0x02, 0x03, 0x04}:
        _validate_range("Quantity", request.quantity, 1, 2000 if function < 3 else 125)
        return bytes([function]) + address + request.quantity.to_bytes(2, "big")

    if function == 0x05:
        value = 0xFF00 if request.coil_value else 0x0000
        return bytes([function]) + address + value.to_bytes(2, "big")

    if function == 0x06:
        return bytes([function]) + address + request.register_value.to_bytes(2, "big")

    if function == 0x0F:
        values = request.coil_values
        if not values:
            raise ValueError("At least one coil value is required.")
        _validate_range("Coil count", len(values), 1, 1968)
        packed = bytearray((len(values) + 7) // 8)
        for index, enabled in enumerate(values):
            if enabled:
                packed[index // 8] |= 1 << (index % 8)
        return (
            bytes([function])
            + address
            + len(values).to_bytes(2, "big")
            + bytes([len(packed)])
            + bytes(packed)
        )

    if function == 0x10:
        values = request.values
        if not values:
            raise ValueError("At least one register value is required.")
        _validate_range("Register count", len(values), 1, 123)
        for value in values:
            _validate_range("Register value", value, 0, 0xFFFF)
        payload = b"".join(value.to_bytes(2, "big") for value in values)
        return (
            bytes([function])
            + address
            + len(values).to_bytes(2, "big")
            + bytes([len(payload)])
            + payload
        )

    return bytes([function]) + request.custom_payload


def build_rtu_frame(
    request: ModbusRequest,
    checksum_method: str = "Modbus CRC16",
    byte_order: str = "little",
) -> bytes:
    body = bytes([request.slave_id]) + build_pdu(request)
    return append_checksum(body, checksum_method, byte_order)


def build_ascii_frame(
    request: ModbusRequest,
    checksum_method: str = "Modbus ASCII LRC",
    byte_order: str = "big",
) -> bytes:
    body = bytes([request.slave_id]) + build_pdu(request)
    binary = append_checksum(body, checksum_method, byte_order)
    return b":" + binary.hex().upper().encode("ascii") + b"\r\n"


def decode_ascii_frame(frame: bytes | str) -> bytes:
    raw = frame.encode("ascii") if isinstance(frame, str) else frame
    raw = raw.strip()
    if not raw.startswith(b":"):
        raise ValueError("Modbus ASCII frame must start with ':'.")
    return parse_hex(raw[1:].decode("ascii"))


def _summary(slave_id: int, function: int, payload: bytes) -> str:
    base_function = function & 0x7F
    name = FUNCTION_NAMES.get(base_function, f"Custom 0x{base_function:02X}")
    if function & 0x80:
        exception = payload[0] if payload else 0
        return f"Slave {slave_id}, {name}, exception 0x{exception:02X}"
    if base_function in {0x01, 0x02, 0x03, 0x04} and payload:
        return f"Slave {slave_id}, {name}, {payload[0]} data byte(s)"
    return f"Slave {slave_id}, {name}"


def _checksum_error(method: str) -> str:
    if method == "Modbus CRC16":
        return "CRC mismatch"
    if method == "Modbus ASCII LRC":
        return "LRC mismatch"
    return f"{method} mismatch"


def parse_rtu_frame(
    frame: bytes,
    checksum_method: str = "Modbus CRC16",
    byte_order: str = "little",
) -> ModbusFrameResult:
    checksum_length = checksum_size(checksum_method)
    if len(frame) < 2 + checksum_length:
        return ModbusFrameResult(frame, False, "RTU", None, None, "Incomplete frame", "Too short")
    slave_id, function = frame[0], frame[1]
    valid = verify_checksum(frame, checksum_method, byte_order)
    payload = frame[2:-checksum_length] if checksum_length else frame[2:]
    return ModbusFrameResult(
        raw=frame,
        valid=valid,
        protocol="RTU",
        slave_id=slave_id,
        function_code=function,
        summary=_summary(slave_id, function, payload),
        error=None if valid else _checksum_error(checksum_method),
        data=payload,
    )


def parse_ascii_frame(
    frame: bytes | str,
    checksum_method: str = "Modbus ASCII LRC",
    byte_order: str = "big",
) -> ModbusFrameResult:
    raw = frame.encode("ascii") if isinstance(frame, str) else frame
    try:
        binary = decode_ascii_frame(raw)
    except (ValueError, UnicodeError) as exc:
        return ModbusFrameResult(raw, False, "ASCII", None, None, "Invalid frame", str(exc))
    checksum_length = checksum_size(checksum_method)
    if len(binary) < 2 + checksum_length:
        return ModbusFrameResult(raw, False, "ASCII", None, None, "Incomplete frame", "Too short")
    slave_id, function = binary[0], binary[1]
    valid = verify_checksum(binary, checksum_method, byte_order)
    payload = binary[2:-checksum_length] if checksum_length else binary[2:]
    return ModbusFrameResult(
        raw=raw,
        valid=valid,
        protocol="ASCII",
        slave_id=slave_id,
        function_code=function,
        summary=_summary(slave_id, function, payload),
        error=None if valid else _checksum_error(checksum_method),
        data=payload,
    )


def parse_register_values(text: str) -> tuple[int, ...]:
    if not text.strip():
        return ()
    values = []
    for token in text.replace(",", " ").replace(";", " ").split():
        base = 16 if token.lower().startswith("0x") else 10
        value = int(token, base)
        _validate_range("Register value", value, 0, 0xFFFF)
        values.append(value)
    return tuple(values)


def parse_coil_values(text: str) -> tuple[bool, ...]:
    if not text.strip():
        return ()
    values = []
    for token in text.replace(",", " ").replace(";", " ").split():
        normalized = token.strip().lower()
        if normalized in {"1", "true", "on"}:
            values.append(True)
        elif normalized in {"0", "false", "off"}:
            values.append(False)
        else:
            raise ValueError(f"Invalid coil value: {token}")
    return tuple(values)
