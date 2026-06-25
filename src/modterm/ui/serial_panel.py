from __future__ import annotations

from typing import Any

import serial
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modterm.core.i18n import TranslationManager
from modterm.core.serial_models import SerialConfig, SerialPortInfo
from modterm.services.serial_service import SerialService


class SerialConnectionPanel(QFrame):
    connection_changed = Signal(bool)
    status_message = Signal(str)
    data_received = Signal(bytes)
    data_written = Signal(bytes, int)
    serial_error = Signal(str)

    def __init__(
        self,
        service: SerialService,
        translator: TranslationManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self._service = service
        self._tr = translator
        self._service.set_callbacks(
            self.data_received.emit,
            self.serial_error.emit,
            self.data_written.emit,
        )
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self._set_connected_state(False)
        self.retranslate_ui()
        self.refresh_ports()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitle")
        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.refresh_ports)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        self.port_table = QTableWidget(0, 4)
        self.port_table.setObjectName("portTable")
        self.port_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.port_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.port_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.port_table.setAlternatingRowColors(True)
        self.port_table.verticalHeader().setVisible(False)
        self.port_table.horizontalHeader().setStretchLastSection(True)
        self.port_table.setMaximumHeight(190)
        self.port_table.itemSelectionChanged.connect(self._update_connect_button)
        layout.addWidget(self.port_table)

        self.port_count_label = QLabel()
        self.port_count_label.setObjectName("mutedLabel")
        layout.addWidget(self.port_count_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)

        self.settings_label = QLabel()
        self.settings_label.setObjectName("sectionSubtitle")
        layout.addWidget(self.settings_label)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.form_labels: dict[str, QLabel] = {}

        self.baudrate_combo = QComboBox()
        self.baudrate_combo.setEditable(True)
        self.baudrate_combo.addItems(
            ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
        )
        self.baudrate_combo.setCurrentText("9600")

        self.data_bits_combo = QComboBox()
        for bits in (5, 6, 7, 8):
            self.data_bits_combo.addItem(str(bits), bits)
        self.data_bits_combo.setCurrentText("8")

        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItem("1", serial.STOPBITS_ONE)
        self.stop_bits_combo.addItem("1.5", serial.STOPBITS_ONE_POINT_FIVE)
        self.stop_bits_combo.addItem("2", serial.STOPBITS_TWO)

        self.parity_combo = QComboBox()
        self.parity_combo.addItem("None", serial.PARITY_NONE)
        self.parity_combo.addItem("Even", serial.PARITY_EVEN)
        self.parity_combo.addItem("Odd", serial.PARITY_ODD)
        self.parity_combo.addItem("Mark", serial.PARITY_MARK)
        self.parity_combo.addItem("Space", serial.PARITY_SPACE)

        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 60.0)
        self.timeout_spin.setDecimals(2)
        self.timeout_spin.setValue(0.1)
        self.timeout_spin.setSuffix(" s")

        fields = [
            ("baudrate", self.baudrate_combo),
            ("data_bits", self.data_bits_combo),
            ("stop_bits", self.stop_bits_combo),
            ("parity", self.parity_combo),
            ("timeout", self.timeout_spin),
        ]
        for key, widget in fields:
            label = QLabel()
            self.form_labels[key] = label
            form.addRow(label, widget)
        layout.addLayout(form)

        layout.addStretch()

        self.connect_button = QPushButton()
        self.connect_button.setObjectName("connectButton")
        self.connect_button.setMinimumHeight(44)
        self.connect_button.clicked.connect(self._toggle_connection)
        layout.addWidget(self.connect_button)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(34)
        layout.addWidget(self.status_label)

    def retranslate_ui(self) -> None:
        t = self._tr.t
        self.title_label.setText(t("serial_connection"))
        self.refresh_button.setText(t("refresh"))
        self.settings_label.setText(t("connection_settings"))
        self.port_table.setHorizontalHeaderLabels(
            [t("port"), t("description"), t("manufacturer"), "VID:PID"]
        )
        for key, label in self.form_labels.items():
            label.setText(t(key))
        self._set_connected_state(self._service.is_connected)

    def refresh_ports(self) -> None:
        try:
            ports = self._service.list_ports()
        except Exception as exc:
            self._show_error(str(exc))
            return
        selected_device = self.selected_device()
        self.port_table.setRowCount(0)
        for row, port in enumerate(ports):
            self.port_table.insertRow(row)
            self._set_port_row(row, port)
            if port.device == selected_device:
                self.port_table.selectRow(row)
        self.port_table.resizeColumnsToContents()
        if ports and not self.port_table.selectedItems():
            self.port_table.selectRow(0)
        self.port_count_label.setText(self._tr.t("ports_found", count=len(ports)))
        self.status_message.emit(self.port_count_label.text())
        self._update_connect_button()

    def _set_port_row(self, row: int, port: SerialPortInfo) -> None:
        item = QTableWidgetItem(port.device)
        item.setData(Qt.ItemDataRole.UserRole, port.device)
        self.port_table.setItem(row, 0, item)
        self.port_table.setItem(row, 1, QTableWidgetItem(port.description or "—"))
        self.port_table.setItem(row, 2, QTableWidgetItem(port.manufacturer or "—"))
        self.port_table.setItem(row, 3, QTableWidgetItem(port.vid_pid))

    def selected_device(self) -> str | None:
        row = self.port_table.currentRow()
        item = self.port_table.item(row, 0) if row >= 0 else None
        return str(item.data(Qt.ItemDataRole.UserRole) or item.text()) if item else None

    def current_config(self) -> SerialConfig:
        port = self.selected_device()
        if port is None:
            raise ValueError("Select a serial port first.")
        try:
            baudrate = int(self.baudrate_combo.currentText().strip())
        except ValueError as exc:
            raise ValueError("Baud rate must be an integer.") from exc
        return SerialConfig(
            port=port,
            baudrate=baudrate,
            bytesize=int(self.data_bits_combo.currentData()),
            stopbits=float(self.stop_bits_combo.currentData()),
            parity=str(self.parity_combo.currentData()),
            timeout=float(self.timeout_spin.value()),
            write_timeout=float(self.timeout_spin.value()),
        )

    def settings_dict(self) -> dict[str, Any]:
        config = self.current_config()
        return {
            "port": config.port,
            "baudrate": config.baudrate,
            "bytesize": config.bytesize,
            "stopbits": config.stopbits,
            "parity": config.parity,
            "timeout": config.timeout,
        }

    def apply_settings(self, settings: dict[str, Any]) -> None:
        port = str(settings.get("port", ""))
        for row in range(self.port_table.rowCount()):
            if self.port_table.item(row, 0).text() == port:
                self.port_table.selectRow(row)
                break
        self.baudrate_combo.setCurrentText(str(settings.get("baudrate", 9600)))
        self._select_data(self.data_bits_combo, settings.get("bytesize", 8))
        self._select_data(self.stop_bits_combo, settings.get("stopbits", 1))
        self._select_data(self.parity_combo, settings.get("parity", serial.PARITY_NONE))
        self.timeout_spin.setValue(float(settings.get("timeout", 0.1)))

    @staticmethod
    def _select_data(combo: QComboBox, value: object) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _toggle_connection(self) -> None:
        if self._service.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self) -> None:
        try:
            config = self.current_config()
            self._service.connect(config)
        except (ValueError, RuntimeError, serial.SerialException, OSError) as exc:
            self._show_error(str(exc))
            return
        self._set_connected_state(True)
        self.connection_changed.emit(True)
        self.status_message.emit(f"{config.port} connected at {config.baudrate} baud.")

    def disconnect(self) -> None:
        port = self._service.config.port if self._service.config else "Serial port"
        try:
            self._service.disconnect()
        except (serial.SerialException, OSError) as exc:
            self._show_error(str(exc))
        self._set_connected_state(False)
        self.connection_changed.emit(False)
        self.status_message.emit(f"{port} disconnected.")

    def _set_connected_state(self, connected: bool) -> None:
        t = self._tr.t
        self.connect_button.setText(t("disconnect") if connected else t("connect"))
        self.connect_button.setProperty("connected", connected)
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.status_label.setText(t("connected") if connected else t("disconnected"))
        self.status_label.setProperty("connected", connected)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        for widget in (
            self.port_table,
            self.refresh_button,
            self.baudrate_combo,
            self.data_bits_combo,
            self.stop_bits_combo,
            self.parity_combo,
            self.timeout_spin,
        ):
            widget.setEnabled(not connected)
        self._update_connect_button()

    def _update_connect_button(self) -> None:
        self.connect_button.setEnabled(
            self._service.is_connected or self.selected_device() is not None
        )

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "ModTerm", message)
        self.status_message.emit(message)

    def shutdown(self) -> None:
        if self._service.is_connected:
            self._service.disconnect()
