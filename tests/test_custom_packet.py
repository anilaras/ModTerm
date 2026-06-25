from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modterm.app import create_application
from modterm.core.i18n import TranslationManager
from modterm.ui.terminal_pages import CustomPacketPage


def test_custom_packet_builder_combines_header_payload_footer_checksum() -> None:
    app = create_application([])
    page = CustomPacketPage(TranslationManager())
    page.header_edit.setText("AA 55")
    page.format_combo.setCurrentText("HEX")
    page.payload_edit.setPlainText("01 02 03")
    page.footer_edit.setText("0D")
    page.checksum_combo.setCurrentText("SUM8")
    page.ending_combo.setCurrentText("LF")

    assert page.build_frame() == bytes.fromhex("AA 55 01 02 03 0D 12 0A")

    page.close()
    app.quit()


def test_custom_packet_supports_ascii_and_crc_byte_order() -> None:
    app = create_application([])
    page = CustomPacketPage(TranslationManager())
    page.format_combo.setCurrentText("ASCII")
    page.payload_edit.setPlainText(r"AB\r")
    page.checksum_combo.setCurrentText("CRC-16 IBM")
    page.byte_order_combo.setCurrentIndex(page.byte_order_combo.findData("little"))

    frame = page.build_frame()

    assert frame.startswith(b"AB\r")
    assert len(frame) == 5

    page.close()
    app.quit()
