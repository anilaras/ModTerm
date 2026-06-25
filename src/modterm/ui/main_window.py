from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from modterm import __version__
from modterm.core.i18n import TranslationManager
from modterm.core.modbus import parse_ascii_frame, parse_rtu_frame
from modterm.core.models import (
    CommandTemplate,
    LogEntry,
    ProjectData,
    UserPreferences,
)
from modterm.services.log_service import LogService
from modterm.services.persistence import (
    load_project,
    load_templates,
    save_templates,
)
from modterm.services.persistence import (
    save_project as write_project,
)
from modterm.services.serial_service import SerialService
from modterm.ui.command_panel import CommandLibraryPanel
from modterm.ui.log_panel import CommunicationLogPanel, LogsExportPage
from modterm.ui.serial_panel import SerialConnectionPanel
from modterm.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET
from modterm.ui.terminal_pages import (
    ChecksumPage,
    CustomPacketPage,
    ModbusPage,
    RawTerminalPage,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings()
        self.translator = TranslationManager(self.settings.value("language", "en", str))
        self.theme = self.settings.value("theme", "dark", str)
        self.project_path: Path | None = None
        self.project_name = "Untitled"
        self._last_protocol = "RAW"
        self._pending_protocols: deque[str] = deque()
        self._receive_buffer = bytearray()
        self._receive_timer = QTimer(self)
        self._receive_timer.setSingleShot(True)
        self._receive_timer.timeout.connect(self._flush_received)

        self.serial_service = SerialService()
        self.log_service = LogService()

        self._build_ui()
        self._build_menus()
        self._wire_signals()
        self._load_template_library()
        self.apply_theme(self.theme)
        self.translator.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._update_project_label()

        self.resize(1500, 900)
        self.setMinimumSize(1100, 700)

    def _build_ui(self) -> None:
        root = QSplitter(Qt.Orientation.Horizontal)
        self.serial_panel = SerialConnectionPanel(self.serial_service, self.translator)
        self.command_panel = CommandLibraryPanel(self.translator)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(8, 8, 8, 8)
        center_layout.setSpacing(8)
        center_layout.addWidget(self._build_top_bar())

        vertical = QSplitter(Qt.Orientation.Vertical)
        self.tabs = QTabWidget()
        self.raw_page = RawTerminalPage(self.translator)
        self.rtu_page = ModbusPage(self.translator, "RTU")
        self.ascii_page = ModbusPage(self.translator, "ASCII")
        self.custom_page = CustomPacketPage(self.translator)
        self.checksum_page = ChecksumPage(self.translator)
        self.logs_page = LogsExportPage(self.translator, self.log_service)
        for page in (
            self.raw_page,
            self.rtu_page,
            self.ascii_page,
            self.custom_page,
            self.checksum_page,
            self.logs_page,
        ):
            self.tabs.addTab(page, "")
        self.log_panel = CommunicationLogPanel(self.translator, self.log_service)
        vertical.addWidget(self.tabs)
        vertical.addWidget(self.log_panel)
        vertical.setSizes([470, 330])
        vertical.setStretchFactor(0, 3)
        vertical.setStretchFactor(1, 2)
        center_layout.addWidget(vertical)

        root.addWidget(self.serial_panel)
        root.addWidget(center)
        root.addWidget(self.command_panel)
        root.setSizes([330, 920, 280])
        root.setStretchFactor(0, 0)
        root.setStretchFactor(1, 1)
        root.setStretchFactor(2, 0)
        self.setCentralWidget(root)

        self.connection_status = QLabel()
        self.connection_status.setObjectName("mutedLabel")
        self.counter_status = QLabel("TX 0 B  |  RX 0 B")
        self.statusBar().addPermanentWidget(self.connection_status)
        self.statusBar().addPermanentWidget(self.counter_status)

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        brand = QLabel("MODTERM")
        brand.setStyleSheet(
            "font-size: 18pt; font-weight: 900; letter-spacing: 3px; color: #65d6c5;"
        )
        subtitle = QLabel("SERIAL / RS-485 / MODBUS")
        subtitle.setObjectName("mutedLabel")
        self.project_label = QLabel()
        self.project_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.project_label)
        return bar

    def _build_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu("")
        self.new_action = QAction(self)
        self.open_action = QAction(self)
        self.save_action = QAction(self)
        self.save_as_action = QAction(self)
        self.export_action = QAction(self)
        self.exit_action = QAction(self)
        self.new_action.setShortcut("Ctrl+N")
        self.open_action.setShortcut("Ctrl+O")
        self.save_action.setShortcut("Ctrl+S")
        self.file_menu.addActions(
            [self.new_action, self.open_action, self.save_action, self.save_as_action]
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.view_menu = self.menuBar().addMenu("")
        self.language_menu = self.view_menu.addMenu("")
        self.english_action = QAction(self, checkable=True)
        self.turkish_action = QAction(self, checkable=True)
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        language_group.addAction(self.english_action)
        language_group.addAction(self.turkish_action)
        self.language_menu.addActions([self.english_action, self.turkish_action])
        self.theme_menu = self.view_menu.addMenu("")
        self.dark_action = QAction(self, checkable=True)
        self.light_action = QAction(self, checkable=True)
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        theme_group.addAction(self.dark_action)
        theme_group.addAction(self.light_action)
        self.theme_menu.addActions([self.dark_action, self.light_action])

        self.help_menu = self.menuBar().addMenu("")
        self.about_action = QAction(self)
        self.help_menu.addAction(self.about_action)

        self.new_action.triggered.connect(self.new_project)
        self.open_action.triggered.connect(self.open_project)
        self.save_action.triggered.connect(self.save_project)
        self.save_as_action.triggered.connect(lambda: self.save_project(save_as=True))
        self.export_action.triggered.connect(self.log_panel.export_text)
        self.exit_action.triggered.connect(self.close)
        self.english_action.triggered.connect(lambda: self.set_language("en"))
        self.turkish_action.triggered.connect(lambda: self.set_language("tr"))
        self.dark_action.triggered.connect(lambda: self.apply_theme("dark"))
        self.light_action.triggered.connect(lambda: self.apply_theme("light"))
        self.about_action.triggered.connect(self.show_about)

    def _wire_signals(self) -> None:
        self.serial_panel.status_message.connect(self.show_status)
        self.serial_panel.connection_changed.connect(self._connection_changed)
        self.serial_panel.data_received.connect(self._receive_data)
        self.serial_panel.data_written.connect(self._write_complete)
        self.serial_panel.serial_error.connect(self._serial_error)
        self.raw_page.send_requested.connect(self.send_data)
        self.rtu_page.send_requested.connect(self.send_data)
        self.ascii_page.send_requested.connect(self.send_data)
        self.custom_page.send_requested.connect(self.send_data)
        self.raw_page.error_occurred.connect(self._show_error)
        self.rtu_page.error_occurred.connect(self._show_error)
        self.ascii_page.error_occurred.connect(self._show_error)
        self.custom_page.error_occurred.connect(self._show_error)
        self.checksum_page.error_occurred.connect(self._show_error)
        self.command_panel.add_requested.connect(self.add_template)
        self.command_panel.update_requested.connect(self.update_template)
        self.command_panel.delete_requested.connect(self.delete_template)
        self.command_panel.load_requested.connect(self.load_template)
        self.command_panel.repeat_send_requested.connect(self.send_current_command)

    def retranslate_ui(self) -> None:
        t = self.translator.t
        self.setWindowTitle(t("app_title"))
        self.file_menu.setTitle(t("file"))
        self.new_action.setText(t("new_project"))
        self.open_action.setText(t("open_project"))
        self.save_action.setText(t("save_project"))
        self.save_as_action.setText(t("save_project_as"))
        self.export_action.setText(t("export_log"))
        self.exit_action.setText(t("exit"))
        self.view_menu.setTitle(t("view"))
        self.language_menu.setTitle(t("language"))
        self.english_action.setText(t("english"))
        self.turkish_action.setText(t("turkish"))
        self.theme_menu.setTitle(t("theme"))
        self.dark_action.setText(t("dark"))
        self.light_action.setText(t("light"))
        self.help_menu.setTitle(t("help"))
        self.about_action.setText(t("about"))
        tab_keys = [
            "raw_terminal",
            "modbus_rtu",
            "modbus_ascii",
            "custom_packet",
            "checksum_calculator",
            "logs_export",
        ]
        for index, key in enumerate(tab_keys):
            self.tabs.setTabText(index, t(key))
        self.english_action.setChecked(self.translator.language == "en")
        self.turkish_action.setChecked(self.translator.language == "tr")
        self._connection_changed(self.serial_service.is_connected)
        self.show_status(t("ready"))

    def set_language(self, language: str) -> None:
        self.translator.set_language(language)
        self.settings.setValue("language", language)

    def apply_theme(self, theme: str) -> None:
        self.theme = "light" if theme == "light" else "dark"
        self.setStyleSheet(LIGHT_STYLESHEET if self.theme == "light" else DARK_STYLESHEET)
        self.settings.setValue("theme", self.theme)
        self.dark_action.setChecked(self.theme == "dark")
        self.light_action.setChecked(self.theme == "light")

    def send_data(self, data: bytes, protocol: str) -> None:
        self._pending_protocols.append(protocol)
        try:
            queued = self.serial_service.write_async(data)
        except (RuntimeError, OSError) as exc:
            self._pending_protocols.pop()
            self._show_error(str(exc))
            return
        self._last_protocol = protocol
        self.show_status(f"Queued {queued} byte(s) for transmission.")

    def _write_complete(self, data: bytes, written: int) -> None:
        context = self._pending_protocols.popleft() if self._pending_protocols else "RAW"
        self._last_protocol = context
        protocol, _, _ = self._protocol_context(context)
        self.log_panel.add_entry(LogEntry(datetime.now(), "TX", data, protocol))
        self.show_status(self.translator.t("sent_bytes", count=written))
        self._update_statistics()

    def send_current_command(self) -> None:
        try:
            page = self.tabs.currentWidget()
            if page is self.raw_page:
                self.raw_page.send_current()
            elif page is self.rtu_page:
                self.rtu_page.send_current()
            elif page is self.ascii_page:
                self.ascii_page.send_current()
            elif page is self.custom_page:
                self.custom_page.send_current()
            else:
                raise ValueError("Select a command terminal before starting repeat mode.")
        except (ValueError, RuntimeError) as exc:
            self.command_panel.stop_repeat()
            self._show_error(str(exc))

    def _receive_data(self, data: bytes) -> None:
        self._receive_buffer.extend(data)
        self._receive_timer.start(50)

    def _flush_received(self) -> None:
        if not self._receive_buffer:
            return
        data = bytes(self._receive_buffer)
        self._receive_buffer.clear()
        note = ""
        protocol, checksum_method, byte_order = self._protocol_context(self._last_protocol)
        if protocol == "RTU":
            result = parse_rtu_frame(data, checksum_method, byte_order)
            note = result.summary if result.valid else f"{result.summary}: {result.error}"
        elif protocol == "ASCII":
            result = parse_ascii_frame(data, checksum_method, byte_order)
            note = result.summary if result.valid else f"{result.summary}: {result.error}"
        self.log_panel.add_entry(LogEntry(datetime.now(), "RX", data, protocol, note))
        self.show_status(self.translator.t("received_bytes", count=len(data)))
        self._update_statistics()

    def _serial_error(self, message: str) -> None:
        self.log_panel.add_error(message)
        self.serial_panel.disconnect()
        self._show_error(message)

    def _connection_changed(self, connected: bool) -> None:
        self.connection_status.setText(
            self.translator.t("connected") if connected else self.translator.t("disconnected")
        )

    def _update_statistics(self) -> None:
        stats = self.log_service.statistics
        self.counter_status.setText(
            f"TX {stats['tx_frames']} / {stats['tx_bytes']} B  |  "
            f"RX {stats['rx_frames']} / {stats['rx_bytes']} B"
        )
        self.logs_page.refresh()

    def _current_template_data(self, name: str) -> CommandTemplate:
        if not name.strip():
            raise ValueError("Template name is required.")
        page = self.tabs.currentWidget()
        if page not in {self.raw_page, self.rtu_page, self.ascii_page, self.custom_page}:
            raise ValueError("Select a packet or protocol terminal.")
        mode, payload, parameters = page.template_state()
        return CommandTemplate(
            name=name.strip(),
            description=self.command_panel.description_edit.text().strip(),
            mode=mode,
            payload=payload,
            auto_checksum=mode.startswith("Modbus") or mode == "Custom Packet",
            repeat=self.command_panel.repeat_settings(),
            parameters=parameters,
        )

    def add_template(self, name: str) -> None:
        try:
            self.command_panel.append_template(self._current_template_data(name))
            self._save_template_library()
        except ValueError as exc:
            self._show_error(str(exc))

    def update_template(self, index: int, name: str) -> None:
        try:
            self.command_panel.replace_template(index, self._current_template_data(name))
            self._save_template_library()
        except ValueError as exc:
            self._show_error(str(exc))

    def delete_template(self, index: int) -> None:
        try:
            self.command_panel.remove_template(index)
            self._save_template_library()
        except ValueError as exc:
            self._show_error(str(exc))

    def load_template(self, index: int) -> None:
        try:
            template = self.command_panel.selected_template(index)
            if template.mode.startswith("Raw"):
                self.tabs.setCurrentWidget(self.raw_page)
                raw_format = template.mode.removeprefix("Raw ").strip()
                format_index = self.raw_page.format_combo.findText(raw_format)
                if format_index >= 0:
                    self.raw_page.format_combo.setCurrentIndex(format_index)
                self.raw_page.apply_template(template.payload, template.parameters)
            elif template.mode == "Modbus RTU":
                self.tabs.setCurrentWidget(self.rtu_page)
                self.rtu_page.apply_template(template.payload, template.parameters)
            elif template.mode == "Modbus ASCII":
                self.tabs.setCurrentWidget(self.ascii_page)
                self.ascii_page.apply_template(template.payload, template.parameters)
            elif template.mode == "Custom Packet":
                self.tabs.setCurrentWidget(self.custom_page)
                self.custom_page.apply_template(template.payload, template.parameters)
            self.command_panel.apply_repeat_settings(template.repeat)
        except ValueError as exc:
            self._show_error(str(exc))

    def _template_path(self) -> Path:
        directory = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        )
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            directory = Path(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
            )
            directory /= "modterm"
            directory.mkdir(parents=True, exist_ok=True)
        return directory / "templates.json"

    def _load_template_library(self) -> None:
        try:
            self.command_panel.set_templates(load_templates(self._template_path()))
        except (ValueError, OSError) as exc:
            self.show_status(str(exc))

    def _save_template_library(self) -> None:
        try:
            save_templates(self._template_path(), self.command_panel.templates)
        except OSError as exc:
            self.show_status(str(exc))

    def new_project(self) -> None:
        self.project_path = None
        self.project_name = "Untitled"
        self.command_panel.set_templates([])
        self.log_panel.clear()
        self._update_project_label()

    def project_data(self) -> ProjectData:
        try:
            serial_settings = self.serial_panel.settings_dict()
        except ValueError:
            serial_settings = {}
        return ProjectData(
            name=self.project_name,
            serial=serial_settings,
            templates=self.command_panel.templates,
            preferences=UserPreferences(
                language=self.translator.language,
                theme=self.theme,
                display_mode=self.log_panel.display_mode,
                timestamp=True,
            ),
            log_settings={"auto_scroll": self.log_panel.auto_scroll.isChecked()},
        )

    def open_project(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, self.translator.t("open_project"), "", "ModTerm Project (*.modterm *.json)"
        )
        if not filename:
            return
        try:
            project = load_project(filename)
            self.project_path = Path(filename)
            self.project_name = project.name
            self.serial_panel.apply_settings(project.serial)
            self.command_panel.set_templates(project.templates)
            self.set_language(project.preferences.language)
            self.apply_theme(project.preferences.theme)
            self.log_panel.display_combo.setCurrentText(project.preferences.display_mode)
            self.log_panel.auto_scroll.setChecked(
                bool(project.log_settings.get("auto_scroll", True))
            )
            self._update_project_label()
            self.show_status(self.translator.t("project_loaded"))
        except (ValueError, OSError) as exc:
            self._show_error(str(exc))

    def save_project(self, _checked: bool = False, save_as: bool = False) -> None:
        if self.project_path is None or save_as:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                self.translator.t("save_project_as"),
                f"{self.project_name}.modterm",
                "ModTerm Project (*.modterm)",
            )
            if not filename:
                return
            if not filename.endswith(".modterm"):
                filename += ".modterm"
            self.project_path = Path(filename)
            self.project_name = self.project_path.stem
        try:
            write_project(self.project_path, self.project_data())
            self._update_project_label()
            self.show_status(self.translator.t("project_saved"))
        except OSError as exc:
            self._show_error(str(exc))

    def _update_project_label(self) -> None:
        self.project_label.setText(f"PROJECT: {self.project_name}")

    @staticmethod
    def _protocol_context(context: str) -> tuple[str, str, str]:
        parts = context.split("|", 2)
        protocol = parts[0]
        if len(parts) == 3:
            return protocol, parts[1], parts[2]
        if protocol == "RTU":
            return protocol, "Modbus CRC16", "little"
        if protocol == "ASCII":
            return protocol, "Modbus ASCII LRC", "big"
        return protocol, "None", "little"

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def _show_error(self, message: str) -> None:
        self.log_panel.add_error(message)
        QMessageBox.critical(self, "ModTerm", message)
        self.show_status(message)

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "ModTerm",
            f"<h2>ModTerm {__version__}</h2>"
            "<p>Industrial serial, RS-485 and Modbus RTU/ASCII workbench.</p>"
            "<p>Built with Python, PySide6 and pySerial.</p>",
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.command_panel.stop_repeat()
        self.serial_panel.shutdown()
        self._save_template_library()
        event.accept()
