@echo off
setlocal
cd /d "%~dp0"

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
  set "TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if not exist ".venv\Scripts\python.exe" (
  powershell -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
)

".venv\Scripts\python.exe" -m poe2_p2p --cli
pause
