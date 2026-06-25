from __future__ import annotations

import os
import threading
import time

import pytest

from modterm.core.serial_models import SerialConfig
from modterm.services.serial_service import SerialService

if os.name != "nt":
    import pty


@pytest.mark.skipif(os.name == "nt", reason="Linux pseudo-terminal test")
def test_linux_pseudo_terminal_read_and_write() -> None:
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    received: list[bytes] = []
    event = threading.Event()

    def on_data(data: bytes) -> None:
        received.append(data)
        event.set()

    service = SerialService()
    service.set_callbacks(on_data)
    try:
        service.connect(SerialConfig(port=slave_name, timeout=0.05))

        os.write(master_fd, b"DEVICE-REPLY")
        assert event.wait(1.0)
        deadline = time.monotonic() + 1.0
        while len(b"".join(received)) < len(b"DEVICE-REPLY") and time.monotonic() < deadline:
            time.sleep(0.01)
        assert b"DEVICE-REPLY" in b"".join(received)

        assert service.write(b"HOST-COMMAND") == 12
        assert os.read(master_fd, 12) == b"HOST-COMMAND"
    finally:
        service.disconnect()
        os.close(master_fd)
        os.close(slave_fd)
