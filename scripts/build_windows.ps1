param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($Python)) {
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        $Python = $VenvPython
    }
    else {
        $Python = "python"
    }
}

$Platform = & $Python -c "import platform; print(platform.system())"
if ($LASTEXITCODE -ne 0 -or $Platform.Trim() -ne "Windows") {
    throw "Windows EXE must be built on Windows. Run this script in Windows or use GitHub Actions."
}

$Version = (& $Python -c "import pathlib,tomllib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])").Trim()
$Machine = (& $Python -c "import platform; print(platform.machine())").Trim().ToLowerInvariant()

switch ($Machine) {
    { $_ -in @("amd64", "x86_64") } { $Architecture = "x86_64"; break }
    { $_ -in @("arm64", "aarch64") } { $Architecture = "arm64"; break }
    default { throw "Unsupported Windows architecture: $Machine" }
}

& $Python -c "import PyInstaller, PySide6, serial, PIL"
if ($LASTEXITCODE -ne 0) {
    throw "Missing build dependencies. Run: python -m pip install -e '.[dev]'"
}

$BuildRoot = Join-Path $ProjectRoot "build\windows"
$OutputDir = Join-Path $ProjectRoot "dist\windows"
$IconFile = Join-Path $BuildRoot "modterm.ico"
$VersionFile = Join-Path $BuildRoot "version_info.txt"
$TemporaryExe = Join-Path $OutputDir "ModTerm.exe"
$OutputName = "ModTerm-$Version-windows-$Architecture.exe"
$OutputFile = Join-Path $OutputDir $OutputName
$ChecksumFile = "$OutputFile.sha256"

Write-Host "Building ModTerm $Version Windows EXE ($Architecture)..."

Remove-Item $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $OutputDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item $BuildRoot -ItemType Directory -Force | Out-Null
New-Item $OutputDir -ItemType Directory -Force | Out-Null

$env:QT_QPA_PLATFORM = "offscreen"
& $Python packaging\render_windows_assets.py `
    packaging\modterm.svg `
    $IconFile `
    $VersionFile `
    $Version
if ($LASTEXITCODE -ne 0) {
    throw "Windows icon or version metadata generation failed."
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $OutputDir `
    --workpath (Join-Path $BuildRoot "pyinstaller") `
    packaging\modterm-windows.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller Windows build failed."
}

if (-not (Test-Path $TemporaryExe)) {
    throw "Expected executable was not generated: $TemporaryExe"
}

Move-Item $TemporaryExe $OutputFile -Force
$Hash = (Get-FileHash $OutputFile -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $OutputName" | Set-Content $ChecksumFile -Encoding ascii

Write-Host ""
Write-Host "Windows executable ready:"
Write-Host $OutputFile
Write-Host $ChecksumFile

