from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from modterm.core.checksums import (
    CHECKSUM_METHODS,
    CHECKSUMS,
    append_checksum,
    calculate_checksum,
    checksum_size,
)
from modterm.core.i18n import TranslationManager
from modterm.core.modbus import (
    FUNCTION_NAMES,
    ModbusRequest,
    build_ascii_frame,
    build_rtu_frame,
    parse_coil_values,
    parse_register_values,
)
from modterm.core.parsers import (
    append_line_ending,
    format_hex,
    parse_ascii_escapes,
    parse_binary,
    parse_hex,
    parse_payload,
)


class RawTerminalPage(QWidget):
    send_requested = Signal(bytes, str)
    error_occurred = Signal(str)

    def __init__(self, translator: TranslationManager) -> None:
        super().__init__()
        self._tr = translator
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.format_label = QLabel()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["ASCII", "HEX", "Binary"])
        self.ending_label = QLabel()
        self.ending_combo = QComboBox()
        self.ending_combo.addItems(["None", "CR", "LF", "CRLF"])
        toolbar.addWidget(self.format_label)
        toolbar.addWidget(self.format_combo)
        toolbar.addSpacing(20)
        toolbar.addWidget(self.ending_label)
        toolbar.addWidget(self.ending_combo)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.payload_label = QLabel()
        self.payload_label.setObjectName("sectionSubtitle")
        layout.addWidget(self.payload_label)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "ASCII: STATUS?\\r\\n    HEX: 01 03 00 00 00 02    Binary: 00000001 00000011"
        )
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)

        buttons = QHBoxLayout()
        self.send_button = QPushButton()
        self.clear_button = QPushButton()
        self.clear_button.setObjectName("secondaryButton")
        self.send_button.clicked.connect(self.send_current)
        self.clear_button.clicked.connect(self.editor.clear)
        buttons.addStretch()
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.send_button)
        layout.addLayout(buttons)
        layout.addStretch()

    def retranslate_ui(self) -> None:
        t = self._tr.t
        self.format_label.setText(t("input_format"))
        self.ending_label.setText(t("line_ending"))
        self.payload_label.setText(t("payload"))
        self.send_button.setText(t("send"))
        self.clear_button.setText(t("clear"))

    def build_payload(self) -> bytes:
        data = parse_payload(self.editor.toPlainText(), self.format_combo.currentText())
        return append_line_ending(data, self.ending_combo.currentText())

    def send_current(self) -> None:
        try:
            self.send_requested.emit(self.build_payload(), "RAW")
        except ValueError as exc:
            self.error_occurred.emit(str(exc))

    def template_state(self) -> tuple[str, str, dict[str, Any]]:
        mode = f"Raw {self.format_combo.currentText()}"
        return mode, self.editor.toPlainText(), {"line_ending": self.ending_combo.currentText()}

    def apply_template(self, payload: str, parameters: dict[str, Any]) -> None:
        self.editor.setPlainText(payload)
        ending = str(parameters.get("line_ending", "None"))
        index = self.ending_combo.findText(ending)
        if index >= 0:
            self.ending_combo.setCurrentIndex(index)


