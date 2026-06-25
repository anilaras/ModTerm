from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_svg(source: Path, destination: Path, size: int = 512) -> None:
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise RuntimeError(f"Geçersiz SVG dosyası: {source}")

    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
    image.fill(0)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    destination.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(destination), "PNG"):
        raise RuntimeError(f"PNG dosyası yazılamadı: {destination}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Kullanım: render_icon.py SOURCE.svg DESTINATION.png", file=sys.stderr)
        return 2

    app = QGuiApplication([])
    render_svg(Path(sys.argv[1]), Path(sys.argv[2]))
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
