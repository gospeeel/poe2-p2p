Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv")) {
    try {
        py -3.11 -m venv .venv
    }
    catch {
        python -m venv .venv
    }
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
if (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
    $env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
}
& .\.venv\Scripts\python.exe -m PyInstaller .\POE2-P2P.spec --clean --noconfirm

Write-Host "Built: dist\POE2-P2P\POE2-P2P.exe"
