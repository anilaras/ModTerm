from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_png(source: Path, destination: Path, size: int = 512) -> None:
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG file: {source}")

    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    destination.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(destination), "PNG"):
        raise RuntimeError(f"Could not write PNG file: {destination}")


def create_icon(source: Path, destination: Path) -> None:
    temporary_png = destination.with_suffix(".png")
    try:
        render_png(source, temporary_png)
        with Image.open(temporary_png) as image:
            image.save(
                destination,
                format="ICO",
                sizes=[
                    (16, 16),
                    (24, 24),
                    (32, 32),
                    (48, 48),
                    (64, 64),
                    (128, 128),
                    (256, 256),
                ],
            )
    finally:
        temporary_png.unlink(missing_ok=True)


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".")]
    if len(parts) > 4:
        raise ValueError("Windows version may contain at most four numeric components.")
    padded = (parts + [0] * 4)[:4]
    return padded[0], padded[1], padded[2], padded[3]


def create_version_info(destination: Path, version: str) -> None:
    numeric = version_tuple(version)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric},
    prodvers={numeric},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'ModTerm Contributors'),
          StringStruct('FileDescription', 'Industrial Serial and Modbus Workbench'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'ModTerm'),
          StringStruct('LegalCopyright', 'Copyright (c) 2026 ModTerm Contributors'),
          StringStruct('OriginalFilename', 'ModTerm.exe'),
          StringStruct('ProductName', 'ModTerm'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "Usage: render_windows_assets.py SOURCE.svg DESTINATION.ico VERSION_INFO.txt VERSION",
            file=sys.stderr,
        )
        return 2

    app = QGuiApplication([])
    create_icon(Path(sys.argv[1]), Path(sys.argv[2]))
    create_version_info(Path(sys.argv[3]), sys.argv[4])
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
