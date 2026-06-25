#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
APP_NAME="ModTerm"

if [[ ! -x "$PYTHON" ]]; then
    echo "Python ortamı bulunamadı: $PYTHON" >&2
    echo "Önce README içindeki geliştirme bağımlılıklarını kurun." >&2
    exit 1
fi

PYTHON_ARCH="$("$PYTHON" -c 'import platform; print(platform.machine())')"
VERSION="$("$PYTHON" -c \
    'import pathlib, tomllib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])')"

case "$PYTHON_ARCH" in
    x86_64|amd64)
        APPIMAGE_ARCH="x86_64"
        ;;
    aarch64|arm64)
        APPIMAGE_ARCH="aarch64"
        ;;
    *)
        echo "Desteklenmeyen mimari: $PYTHON_ARCH" >&2
        exit 1
        ;;
esac

if ! "$PYTHON" -c 'import PyInstaller, PySide6, serial' >/dev/null 2>&1; then
    echo "Eksik build bağımlılıkları var." >&2
    echo "\"$PYTHON\" -m pip install -e '.[dev]' komutunu çalıştırın." >&2
    exit 1
fi

BUILD_ROOT="$PROJECT_ROOT/build/appimage"
PYINSTALLER_DIST="$PROJECT_ROOT/dist"
APPDIR="$BUILD_ROOT/${APP_NAME}.AppDir"
OUTPUT_DIR="$PROJECT_ROOT/dist/appimage"
OUTPUT_FILE="$OUTPUT_DIR/${APP_NAME}-${VERSION}-${APPIMAGE_ARCH}.AppImage"
ICON_PNG="$BUILD_ROOT/modterm.png"
APPIMAGETOOL="$PROJECT_ROOT/tools/appimagetool-${APPIMAGE_ARCH}.AppImage"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${APPIMAGE_ARCH}.AppImage"
RUNTIME_FILE="$PROJECT_ROOT/tools/runtime-${APPIMAGE_ARCH}"
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-${APPIMAGE_ARCH}"

download_file() {
    local url="$1"
    local destination="$2"

    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --retry 3 --output "${destination}.part" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget --output-document="${destination}.part" "$url"
    else
        echo "Dosya indirmek için curl veya wget gerekiyor." >&2
        exit 1
    fi

    mv "${destination}.part" "$destination"
}

echo "ModTerm ${VERSION} AppImage hazırlanıyor (${APPIMAGE_ARCH})..."

rm -rf "$APPDIR" "$PYINSTALLER_DIST/modterm"
mkdir -p "$BUILD_ROOT" "$OUTPUT_DIR" "$PROJECT_ROOT/tools"

QT_QPA_PLATFORM=offscreen "$PYTHON" \
    packaging/render_icon.py packaging/modterm.svg "$ICON_PNG"

"$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$PYINSTALLER_DIST" \
    --workpath "$BUILD_ROOT/pyinstaller" \
    packaging/modterm.spec

mkdir -p \
    "$APPDIR/usr/bin" \
    "$APPDIR/usr/lib/modterm" \
    "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/icons/hicolor/512x512/apps"

cp -a "$PYINSTALLER_DIST/modterm/." "$APPDIR/usr/lib/modterm/"
cp packaging/AppRun "$APPDIR/AppRun"
cp packaging/modterm.desktop "$APPDIR/modterm.desktop"
cp packaging/modterm.desktop "$APPDIR/usr/share/applications/modterm.desktop"
cp "$ICON_PNG" "$APPDIR/modterm.png"
cp "$ICON_PNG" "$APPDIR/usr/share/icons/hicolor/512x512/apps/modterm.png"
ln -sfn modterm.png "$APPDIR/.DirIcon"

cat >"$APPDIR/usr/bin/modterm" <<'EOF'
#!/bin/sh
set -eu
APPDIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
exec "$APPDIR/usr/lib/modterm/modterm" "$@"
EOF

chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/modterm"

if [[ ! -x "$APPIMAGETOOL" ]]; then
    echo "appimagetool indiriliyor..."
    download_file "$APPIMAGETOOL_URL" "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
fi

if [[ ! -f "$RUNTIME_FILE" ]]; then
    echo "AppImage runtime indiriliyor..."
    download_file "$RUNTIME_URL" "$RUNTIME_FILE"
fi

rm -f "$OUTPUT_FILE"
ARCH="$APPIMAGE_ARCH" APPIMAGE_EXTRACT_AND_RUN=1 \
    "$APPIMAGETOOL" \
    --no-appstream \
    --runtime-file "$RUNTIME_FILE" \
    "$APPDIR" \
    "$OUTPUT_FILE"
chmod +x "$OUTPUT_FILE"
(
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$OUTPUT_FILE")" >"$(basename "$OUTPUT_FILE").sha256"
)

echo
echo "AppImage hazır:"
echo "$OUTPUT_FILE"
echo "$OUTPUT_FILE.sha256"
