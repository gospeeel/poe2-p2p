# POE2 P2P

Prototype for a lightweight POE2 Currency Exchange arbitrage overlay.

## What Can Be Tested Here

On this development machine you can verify:

- core arbitrage calculation;
- poe.ninja candidate fetching;
- crop/OCR code paths, if Tesseract is installed;
- PySide6 overlay in test/offscreen mode;
- PyInstaller spec smoke-test for the current OS.

Windows-only checks still need a Windows PC:

- real `.exe` output;
- overlay above POE2;
- live screen capture coordinates;
- live NPC validation.

## Windows Quick Start

For normal users, do not download `Source code.zip`.

Download the ready installer from GitHub Releases:

```text
POE2-P2P-Setup.exe
```

Then:

```text
Run POE2-P2P-Setup.exe
Install
Launch POE2 P2P from Start Menu or Desktop shortcut
```

## Диагностика на Windows

После установки открой приложение и нажми:

```text
Настройки -> Диагностика
```

Приложение создаст отчет в папке `logs`. В отчете проверяются:

- доступность Tesseract OCR;
- наличие калибровки;
- возможность записи логов;
- живой снимок области `Market Ratio`;
- OCR живого снимка, если область калибровки настроена.
- статус оставшихся TODO, которые можно закрыть после Windows/live проверки.

То же самое можно запустить из PowerShell:

```powershell
.\POE2-P2P.exe --diagnostics --diagnostics-live
```

Если проверка нужна без живого снимка:

```powershell
.\POE2-P2P.exe --diagnostics
```

Для проверки NPC в игре дополнительно сравни глазами:

- текст `Market Ratio` в игре;
- строку `Живое распознавание Market Ratio` в отчете;
- итоговую связку и профит в таблице приложения.

Для полной проверки Windows-запуска можно использовать готовый скрипт из корня проекта:

```text
validate_windows.bat
```

Он найдет установленный `POE2-P2P.exe` или локальный `dist\POE2-P2P\POE2-P2P.exe`, запустит диагностику, создаст `logs\windows-validation.md` и предложит вручную проверить окно, трей и закрытие приложения.

Developer/manual setup after copying the project folder to a Windows PC:

1. Install Tesseract OCR.
   Recommended installer: `https://github.com/UB-Mannheim/tesseract/wiki`

2. Double-click:

```text
setup_windows.ps1
```

If Windows blocks script execution, right-click the project folder and open PowerShell there:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

3. Run the app without building exe:

```text
run_app.bat
```

4. Build portable Windows exe:

```text
build_exe.bat
```

Expected output:

```text
dist\POE2-P2P\POE2-P2P.exe
```

## Build Windows Installer

For a user-friendly install flow, build an installer on Windows or let GitHub Actions build it.

### Option A: GitHub Releases

Push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions will build:

```text
POE2-P2P-Setup.exe
```

and attach it to the GitHub Release for that tag.

You can also run the workflow manually from:

```text
GitHub -> Actions -> Build Windows Installer -> Run workflow
```

In that case the installer is available as a workflow artifact.

### Option B: Local Windows Build

1. Install Inno Setup 6:

```text
https://jrsoftware.org/isinfo.php
```

2. Install Tesseract OCR on the build machine if you want OCR bundled into the installer:

```text
https://github.com/UB-Mannheim/tesseract/wiki
```

3. Run:

```text
build_installer.bat
```

Expected output:

```text
installer_output\POE2-P2P-Setup.exe
```

End-user flow:

```text
Download POE2-P2P-Setup.exe
Run installer
Launch POE2 P2P from Start Menu or Desktop shortcut
```

If Tesseract exists at `C:\Program Files\Tesseract-OCR` during installer build, it is copied into the app folder and OCR works without a separate user install.

If Tesseract is installed in the default location, the launchers set it automatically:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If your Tesseract path is different, set:

```powershell
$env:TESSERACT_CMD = "D:\Your\Path\tesseract.exe"
```

## Run CLI MVP

```bash
python3 -m poe2_p2p --cli
```

The CLI uses sample rates derived from the screenshots in this directory.

## Run Overlay

```bash
pip install -r requirements.txt
python3 -m poe2_p2p
```

If `PySide6` is not installed, use `--cli`.

## Current MVP Scope

- sample rates from screenshots;
- directed graph exchange model;
- cycle search from `Exalted Orb`;
- opportunity ranking by net profit and ROI;
- SQLite storage for scanned rates and opportunities;
- optional PySide6 always-on-top table window.

## OCR/Crop Commands

Parse a ratio string:

```bash
python3 -m poe2_p2p --ratio-text "1 : 2050"
```

Crop the default Market Ratio area from a screenshot:

```bash
python3 -m poe2_p2p --crop-image Screenshot_1.jpg --crop-output ratio_crop.png
```

Run OCR on a cropped ratio image:

```bash
python3 -m poe2_p2p --ocr-image ratio_crop.png
```

Save/load calibration:

```bash
python3 -m poe2_p2p --region 385,122,90,18 --save-calibration calibration.json
python3 -m poe2_p2p --load-calibration calibration.json --crop-image Screenshot_1.jpg
```

Export opportunities and alerts:

```bash
python3 -m poe2_p2p --export-csv opportunities.csv
python3 -m poe2_p2p --alert-profit 100 --alert-roi 2
python3 -m poe2_p2p --history 10
python3 -m poe2_p2p --history-dashboard history.html
```

Cache icons from poe.ninja:

```bash
python3 -m poe2_p2p --cache-icons --candidate-limit 100
```

## Build Windows exe

On Windows PowerShell:

```powershell
.\scripts\build_exe.ps1
```

Expected output:

```text
dist\POE2-P2P\POE2-P2P.exe
```
