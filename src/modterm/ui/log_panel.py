from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from modterm.core.i18n import TranslationManager
from modterm.core.models import LogEntry
from modterm.core.parsers import format_payload
from modterm.services.log_service import LogService


class CommunicationLogPanel(QFrame):
    display_mode_changed = Signal(str)

    def __init__(self, translator: TranslationManager, log_service: LogService) -> None:
        super().__init__()
        self.setObjectName("commandPanel")
        self._tr = translator
        self._logs = log_service
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitle")
        self.display_label = QLabel()
        self.display_combo = QComboBox()
        self.display_combo.addItems(["ASCII", "HEX", "Binary", "Mixed"])
        self.display_combo.setCurrentText("Mixed")
        self.auto_scroll = QCheckBox()
        self.auto_scroll.setChecked(True)
        self.clear_button = QPushButton()
        self.clear_button.setObjectName("secondaryButton")
        self.save_button = QPushButton()
        self.save_button.setObjectName("secondaryButton")
        self.clear_button.clicked.connect(self.clear)
        self.save_button.clicked.connect(self.export_text)
        self.display_combo.currentTextChanged.connect(self._rerender)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.display_label)
        header.addWidget(self.display_combo)
        header.addWidget(self.auto_scroll)
        header.addWidget(self.clear_button)
        header.addWidget(self.save_button)
        layout.addLayout(header)
        self.monitor = QTextEdit()
        self.monitor.setReadOnly(True)
        self.monitor.setObjectName("communicationMonitor")
        self.monitor.document().setMaximumBlockCount(10000)
        layout.addWidget(self.monitor)

    def retranslate_ui(self) -> None:
        t = self._tr.t
        self.title_label.setText(t("terminal_monitor"))
        self.display_label.setText(t("display"))
        self.auto_scroll.setText(t("auto_scroll"))
        self.clear_button.setText(t("clear_log"))
        self.save_button.setText(t("save_log"))

    @property
    def display_mode(self) -> str:
        return self.display_combo.currentText()

    def add_entry(self, entry: LogEntry) -> None:
        self._logs.add(entry)
        self._append_html(entry)

    def _append_html(self, entry: LogEntry) -> None:
        color = "#55d6be" if entry.direction == "TX" else "#64b5f6"
        if entry.direction == "ERR" or "mismatch" in entry.note.lower():
            color = "#ff6b7a"
        timestamp = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
        payload = escape(format_payload(entry.data, self.display_mode))
        note = f' <span style="color:#f5c96a">— {escape(entry.note)}</span>' if entry.note else ""
        self.monitor.append(
            f'<span style="color:#718596">{timestamp}</span> '
            f'<b style="color:{color}">[{entry.direction}]</b> '
            f'<span style="color:#9fb3c5">[{escape(entry.protocol)}]</span> '
            f'<span style="font-family:monospace">{payload}</span>{note}'
        )
        if self.auto_scroll.isChecked():
            self.monitor.moveCursor(QTextCursor.MoveOperation.End)

    def add_error(self, message: str) -> None:
        self.add_entry(LogEntry(datetime.now(), "ERR", b"", "SYSTEM", message))

    def _rerender(self) -> None:
        self.monitor.clear()
        for entry in self._logs.entries:
            self._append_html(entry)
        self.display_mode_changed.emit(self.display_mode)

    def clear(self) -> None:
        self._logs.clear()
        self.monitor.clear()

    def export_text(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export communication log", "modterm-log.txt", "Text files (*.txt)"
        )
        if filename:
            self._logs.export_text(Path(filename))


class LogsExportPage(QWidget):
    def __init__(self, translator: TranslationManager, log_service: LogService) -> None:
        super().__init__()
        self._tr = translator
        self._logs = log_service
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        layout.addWidget(self.title)
        self.stats = QLabel()
        self.stats.setStyleSheet("font-size: 13pt; line-height: 1.6;")
        layout.addWidget(self.stats)
        row = QHBoxLayout()
        self.csv_button = QPushButton()
        self.text_button = QPushButton()
        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("secondaryButton")
        self.csv_button.clicked.connect(self.export_csv)
        self.text_button.clicked.connect(self.export_text)
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.csv_button)
        row.addWidget(self.text_button)
        row.addWidget(self.refresh_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()

    def retranslate_ui(self) -> None:
        t = self._tr.t
        self.title.setText(t("log_statistics"))
        self.csv_button.setText(t("export_csv"))
        self.text_button.setText(t("export_text"))
        self.refresh_button.setText(t("refresh"))
        self.refresh()

    def refresh(self) -> None:
        t = self._tr.t
        stats = self._logs.statistics
        self.stats.setText(
            f"{t('tx_frames')}: <b>{stats['tx_frames']}</b><br>"
            f"{t('rx_frames')}: <b>{stats['rx_frames']}</b><br>"
            f"{t('tx_bytes')}: <b>{stats['tx_bytes']}</b><br>"
            f"{t('rx_bytes')}: <b>{stats['rx_bytes']}</b>"
        )

    def export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "modterm-log.csv", "CSV files (*.csv)"
        )
        if filename:
            self._logs.export_csv(filename)

    def export_text(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export text", "modterm-log.txt", "Text files (*.txt)"
        )
        if filename:
            self._logs.export_text(filename)
