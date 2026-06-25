from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Protocol

import serial
from serial.tools import list_ports

from modterm.core.serial_models import SerialConfig, SerialPortInfo


class SerialConnection(Protocol):
    is_open: bool
    in_waiting: int

    def open(self) -> None: ...

    def close(self) -> None: ...

    def read(self, size: int = 1) -> bytes: ...

    def write(self, data: bytes) -> int: ...

    def flush(self) -> None: ...


SerialFactory = Callable[..., SerialConnection]
DataCallback = Callable[[bytes], None]
ErrorCallback = Callable[[str], None]
WriteCallback = Callable[[bytes, int], None]


class SerialService:
    """Owns serial port discovery and connection lifetime."""

    def __init__(self, serial_factory: SerialFactory | None = None) -> None:
        self._serial_factory = serial_factory or serial.Serial
        self._connection: SerialConnection | None = None
        self._config: SerialConfig | None = None
        self._data_callback: DataCallback | None = None
        self._error_callback: ErrorCallback | None = None
        self._write_callback: WriteCallback | None = None
        self._reader_thread: threading.Thread | None = None
        self._writer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        self._write_queue: queue.Queue[bytes | None] = queue.Queue()

    @property
    def is_connected(self) -> bool:
        return bool(self._connection is not None and self._connection.is_open)

    @property
    def config(self) -> SerialConfig | None:
        return self._config

    def set_callbacks(
        self,
        data_callback: DataCallback | None = None,
        error_callback: ErrorCallback | None = None,
        write_callback: WriteCallback | None = None,
    ) -> None:
        self._data_callback = data_callback
        self._error_callback = error_callback
        self._write_callback = write_callback

    def list_ports(self) -> list[SerialPortInfo]:
        ports = [
            SerialPortInfo(
                device=port.device,
                description=port.description or "",
                manufacturer=port.manufacturer,
                vid=port.vid,
                pid=port.pid,
                serial_number=port.serial_number,
            )
            for port in list_ports.comports()
        ]
        return sorted(ports, key=lambda item: item.device)

    def connect(self, config: SerialConfig) -> None:
        if self.is_connected:
            raise RuntimeError("The serial connection is already open.")

        config.validate()
        connection = self._serial_factory(
            port=config.port,
            baudrate=config.baudrate,
            bytesize=config.bytesize,
            stopbits=config.stopbits,
            parity=config.parity,
            timeout=config.timeout,
            write_timeout=config.write_timeout,
        )

        if not connection.is_open:
            connection.open()

        self._connection = connection
        self._config = config
        self._stop_event.clear()
        self._write_queue = queue.Queue()
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            name="modterm-serial-writer",
            daemon=True,
        )
        self._writer_thread.start()
        if self._data_callback is not None:
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                name="modterm-serial-reader",
                daemon=True,
            )
            self._reader_thread.start()

    def write(self, data: bytes) -> int:
        if not data:
            return 0
        connection = self._connection
        if connection is None or not connection.is_open:
            raise RuntimeError("The serial port is not connected.")
        with self._write_lock:
            written = connection.write(data)
            connection.flush()
        return written

    def write_async(self, data: bytes) -> int:
        if not data:
            return 0
        if not self.is_connected:
            raise RuntimeError("The serial port is not connected.")
        self._write_queue.put(bytes(data))
        return len(data)

    def _writer_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                data = self._write_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if data is None:
                break
            try:
                written = self.write(data)
                if self._write_callback is not None:
                    self._write_callback(data, written)
            except (serial.SerialException, OSError, RuntimeError, TypeError) as exc:
                if not self._stop_event.is_set() and self._error_callback is not None:
                    self._error_callback(str(exc))
                break

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            connection = self._connection
            if connection is None or not connection.is_open:
                break
            try:
                waiting = max(1, int(getattr(connection, "in_waiting", 0)))
                data = connection.read(waiting)
                if data and self._data_callback is not None:
                    self._data_callback(bytes(data))
            except (serial.SerialException, OSError, AttributeError, TypeError) as exc:
                if not self._stop_event.is_set() and self._error_callback is not None:
                    self._error_callback(str(exc))
                break

    def disconnect(self) -> None:
        self._stop_event.set()
        self._write_queue.put(None)
        connection = self._connection
        reader = self._reader_thread
        writer = self._writer_thread
        self._reader_thread = None
        self._writer_thread = None
        if writer is not None and writer.is_alive() and writer is not threading.current_thread():
            writer.join(timeout=1.5)
        if reader is not None and reader.is_alive() and reader is not threading.current_thread():
            reader.join(timeout=1.5)
        self._connection = None
        self._config = None
        if connection is not None and connection.is_open:
            connection.close()
