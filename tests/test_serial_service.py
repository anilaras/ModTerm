from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from modterm.core.serial_models import SerialConfig
from modterm.services.serial_service import SerialService


class FakeSerial:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.is_open = True
        self.open_calls = 0
        self.close_calls = 0
        self.written = bytearray()
        self.in_waiting = 0

    def open(self) -> None:
        self.open_calls += 1
        self.is_open = True

    def close(self) -> None:
        self.close_calls += 1
        self.is_open = False

    def read(self, size: int = 1) -> bytes:
        return b""

    def write(self, data: bytes) -> int:
        self.written.extend(data)
        return len(data)

    def flush(self) -> None:
        pass


class SerialServiceTests(unittest.TestCase):
    def test_connect_and_disconnect_own_connection_lifetime(self) -> None:
        created: list[FakeSerial] = []

        def factory(**kwargs: object) -> FakeSerial:
            connection = FakeSerial(**kwargs)
            created.append(connection)
            return connection

        service = SerialService(serial_factory=factory)
        config = SerialConfig(port="/dev/ttyUSB0", baudrate=19200)

        service.connect(config)

        self.assertTrue(service.is_connected)
        self.assertEqual(service.config, config)
        self.assertEqual(created[0].kwargs["port"], "/dev/ttyUSB0")
        self.assertEqual(created[0].kwargs["baudrate"], 19200)

        service.disconnect()

        self.assertFalse(service.is_connected)
        self.assertIsNone(service.config)
        self.assertEqual(created[0].close_calls, 1)

    def test_second_connection_is_rejected(self) -> None:
        service = SerialService(serial_factory=FakeSerial)
        service.connect(SerialConfig(port="/dev/ttyUSB0"))

        with self.assertRaisesRegex(RuntimeError, "already open"):
            service.connect(SerialConfig(port="/dev/ttyUSB1"))

    def test_write_sends_all_bytes(self) -> None:
        created: list[FakeSerial] = []

        def factory(**kwargs: object) -> FakeSerial:
            connection = FakeSerial(**kwargs)
            created.append(connection)
            return connection

        service = SerialService(serial_factory=factory)
        service.connect(SerialConfig(port="/dev/ttyUSB0"))

        written = service.write(b"\x01\x03")

        self.assertEqual(written, 2)
        self.assertEqual(created[0].written, b"\x01\x03")
        service.disconnect()

    def test_async_write_uses_writer_thread(self) -> None:
        created: list[FakeSerial] = []
        completed: list[tuple[bytes, int]] = []
        event = threading.Event()

        def factory(**kwargs: object) -> FakeSerial:
            connection = FakeSerial(**kwargs)
            created.append(connection)
            return connection

        def on_written(data: bytes, count: int) -> None:
            completed.append((data, count))
            event.set()

        service = SerialService(serial_factory=factory)
        service.set_callbacks(write_callback=on_written)
        service.connect(SerialConfig(port="/dev/ttyUSB0"))
        service.write_async(b"ASYNC")

        self.assertTrue(event.wait(1.0))
        self.assertEqual(completed, [(b"ASYNC", 5)])
        self.assertEqual(created[0].written, b"ASYNC")
        service.disconnect()

    @patch("modterm.services.serial_service.list_ports.comports")
    def test_port_metadata_is_mapped_and_sorted(self, comports: object) -> None:
        comports.return_value = [
            SimpleNamespace(
                device="/dev/ttyUSB1",
                description="Adapter B",
                manufacturer=None,
                vid=None,
                pid=None,
                serial_number=None,
            ),
            SimpleNamespace(
                device="/dev/ttyACM0",
                description="Adapter A",
                manufacturer="Vendor",
                vid=0x1234,
                pid=0xABCD,
                serial_number="42",
            ),
        ]

        ports = SerialService().list_ports()

        self.assertEqual([port.device for port in ports], ["/dev/ttyACM0", "/dev/ttyUSB1"])
        self.assertEqual(ports[0].manufacturer, "Vendor")
        self.assertEqual(ports[0].vid_pid, "1234:ABCD")


if __name__ == "__main__":
    unittest.main()