class ModbusPage(QWidget):
    send_requested = Signal(bytes, str)
    error_occurred = Signal(str)

    def __init__(self, translator: TranslationManager, protocol: str) -> None:
        super().__init__()
        self._tr = translator
        self.protocol = protocol.upper()
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._function_changed()

    def _spin(self, maximum: int = 65535, value: int = 0) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, maximum)
        spin.setValue(value)
        spin.setDisplayIntegerBase(10)
        return spin

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form_group = QGroupBox()
        form = QGridLayout(form_group)
        self.labels: dict[str, QLabel] = {}

        self.slave_spin = self._spin(247, 1)
        self.function_combo = QComboBox()
        for function, name in FUNCTION_NAMES.items():
            self.function_combo.addItem(f"0x{function:02X} — {name}", function)
        self.function_combo.addItem("Custom Function", -1)
        self.custom_function_spin = self._spin(255, 65)
        self.custom_function_spin.setPrefix("0x")
        self.custom_function_spin.setDisplayIntegerBase(16)
        self.address_spin = self._spin()
        self.quantity_spin = self._spin(2000, 1)
        self.register_spin = self._spin()
        self.coil_check = QCheckBox("ON / 0xFF00")
        self.values_edit = QLineEdit()
        self.values_edit.setPlaceholderText("Registers: 10, 20, 0x1234   Coils: 1, 0, 1")
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("00 01 02 03")
        self.checksum_combo = QComboBox()
        self.checksum_combo.addItems(CHECKSUM_METHODS)
        default_checksum = "Modbus CRC16" if self.protocol == "RTU" else "Modbus ASCII LRC"
        self.checksum_combo.setCurrentText(default_checksum)
        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItem("Little-endian", "little")
        self.byte_order_combo.addItem("Big-endian", "big")
        self.byte_order_combo.setCurrentIndex(0 if self.protocol == "RTU" else 1)

        fields = [
            ("slave_id", self.slave_spin),
            ("function", self.function_combo),
            ("custom_payload", self.custom_function_spin),
            ("start_address", self.address_spin),
            ("quantity", self.quantity_spin),
            ("register_value", self.register_spin),
            ("coil_value", self.coil_check),
            ("multiple_values", self.values_edit),
            ("custom_payload", self.custom_edit),
            ("checksum_method", self.checksum_combo),
            ("byte_order", self.byte_order_combo),
        ]
        self.field_rows: list[tuple[str, QLabel, QWidget]] = []
        for index, (key, widget) in enumerate(fields):
            label = QLabel()
            self.field_rows.append((key, label, widget))
            form.addWidget(label, index, 0)
            form.addWidget(widget, index, 1)
        form.setColumnStretch(1, 1)
        layout.addWidget(form_group)

        self.preview_label = QLabel()
        self.preview_label.setObjectName("sectionSubtitle")
        layout.addWidget(self.preview_label)
        self.preview = QLineEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

        button_row = QHBoxLayout()
        self.build_button = QPushButton()
        self.build_button.setObjectName("secondaryButton")
        self.send_button = QPushButton()
        self.build_button.clicked.connect(self.update_preview)
        self.send_button.clicked.connect(self.send_current)
        button_row.addStretch()
        button_row.addWidget(self.build_button)
        button_row.addWidget(self.send_button)
        layout.addLayout(button_row)
        layout.addStretch()

        self.function_combo.currentIndexChanged.connect(self._function_changed)
        self.checksum_combo.currentTextChanged.connect(self._checksum_changed)
        self.byte_order_combo.currentIndexChanged.connect(
            lambda _index: self.update_preview(silent=True)
        )

    def retranslate_ui(self) -> None:
        t = self._tr.t
        for key, label, widget in self.field_rows:
            if widget is self.custom_function_spin:
                label.setText("Custom function code")
            else:
                label.setText(t(key))
        self.preview_label.setText(t("frame_preview"))
        self.build_button.setText(t("build"))
        self.send_button.setText(t("build_send"))

    def _function_changed(self) -> None:
        function = int(self.function_combo.currentData())
        read = function in {1, 2, 3, 4}
        single_coil = function == 5
        single_register = function == 6
        multiple = function in {15, 16}
        custom = function == -1
        self.custom_function_spin.setVisible(custom)
        self.field_rows[2][1].setVisible(custom)
        self.address_spin.setVisible(not custom)
        self.field_rows[3][1].setVisible(not custom)
        self.quantity_spin.setVisible(read)
        self.field_rows[4][1].setVisible(read)
        self.register_spin.setVisible(single_register)
        self.field_rows[5][1].setVisible(single_register)
        self.coil_check.setVisible(single_coil)
        self.field_rows[6][1].setVisible(single_coil)
        self.values_edit.setVisible(multiple)
        self.field_rows[7][1].setVisible(multiple)
        self.custom_edit.setVisible(custom)
        self.field_rows[8][1].setVisible(custom)
        self._checksum_changed()
        self.update_preview(silent=True)

    def _checksum_changed(self, _method: str = "") -> None:
        is_16_bit = checksum_size(self.checksum_method) == 2
        self.byte_order_combo.setVisible(is_16_bit)
        self.field_rows[10][1].setVisible(is_16_bit)
        self.update_preview(silent=True)

    @property
    def checksum_method(self) -> str:
        return self.checksum_combo.currentText()

    @property
    def checksum_byte_order(self) -> str:
        return str(self.byte_order_combo.currentData())

    @property
    def protocol_context(self) -> str:
        return f"{self.protocol}|{self.checksum_method}|{self.checksum_byte_order}"

    def request(self) -> ModbusRequest:
        function = int(self.function_combo.currentData())
        if function == -1:
            function = self.custom_function_spin.value()
        values = parse_register_values(self.values_edit.text()) if function == 0x10 else ()
        coils = parse_coil_values(self.values_edit.text()) if function == 0x0F else ()
        return ModbusRequest(
            slave_id=self.slave_spin.value(),
            function_code=function,
            start_address=self.address_spin.value(),
            quantity=self.quantity_spin.value(),
            register_value=self.register_spin.value(),
            coil_value=self.coil_check.isChecked(),
            values=values,
            coil_values=coils,
            custom_payload=(
                parse_hex(self.custom_edit.text()) if function not in FUNCTION_NAMES else b""
            ),
        )

    def build_frame(self) -> bytes:
        request = self.request()
        if self.protocol == "RTU":
            return build_rtu_frame(request, self.checksum_method, self.checksum_byte_order)
        return build_ascii_frame(request, self.checksum_method, self.checksum_byte_order)

    def update_preview(self, _checked: bool = False, silent: bool = False) -> None:
        try:
            frame = self.build_frame()
            self.preview.setText(
                frame.decode("ascii").strip() if self.protocol == "ASCII" else format_hex(frame)
            )
        except ValueError as exc:
            if not silent:
                self.error_occurred.emit(str(exc))
            self.preview.clear()

    def send_current(self) -> None:
        try:
            frame = self.build_frame()
            self.preview.setText(
                frame.decode("ascii").strip() if self.protocol == "ASCII" else format_hex(frame)
            )
            self.send_requested.emit(frame, self.protocol_context)
        except ValueError as exc:
            self.error_occurred.emit(str(exc))

    def template_state(self) -> tuple[str, str, dict[str, Any]]:
        request = self.request()
        parameters = {
            "slave_id": request.slave_id,
            "function_code": request.function_code,
            "start_address": request.start_address,
            "quantity": request.quantity,
            "register_value": request.register_value,
            "coil_value": request.coil_value,
            "values": self.values_edit.text(),
            "custom_payload": self.custom_edit.text(),
            "checksum_method": self.checksum_method,
            "checksum_byte_order": self.checksum_byte_order,
        }
        return f"Modbus {self.protocol}", format_hex(self.build_frame()), parameters

    def apply_template(self, _payload: str, parameters: dict[str, Any]) -> None:
        self.slave_spin.setValue(int(parameters.get("slave_id", 1)))
        function = int(parameters.get("function_code", 3))
        index = self.function_combo.findData(function)
        if index < 0:
            index = self.function_combo.findData(-1)
            self.custom_function_spin.setValue(function)
        self.function_combo.setCurrentIndex(index)
        self.address_spin.setValue(int(parameters.get("start_address", 0)))
        self.quantity_spin.setValue(int(parameters.get("quantity", 1)))
        self.register_spin.setValue(int(parameters.get("register_value", 0)))
        self.coil_check.setChecked(bool(parameters.get("coil_value", False)))
        self.values_edit.setText(str(parameters.get("values", "")))
        self.custom_edit.setText(str(parameters.get("custom_payload", "")))
        default_checksum = "Modbus CRC16" if self.protocol == "RTU" else "Modbus ASCII LRC"
        self.checksum_combo.setCurrentText(str(parameters.get("checksum_method", default_checksum)))
        order = str(
            parameters.get(
                "checksum_byte_order",
                "little" if self.protocol == "RTU" else "big",
            )
        )
        order_index = self.byte_order_combo.findData(order)
        if order_index >= 0:
            self.byte_order_combo.setCurrentIndex(order_index)
        self.update_preview(silent=True)


