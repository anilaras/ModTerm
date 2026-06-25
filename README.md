# ModTerm

ModTerm is a cross-platform industrial serial terminal and Modbus RTU/ASCII
workbench for Linux and Windows. It is designed as a free, modern
Docklight-style tool for commissioning, diagnostics, RS-485 device testing
and protocol development.

The default language is English. The complete interface can be switched to
Turkish at runtime from **View → Language**.

## Features

### Serial communication

- Linux and Windows serial device discovery
- Linux device support such as `ttyUSB`, `ttyACM` and `ttyS`
- Windows COM port support such as `COM1`, `COM3` and USB serial adapters
- Port description, manufacturer and VID/PID information
- Standard and custom baud rates
- 5, 6, 7 and 8 data bits
- 1, 1.5 and 2 stop bits
- None, Even, Odd, Mark and Space parity
- Configurable read/write timeout
- Non-blocking background receive thread
- Clear connected/disconnected status

### Raw terminal

- ASCII, HEX and Binary input
- ASCII escapes: `\r`, `\n`, `\t`, `\\`, `\0`, `\xNN`
- HEX formats such as:
  - `01 03 00 00 00 02`
  - `010300000002`
  - `0x01 0x03 0x00`
- Automatic None, CR, LF or CRLF suffix
- Live ASCII, HEX, Binary or Mixed communication display
- Colored TX, RX and error records with millisecond timestamps

### Modbus RTU and Modbus ASCII

- Function 01 — Read Coils
- Function 02 — Read Discrete Inputs
- Function 03 — Read Holding Registers
- Function 04 — Read Input Registers
- Function 05 — Write Single Coil
- Function 06 — Write Single Register
- Function 0F — Write Multiple Coils
- Function 10 — Write Multiple Registers
- Custom function codes and custom HEX payloads
- Selectable checksum method per RTU and ASCII frame:
  - None
  - Modbus CRC16
  - Modbus ASCII LRC
  - XOR
  - SUM8
  - CRC-8
  - CRC-16 IBM
  - CRC-16 CCITT
- Selectable little-endian or big-endian order for 16-bit checksums
- Standards-compatible defaults: Modbus CRC16/little-endian for RTU and
  LRC for ASCII
- Automatic `:` prefix, ASCII HEX encoding and CRLF suffix in ASCII mode
- Incoming response validation using the checksum selected for the request
- Exception and response summaries in the communication log

### Custom packet builder

- Independent Custom Packet terminal
- Optional arbitrary HEX header and footer
- ASCII, HEX or Binary payload
- Selectable checksum method and 16-bit byte order
- None, CR, LF or CRLF line ending
- Live complete-frame preview
- Send, repeat and command-template integration

### Checksum calculator

- Modbus CRC16
- Modbus ASCII LRC
- XOR
- SUM8
- CRC-8
- CRC-16 IBM
- CRC-16 CCITT

### Workflow and persistence

- Single, finite repeat and infinite repeat modes
- Repeat intervals from 10 ms to 1 hour
- Named command templates with descriptions and repeat settings
- Automatic template library persistence
- `.modterm` JSON project files
- Project serial settings, templates, preferences and log settings
- Text and CSV log export
- Dark and light industrial themes
- English and Turkish interface

## Requirements

- Linux or Windows 10/11
- Python 3.11 or newer for source development
- Access permission for the target serial device

On Ubuntu/Debian, serial access commonly requires membership in `dialout`:

```bash
sudo usermod -aG dialout "$USER"
```

Sign out and back in after changing group membership.

## Development installation

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run:

```bash
modterm
```

or:

```bash
python -m modterm
```

### Windows

Open PowerShell or Command Prompt in the project directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m modterm
```

## Testing and code quality

```bash
make test
make lint
```

The test suite covers checksum reference vectors, payload parsers, Modbus RTU
and ASCII frame generation/validation, project persistence, serial service
lifetime and a real Linux pseudo-terminal read/write cycle.

## Windows EXE

PyInstaller output is operating-system-specific. A Windows `.exe` must be
built on Windows; it cannot be cross-compiled by PyInstaller from Linux.

### Build directly on Windows

Install the development dependencies as shown above, then run:

```bat
scripts\build_windows.bat
```

PowerShell users may call the underlying script directly:

```powershell
.\scripts\build_windows.ps1
```

Output:

```text
dist\windows\ModTerm-1.2.0-windows-x86_64.exe
dist\windows\ModTerm-1.2.0-windows-x86_64.exe.sha256
```

The EXE is a self-contained, windowed, single-file application:

- The target computer does not need Python or PySide6.
- The application can be started by double-clicking the EXE.
- No command prompt window is opened.
- Administrator rights are not requested.
- The first launch may take slightly longer because the single-file bundle
  extracts its runtime into a temporary directory.

### Build with GitHub Actions

Push the project to GitHub, then open:

```text
Actions → Build Windows EXE → Run workflow
```

Download the `ModTerm-Windows-x86_64` artifact after the workflow completes.
The workflow uses Windows Server 2022 and Python 3.11, runs the tests, creates
the EXE and generates its SHA-256 file.

When a version tag such as `v1.2.0` is pushed, both Windows EXE and Linux
AppImage workflows attach their output to the same GitHub Release:

```bash
git tag v1.2.0
git push origin v1.2.0
```

The generated EXE is currently unsigned. Windows SmartScreen may therefore
show an “unknown publisher” warning on downloaded copies. Removing that
warning requires a trusted Windows code-signing certificate; code signing is
intentionally not configured in the repository.

## Linux AppImage

Build a local AppImage:

```bash
make appimage
```

Output:

```text
dist/appimage/ModTerm-1.2.0-x86_64.AppImage
dist/appimage/ModTerm-1.2.0-x86_64.AppImage.sha256
```

Run it:

```bash
chmod +x dist/appimage/ModTerm-*.AppImage
./dist/appimage/ModTerm-*.AppImage
```

Without FUSE:

```bash
./dist/appimage/ModTerm-*.AppImage --appimage-extract-and-run
```

The build script packages Python, PySide6 and pySerial with PyInstaller,
creates the AppDir metadata, downloads/caches the official AppImage tools and
produces a SHA-256 file.

`x86_64` and `aarch64` build hosts are supported. AppImage binaries inherit
the glibc baseline of the build environment. For wider compatibility, use the
included GitHub Actions workflow, which builds on Ubuntu 22.04.

## Linux GitHub build

`.github/workflows/appimage.yml` runs tests and creates an AppImage artifact.
Pushing a version tag creates or updates a GitHub Release:

```bash
git tag v1.2.0
git push origin v1.2.0
```

## Project structure

```text
src/modterm/
├── core/
│   ├── checksums.py
│   ├── i18n.py
│   ├── modbus.py
│   ├── models.py
│   ├── parsers.py
│   └── serial_models.py
├── services/
│   ├── log_service.py
│   ├── persistence.py
│   └── serial_service.py
└── ui/
    ├── command_panel.py
    ├── log_panel.py
    ├── main_window.py
    ├── serial_panel.py
    ├── styles.py
    └── terminal_pages.py
```

## License

MIT
