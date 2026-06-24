Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$PSScriptRoot\build_exe.ps1"

$BundledTesseract = Join-Path $Root "dist\POE2-P2P\tesseract"
$DefaultTesseract = "C:\Program Files\Tesseract-OCR"
if (Test-Path (Join-Path $DefaultTesseract "tesseract.exe")) {
    if (Test-Path $BundledTesseract) {
        Remove-Item $BundledTesseract -Recurse -Force
    }
    New-Item -ItemType Directory -Path $BundledTesseract | Out-Null
    Copy-Item "$DefaultTesseract\*" $BundledTesseract -Recurse -Force
    Write-Host "Bundled Tesseract from: $DefaultTesseract"
}
else {
    Write-Host "Tesseract was not found at $DefaultTesseract"
    Write-Host "Installer will be built without bundled OCR runtime."
}

$PossibleInno = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$ISCC = $PossibleInno | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ISCC) {
    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php and run this script again."
}

if (Test-Path "installer_output") {
    Remove-Item "installer_output" -Recurse -Force
}
& $ISCC ".\installer\POE2-P2P.iss"

Write-Host "Built installer: installer_output\POE2-P2P-Setup.exe"
