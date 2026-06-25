from __future__ import annotations

import unittest

import serial

from modterm.core.serial_models import SerialConfig, SerialPortInfo


class SerialPortInfoTests(unittest.TestCase):
    def test_formats_vid_pid_as_uppercase_hex(self) -> None:
        port = SerialPortInfo(device="/dev/ttyUSB0", vid=0x0403, pid=0x6001)

        self.assertEqual(port.vid_pid, "0403:6001")

    def test_missing_vid_pid_uses_placeholder(self) -> None:
        port = SerialPortInfo(device="/dev/ttyS0")

        self.assertEqual(port.vid_pid, "—")


class SerialConfigTests(unittest.TestCase):
    def test_valid_config_passes_validation(self) -> None:
        config = SerialConfig(
            port="/dev/ttyUSB0",
            baudrate=19200,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_EVEN,
            timeout=0.5,
        )

        config.validate()

    def test_empty_port_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "serial port"):
            SerialConfig(port=" ").validate()

    def test_negative_timeout_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Timeout cannot"):
            SerialConfig(port="/dev/ttyUSB0", timeout=-1).validate()


if __name__ == "__main__":
    unittest.main()