class CustomPacketPage(QWidget):
    send_requested = Signal(bytes, str)
    error_occurred = Signal(str)

    def __init__(self, translator: TranslationManager) -> None:
        super().__init__()
        self._tr = translator
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HEX", "ASCII", "Binary"])
        self.header_edit = QLineEdit()
        self.header_edit.setPlaceholderText("AA 55")
        self.payload_edit = QPlainTextEdit()
        self.payload_edit.setPlaceholderText(
            "Payload may be entered as HEX, ASCII with escapes, or Binary."
        )
        self.payload_edit.setMinimumHeight(100)
        self.footer_edit = QLineEdit()
        self.footer_edit.setPlaceholderText("0D 0A")
        self.checksum_combo = QComboBox()
        self.checksum_combo.addItems(CHECKSUM_METHODS)
        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItem("Little-endian", "little")
        self.byte_order_combo.addItem("Big-endian", "big")
        self.ending_combo = QComboBox()
        self.ending_combo.addItems(["None", "CR", "LF", "CRLF"])

        self.form_labels: dict[str, QLabel] = {}
        for key, widget in (
            ("input_format", self.format_combo),
            ("packet_header", self.header_edit),
            ("payload", self.payload_edit),
            ("packet_footer", self.footer_edit),
            ("checksum_method", self.checksum_combo),
            ("byte_order", self.byte_order_combo),
            ("line_ending", self.ending_combo),
        ):
            label = QLabel()
            self.form_labels[key] = label
            form.addRow(label, widget)
        layout.addLayout(form)

        self.preview_label = QLabel()
        self.preview_label.setObjectName("sectionSubtitle")
        self.preview = QLineEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.preview)

        row = QHBoxLayout()
        self.build_button = QPushButton()
        self.build_button.setObjectName("secondaryButton")
        self.send_button = QPushButton()
        self.build_button.clicked.connect(self.update_preview)
        self.send_button.clicked.connect(self.send_current)
        row.addStretch()
        row.addWidget(self.build_button)
        row.addWidget(self.send_button)
        layout.addLayout(row)
        layout.addStretch()

        self.checksum_combo.currentTextChanged.connect(self._checksum_changed)
        self.byte_order_combo.currentIndexChanged.connect(
            lambda _index: self.update_preview(silent=True)
        )
        self._checksum_changed()

    def retranslate_ui(self) -> None:
        t = self._tr.t
        for key, label in self.form_labels.items():
            label.setText(t(key))
        self.preview_label.setText(t("frame_preview"))
        self.build_button.setText(t("build"))
        self.send_button.setText(t("build_send"))

    @property
    def checksum_method(self) -> str:
        return self.checksum_combo.currentText()

    @property
    def checksum_byte_order(self) -> str:
        return str(self.byte_order_combo.currentData())

    def _checksum_changed(self, _method: str = "") -> None:
        visible = checksum_size(self.checksum_method) == 2
        self.byte_order_combo.setVisible(visible)
        self.form_labels["byte_order"].setVisible(visible)
        self.update_preview(silent=True)

    def build_frame(self) -> bytes:
        header = parse_hex(self.header_edit.text())
        payload = parse_payload(self.payload_edit.toPlainText(), self.format_combo.currentText())
        footer = parse_hex(self.footer_edit.text())
        body = header + payload + footer
        frame = append_checksum(body, self.checksum_method, self.checksum_byte_order)
        return append_line_ending(frame, self.ending_combo.currentText())

    def update_preview(self, _checked: bool = False, silent: bool = False) -> None:
        try:
            self.preview.setText(format_hex(self.build_frame()))
        except ValueError as exc:
            self.preview.clear()
            if not silent:
                self.error_occurred.emit(str(exc))

    def send_current(self) -> None:
        try:
            frame = self.build_frame()
            self.preview.setText(format_hex(frame))
            context = f"CUSTOM|{self.checksum_method}|{self.checksum_byte_order}"
            self.send_requested.emit(frame, context)
        except ValueError as exc:
            self.error_occurred.emit(str(exc))

    def template_state(self) -> tuple[str, str, dict[str, Any]]:
        parameters = {
            "input_format": self.format_combo.currentText(),
            "header": self.header_edit.text(),
            "footer": self.footer_edit.text(),
            "checksum_method": self.checksum_method,
            "checksum_byte_order": self.checksum_byte_order,
            "line_ending": self.ending_combo.currentText(),
        }
        return "Custom Packet", self.payload_edit.toPlainText(), parameters

    def apply_template(self, payload: str, parameters: dict[str, Any]) -> None:
        self.payload_edit.setPlainText(payload)
        for combo, key, default in (
            (self.format_combo, "input_format", "HEX"),
            (self.checksum_combo, "checksum_method", "None"),
            (self.ending_combo, "line_ending", "None"),
        ):
            index = combo.findText(str(parameters.get(key, default)))
            if index >= 0:
                combo.setCurrentIndex(index)
        order_index = self.byte_order_combo.findData(
            str(parameters.get("checksum_byte_order", "little"))
        )
        if order_index >= 0:
            self.byte_order_combo.setCurrentIndex(order_index)
        self.header_edit.setText(str(parameters.get("header", "")))
        self.footer_edit.setText(str(parameters.get("footer", "")))
        self.update_preview(silent=True)


