param(
    [string]$ExePath = "",
    [switch]$SkipLive,
    [switch]$SkipLaunch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Write-Step($Message) {
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Find-AppExe {
    param([string]$ExplicitPath)

    $Candidates = @()
    if ($ExplicitPath) {
        $Candidates += $ExplicitPath
    }
    $Candidates += Join-Path $Root "dist\POE2-P2P\POE2-P2P.exe"
    $Candidates += Join-Path $env:ProgramFiles "POE2 P2P\POE2-P2P.exe"
    if (${env:ProgramFiles(x86)}) {
        $Candidates += Join-Path ${env:ProgramFiles(x86)} "POE2 P2P\POE2-P2P.exe"
    }
    $Candidates += Join-Path $env:LOCALAPPDATA "Programs\POE2 P2P\POE2-P2P.exe"

    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path $Candidate)) {
            return (Resolve-Path $Candidate).Path
        }
    }
    return ""
}

function Find-Python {
    $LocalPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $LocalPython) {
        return (Resolve-Path $LocalPython).Path
    }
    return ""
}

Write-Step "Проверка POE2 P2P на Windows"

$DefaultTesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (Test-Path $DefaultTesseract) {
    $env:TESSERACT_CMD = $DefaultTesseract
    Write-Host "Tesseract OCR найден: $DefaultTesseract"
}
else {
    Write-Host "Tesseract OCR не найден по стандартному пути: $DefaultTesseract" -ForegroundColor Yellow
}

$LogsDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
$ReportPath = Join-Path $LogsDir "windows-validation.md"

$AppExe = Find-AppExe $ExePath
$Python = Find-Python

Write-Step "Диагностика"
if ($AppExe) {
    Write-Host "Найден exe: $AppExe"
    $Args = @("--diagnostics", "--diagnostics-output", $ReportPath)
    if (-not $SkipLive) {
        $Args += "--diagnostics-live"
    }
    & $AppExe @Args
}
elseif ($Python) {
    Write-Host "Exe не найден, используется локальное Python-окружение: $Python" -ForegroundColor Yellow
    $Args = @("-m", "poe2_p2p", "--diagnostics", "--diagnostics-output", $ReportPath)
    if (-not $SkipLive) {
        $Args += "--diagnostics-live"
    }
    & $Python @Args
}
else {
    Write-Host "Не найден ни установленный exe, ни .venv\Scripts\python.exe." -ForegroundColor Red
    Write-Host "Запусти установщик или setup_windows.ps1, затем повтори проверку."
    exit 2
}

Write-Step "Ручная проверка окна приложения"
if (-not $SkipLaunch) {
    if ($AppExe) {
        Start-Process -FilePath $AppExe
    }
    elseif ($Python) {
        Start-Process -FilePath $Python -ArgumentList "-m", "poe2_p2p" -WorkingDirectory $Root
    }
    Write-Host "Проверь окно приложения:"
    Write-Host "1. Окно открывается поверх игры или рабочего стола."
    Write-Host "2. Кнопка «Скрыть» убирает окно в трей."
    Write-Host "3. Пункт «Выход» в трее завершает приложение без диспетчера задач."
    Write-Host "4. Кнопка «Диагностика» в настройках создает отчет."
    Read-Host "Нажми Enter после ручной проверки"
}

Write-Step "Готово"
Write-Host "Отчет диагностики: $ReportPath"
if (Test-Path $ReportPath) {
    Start-Process explorer.exe "/select,`"$ReportPath`""
}
Write-Host "Пришли файл отчета и результат ручной проверки окна приложения."
