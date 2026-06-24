@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\build_installer.ps1"
pause