class ChecksumPage(QWidget):
    error_occurred = Signal(str)

    def __init__(self, translator: TranslationManager) -> None:
        super().__init__()
        self._tr = translator
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HEX", "ASCII", "Binary"])
        self.method_combo = QComboBox()
        self.method_combo.addItems(CHECKSUMS)
        self.input_editor = QPlainTextEdit()
        self.input_editor.setPlaceholderText("01 03 00 00 00 02")
        self.input_editor.setMinimumHeight(120)
        self.result_edit = QLineEdit()
        self.result_edit.setReadOnly(True)
        self.format_label = QLabel()
        self.method_label = QLabel()
        self.payload_label = QLabel()
        self.result_label = QLabel()
        form.addRow(self.format_label, self.format_combo)
        form.addRow(self.method_label, self.method_combo)
        form.addRow(self.payload_label, self.input_editor)
        form.addRow(self.result_label, self.result_edit)
        layout.addLayout(form)
        self.calculate_button = QPushButton()
        self.calculate_button.clicked.connect(self.calculate)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.calculate_button)
        layout.addLayout(row)
        layout.addStretch()

    def retranslate_ui(self) -> None:
        t = self._tr.t
        self.format_label.setText(t("input_format"))
        self.method_label.setText(t("checksum_method"))
        self.payload_label.setText(t("payload"))
        self.result_label.setText(t("result"))
        self.calculate_button.setText(t("calculate"))

    def calculate(self) -> None:
        try:
            mode = self.format_combo.currentText()
            text = self.input_editor.toPlainText()
            if mode == "HEX":
                data = parse_hex(text)
            elif mode == "Binary":
                data = parse_binary(text)
            else:
                data = parse_ascii_escapes(text)
            value, formatted = calculate_checksum(self.method_combo.currentText(), data)
            self.result_edit.setText(f"0x{formatted}  ({value})")
        except ValueError as exc:
            self.error_occurred.emit(str(exc))
