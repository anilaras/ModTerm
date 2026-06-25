from __future__ import annotations

from dataclasses import dataclass

import serial


@dataclass(frozen=True, slots=True)
class SerialPortInfo:
    """Display-friendly serial port metadata."""

    device: str
    description: str = ""
    manufacturer: str | None = None
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None

    @property
    def vid_pid(self) -> str:
        if self.vid is None or self.pid is None:
            return "—"
        return f"{self.vid:04X}:{self.pid:04X}"


@dataclass(frozen=True, slots=True)
class SerialConfig:
    """Settings required to open a serial connection."""

    port: str
    baudrate: int = 9600
    bytesize: int = serial.EIGHTBITS
    stopbits: float = serial.STOPBITS_ONE
    parity: str = serial.PARITY_NONE
    timeout: float | None = 1.0
    write_timeout: float | None = 1.0

    def validate(self) -> None:
        if not self.port.strip():
            raise ValueError("A serial port must be selected.")
        if self.baudrate <= 0:
            raise ValueError("Baud rate must be greater than zero.")
        if self.bytesize not in {
            serial.FIVEBITS,
            serial.SIXBITS,
            serial.SEVENBITS,
            serial.EIGHTBITS,
        }:
            raise ValueError("Invalid data bits value.")
        if self.stopbits not in {
            serial.STOPBITS_ONE,
            serial.STOPBITS_ONE_POINT_FIVE,
            serial.STOPBITS_TWO,
        }:
            raise ValueError("Invalid stop bits value.")
        if self.parity not in {
            serial.PARITY_NONE,
            serial.PARITY_EVEN,
            serial.PARITY_ODD,
            serial.PARITY_MARK,
            serial.PARITY_SPACE,
        }:
            raise ValueError("Invalid parity value.")
        if self.timeout is not None and self.timeout < 0:
            raise ValueError("Timeout cannot be negative.")
        if self.write_timeout is not None and self.write_timeout < 0:
            raise ValueError("Write timeout cannot be negative.")
