Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv")) {
    try {
        py -3.11 -m venv .venv
    }
    catch {
        python -m venv .venv
    }
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt -r requirements-build.txt

$DefaultTesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (Test-Path $DefaultTesseract) {
    Write-Host "Tesseract found: $DefaultTesseract"
}
else {
    Write-Host "Tesseract was not found at default path: $DefaultTesseract"
    Write-Host "Set TESSERACT_CMD before running OCR if your path is different."
}

Write-Host "Setup complete."
