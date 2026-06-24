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

After copying the project folder to a Windows PC:

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

## Build Windows exe

On Windows PowerShell:

```powershell
.\scripts\build_exe.ps1
```

Expected output:

```text
dist\POE2-P2P\POE2-P2P.exe
```
