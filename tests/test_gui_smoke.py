from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from modterm.app import create_application
    from modterm.ui.main_window import MainWindow
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise
    create_application = None
    MainWindow = None


@unittest.skipIf(create_application is None, "PySide6 kurulu değil")
class GuiSmokeTests(unittest.TestCase):
    def test_main_window_can_be_created(self) -> None:
        app = create_application([])
        window = MainWindow()

        self.assertIn("Industrial Serial", window.windowTitle())
        self.assertEqual(window.centralWidget().count(), 3)
        self.assertEqual(window.tabs.count(), 6)

        window.close()
        app.quit()


if __name__ == "__main__":
    unittest.main()
