from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from modterm.ui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the Qt application."""
    existing = QApplication.instance()
    if existing is not None:
        return existing
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("ModTerm")
    app.setApplicationDisplayName("ModTerm")
    app.setOrganizationName("ModTerm")
    app.setOrganizationDomain("modterm.local")
    app.setStyle("Fusion")
    QCoreApplication.setApplicationVersion("1.1.0")
    return app


def main() -> int:
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
