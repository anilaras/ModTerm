from __future__ import annotations

DARK_STYLESHEET = """
QWidget {
    background: #111820;
    color: #d9e2ec;
    font-family: "Inter", "Noto Sans", "DejaVu Sans";
    font-size: 10pt;
}
QMainWindow, QMenuBar, QMenu, QStatusBar { background: #0c1218; }
QMenuBar::item:selected, QMenu::item:selected { background: #1d4f5c; }
#topBar, #sidePanel, #commandPanel {
    background: #151f29;
    border: 1px solid #263746;
}
#sidePanel { border-radius: 8px; }
#sectionTitle, #sectionSubtitle {
    color: #7dd3c7;
    font-weight: 700;
    letter-spacing: 1px;
}
#sectionTitle { font-size: 11pt; }
#mutedLabel { color: #8293a4; }
#separator { color: #2b3d4b; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QTableWidget, QListWidget {
    background: #0c141c;
    border: 1px solid #314554;
    border-radius: 5px;
    padding: 6px;
    selection-background-color: #176b72;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #48c9b0;
}
QHeaderView::section {
    background: #1d2a35;
    color: #9fb3c5;
    padding: 6px;
    border: 0;
    border-right: 1px solid #314554;
}
QTabWidget::pane { border: 1px solid #2b3d4b; border-radius: 5px; }
QTabBar::tab {
    background: #18242e;
    color: #91a5b7;
    padding: 10px 16px;
    border: 1px solid #263746;
}
QTabBar::tab:selected { background: #1d4f5c; color: white; }
QPushButton {
    background: #1e5963;
    border: 1px solid #347b82;
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #28717a; }
QPushButton:pressed { background: #16434b; }
QPushButton:disabled { background: #25323c; color: #647585; border-color: #34434f; }
#secondaryButton { background: #263746; }
#dangerButton { background: #7f2d38; border-color: #a9414e; }
#connectButton { background: #167c67; font-weight: 800; letter-spacing: 1px; }
#connectButton[connected="true"] { background: #9c3845; border-color: #c64b5a; }
QLabel[connected="true"] {
    background: #164f44; color: #78e4c5; border: 1px solid #2d8f78;
    border-radius: 5px; font-weight: 700;
}
QLabel[connected="false"] {
    background: #3b252a; color: #f5a3ac; border: 1px solid #75414a;
    border-radius: 5px; font-weight: 700;
}
QGroupBox {
    border: 1px solid #2b3d4b;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
    font-weight: 700;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #7dd3c7; }
QScrollBar:vertical { background: #111820; width: 12px; }
QScrollBar::handle:vertical { background: #3b5363; border-radius: 5px; min-height: 24px; }
"""

LIGHT_STYLESHEET = """
QWidget {
    background: #eef2f5;
    color: #1c2934;
    font-family: "Inter", "Noto Sans", "DejaVu Sans";
    font-size: 10pt;
}
QMainWindow, QMenuBar, QMenu, QStatusBar { background: #dde5ea; }
#topBar, #sidePanel, #commandPanel { background: #f8fafb; border: 1px solid #c5d0d8; }
#sectionTitle, #sectionSubtitle { color: #116a70; font-weight: 700; letter-spacing: 1px; }
#mutedLabel { color: #617482; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QTableWidget, QListWidget {
    background: white; border: 1px solid #aebcc6; border-radius: 5px; padding: 6px;
}
QHeaderView::section { background: #dce6eb; padding: 6px; border: 0; }
QTabBar::tab { background: #dce6eb; padding: 10px 16px; }
QTabBar::tab:selected { background: #17777d; color: white; }
QPushButton {
    background: #17777d; color: white; border: 0; border-radius: 5px;
    padding: 7px 14px; font-weight: 600;
}
#secondaryButton { background: #607d8b; }
#dangerButton { background: #a53d4a; }
#connectButton[connected="true"] { background: #a53d4a; }
QLabel[connected="true"] {
    background: #d5f5eb; color: #11634f; border-radius: 5px; font-weight: 700;
}
QLabel[connected="false"] {
    background: #f8dfe2; color: #842f3a; border-radius: 5px; font-weight: 700;
}
QGroupBox {
    border: 1px solid #bdc9d1; border-radius: 6px; margin-top: 10px;
    padding-top: 12px; font-weight: 700;
}
"""
