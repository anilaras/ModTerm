from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from modterm.core.i18n import TranslationManager
from modterm.core.models import CommandTemplate, RepeatSettings


class CommandLibraryPanel(QFrame):
    add_requested = Signal(str)
    update_requested = Signal(int, str)
    delete_requested = Signal(int)
    load_requested = Signal(int)
    repeat_send_requested = Signal()
    repeat_stopped = Signal()

    def __init__(self, translator: TranslationManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("commandPanel")
        self._tr = translator
        self._templates: list[CommandTemplate] = []
        self._remaining = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._build_ui()
        self._tr.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(10)

        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        layout.addWidget(self.title)

        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(
            lambda _item: self.load_requested.emit(self.template_list.currentRow())
        )
        layout.addWidget(self.template_list, 1)

        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        self.description_edit = QLineEdit()
        layout.addWidget(self.description_edit)

        row = QHBoxLayout()
        self.add_button = QPushButton()
        self.update_button = QPushButton()
        self.delete_button = QPushButton()
        self.delete_button.setObjectName("dangerButton")
        row.addWidget(self.add_button)
        row.addWidget(self.update_button)
        row.addWidget(self.delete_button)
        layout.addLayout(row)

        self.load_button = QPushButton()
        self.load_button.setObjectName("secondaryButton")
        layout.addWidget(self.load_button)

        self.add_button.clicked.connect(lambda: self.add_requested.emit(self.name_edit.text()))
        self.update_button.clicked.connect(
            lambda: self.update_requested.emit(
                self.template_list.currentRow(), self.name_edit.text()
            )
        )
        self.delete_button.clicked.connect(
            lambda: self.delete_requested.emit(self.template_list.currentRow())
        )
        self.load_button.clicked.connect(
            lambda: self.load_requested.emit(self.template_list.currentRow())
        )
        self.template_list.currentRowChanged.connect(self._selection_changed)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        self.repeat_title = QLabel()
        self.repeat_title.setObjectName("sectionTitle")
        layout.addWidget(self.repeat_title)

        self.interval_label = QLabel()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 3_600_000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        self.count_label = QLabel()
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1_000_000)
        self.count_spin.setValue(1)
        self.infinite_check = QCheckBox()
        self.infinite_check.toggled.connect(self.count_spin.setDisabled)

        for label, widget in (
            (self.interval_label, self.interval_spin),
            (self.count_label, self.count_spin),
        ):
            line = QHBoxLayout()
            line.addWidget(label)
            line.addStretch()
            line.addWidget(widget)
            layout.addLayout(line)
        layout.addWidget(self.infinite_check)

        repeat_row = QHBoxLayout()
        self.start_button = QPushButton()
        self.stop_button = QPushButton()
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_repeat)
        self.stop_button.clicked.connect(self.stop_repeat)
        repeat_row.addWidget(self.start_button)
        repeat_row.addWidget(self.stop_button)
        layout.addLayout(repeat_row)

    def retranslate_ui(self) -> None:
        t = self._tr.t
        self.title.setText(t("templates"))
        self.name_edit.setPlaceholderText(t("template_name"))
        self.description_edit.setPlaceholderText(t("template_description"))
        self.add_button.setText(t("add"))
        self.update_button.setText(t("update"))
        self.delete_button.setText(t("delete"))
        self.load_button.setText(t("load"))
        self.repeat_title.setText(t("repeat"))
        self.interval_label.setText(t("interval"))
        self.count_label.setText(t("count"))
        self.infinite_check.setText(t("infinite"))
        self.start_button.setText(t("start"))
        self.stop_button.setText(t("stop"))

    @property
    def templates(self) -> list[CommandTemplate]:
        return list(self._templates)

    def set_templates(self, templates: list[CommandTemplate]) -> None:
        self._templates = list(templates)
        self.template_list.clear()
        self.template_list.addItems(template.name for template in templates)

    def append_template(self, template: CommandTemplate) -> None:
        self._templates.append(template)
        self.template_list.addItem(template.name)
        self.template_list.setCurrentRow(len(self._templates) - 1)

    def replace_template(self, index: int, template: CommandTemplate) -> None:
        if not 0 <= index < len(self._templates):
            raise ValueError("Select a template to update.")
        self._templates[index] = template
        self.template_list.item(index).setText(template.name)

    def remove_template(self, index: int) -> None:
        if not 0 <= index < len(self._templates):
            raise ValueError("Select a template to delete.")
        del self._templates[index]
        self.template_list.takeItem(index)

    def selected_template(self, index: int | None = None) -> CommandTemplate:
        selected = self.template_list.currentRow() if index is None else index
        if not 0 <= selected < len(self._templates):
            raise ValueError("Select a template first.")
        return self._templates[selected]

    def _selection_changed(self, index: int) -> None:
        if 0 <= index < len(self._templates):
            template = self._templates[index]
            self.name_edit.setText(template.name)
            self.description_edit.setText(template.description)
            self.apply_repeat_settings(template.repeat)

    def repeat_settings(self) -> RepeatSettings:
        return RepeatSettings(
            interval_ms=self.interval_spin.value(),
            count=self.count_spin.value(),
            infinite=self.infinite_check.isChecked(),
        )

    def apply_repeat_settings(self, settings: RepeatSettings) -> None:
        self.interval_spin.setValue(settings.interval_ms)
        self.count_spin.setValue(max(1, settings.count))
        self.infinite_check.setChecked(settings.infinite)

    def start_repeat(self) -> None:
        settings = self.repeat_settings()
        self._remaining = settings.count
        self._timer.start(settings.interval_ms)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.repeat_send_requested.emit()
        if not settings.infinite:
            self._remaining -= 1
            if self._remaining <= 0:
                self.stop_repeat()

    def _tick(self) -> None:
        self.repeat_send_requested.emit()
        if not self.infinite_check.isChecked():
            self._remaining -= 1
            if self._remaining <= 0:
                self.stop_repeat()

    def stop_repeat(self) -> None:
        self._timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.repeat_stopped.emit()
