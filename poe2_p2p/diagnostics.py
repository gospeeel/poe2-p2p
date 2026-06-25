from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import platform
import sys
import traceback

from . import __version__
from .calibration import MARKET_RATIO, load_calibration_profile
from .capture import CaptureDependencyError, capture_screen_region
from .logging_utils import LOG_DIR
from .ocr import OCRDependencyError, detect_tesseract_cmd, read_ratio_from_image


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    details: str


@dataclass(frozen=True)
class DiagnosticReport:
    checks: tuple[DiagnosticCheck, ...]
    report_path: Path
    live_capture_requested: bool = False

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def text(self) -> str:
        lines = [
            "# Диагностика POE2 P2P",
            "",
            f"Время: {datetime.now(UTC).isoformat()}",
            f"Версия приложения: {__version__}",
            f"Python: {sys.version.split()[0]}",
            f"Система: {platform.platform()}",
            "",
            "## Проверки",
            "",
        ]
        for check in self.checks:
            status = "ОК" if check.ok else "Ошибка"
            lines.append(f"- {status}: {check.name} - {check.details}")
        lines.extend(
            [
                "",
                "## Статус оставшихся TODO",
                "",
                *self._validation_lines(),
            ]
        )
        lines.extend(
            [
                "",
                "## Что отправить разработчику",
                "",
                "1. Этот файл отчета.",
                "2. Скриншот окна NPC Currency Exchange.",
                "3. Текст из вкладки `Скан`, если проверялась живая OCR-область.",
            ]
        )
        return "\n".join(lines)

    def _validation_lines(self) -> list[str]:
        windows = platform.system().lower() == "windows"
        packaged = bool(getattr(sys, "frozen", False))
        dependencies_ok = _check_named(self.checks, "Зависимости Python")
        calibration_ok = _check_named(self.checks, "Калибровка")
        live_screenshot_ok = _check_named(self.checks, "Живой снимок")
        live_ocr_ok = _check_named(self.checks, "Живое распознавание Market Ratio")

        return [
            _todo_line(
                "Проверить запуск на чистой Windows-машине",
                windows and packaged,
                "запусти установленный POE2-P2P.exe и приложи этот отчет",
            ),
            _todo_line(
                "Проверка overlay на Windows",
                windows and dependencies_ok,
                "окно должно открыться, скрываться в трей и закрываться без диспетчера задач",
            ),
            _todo_line(
                "OCR курса на живом снимке",
                self.live_capture_requested and calibration_ok and live_screenshot_ok and live_ocr_ok,
                "открой NPC Currency Exchange, сохрани калибровку Market Ratio и запусти диагностику с живым снимком",
            ),
            "- Требует ручного подтверждения: проверка NPC в игре - сравни распознанный Market Ratio с тем, что видно в игре, и проверь расчет в таблице.",
        ]


def run_diagnostics(
    *,
    live_capture: bool = False,
    report_path: str | Path | None = None,
) -> DiagnosticReport:
    checks: list[DiagnosticCheck] = []
    checks.append(_check_imports())
    checks.append(_check_tesseract())
    checks.append(_check_calibration())
    checks.append(_check_logs_dir())
    if live_capture:
        checks.extend(_check_live_capture())

    path = Path(report_path) if report_path else _default_report_path()
    report = DiagnosticReport(
        checks=tuple(checks),
        report_path=path,
        live_capture_requested=live_capture,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.text, encoding="utf-8")
    return report


def _check_imports() -> DiagnosticCheck:
    missing = []
    for module_name in ("PySide6", "PIL", "mss", "cv2", "pytesseract"):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        return DiagnosticCheck(
            "Зависимости Python",
            False,
            "Не найдены пакеты: " + ", ".join(missing),
        )
    return DiagnosticCheck("Зависимости Python", True, "Все основные пакеты доступны.")


def _check_tesseract() -> DiagnosticCheck:
    tesseract = detect_tesseract_cmd()
    if not tesseract:
        return DiagnosticCheck(
            "Tesseract OCR",
            False,
            "Не найден исполняемый файл Tesseract. Проверь установку или переменную TESSERACT_CMD.",
        )
    return DiagnosticCheck("Tesseract OCR", True, f"Найден: {tesseract}")


def _check_calibration() -> DiagnosticCheck:
    path = Path("calibration.json")
    if not path.exists():
        return DiagnosticCheck(
            "Калибровка",
            False,
            "Файл calibration.json не найден. Открой `Калибровка` и сохрани области.",
        )
    try:
        profile = load_calibration_profile(path)
    except Exception as error:
        return DiagnosticCheck("Калибровка", False, f"Не удалось прочитать calibration.json: {error}")
    region = profile.regions.get(MARKET_RATIO)
    if not region:
        return DiagnosticCheck("Калибровка", False, "В профиле нет области Market Ratio.")
    return DiagnosticCheck(
        "Калибровка",
        True,
        f"Профиль `{profile.name}`, Market Ratio: {region.x},{region.y},{region.width},{region.height}",
    )


def _check_logs_dir() -> DiagnosticCheck:
    try:
        LOG_DIR.mkdir(exist_ok=True)
        probe = LOG_DIR / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as error:
        return DiagnosticCheck("Запись файлов", False, f"Нет доступа к папке логов: {error}")
    return DiagnosticCheck("Запись файлов", True, f"Папка доступна: {LOG_DIR.resolve()}")


def _check_live_capture() -> list[DiagnosticCheck]:
    checks = []
    path = Path("calibration.json")
    if not path.exists():
        return [
            DiagnosticCheck(
                "Живой снимок",
                False,
                "Нельзя проверить живой снимок без calibration.json.",
            )
        ]
    try:
        profile = load_calibration_profile(path)
        region = profile.regions[MARKET_RATIO]
        output = LOG_DIR / "diagnostics-market-ratio.png"
        capture_screen_region(region, output)
        checks.append(
            DiagnosticCheck(
                "Живой снимок",
                True,
                f"Снимок области Market Ratio сохранен: {output.resolve()}",
            )
        )
        result = read_ratio_from_image(output)
        left, right = result.ratio
        checks.append(
            DiagnosticCheck(
                "Живое распознавание Market Ratio",
                True,
                f"Распознано `{result.raw_text}` как {left:g} : {right:g}, уверенность {result.confidence:.2f}.",
            )
        )
    except (CaptureDependencyError, OCRDependencyError, ValueError, KeyError, OSError) as error:
        checks.append(
            DiagnosticCheck(
                "Живой снимок и OCR",
                False,
                f"{error}",
            )
        )
    except Exception:
        checks.append(
            DiagnosticCheck(
                "Живой снимок и OCR",
                False,
                traceback.format_exc(limit=3),
            )
        )
    return checks


def _default_report_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return LOG_DIR / f"diagnostics-{stamp}.md"


def _check_named(checks: tuple[DiagnosticCheck, ...], name: str) -> bool:
    return any(check.name == name and check.ok for check in checks)


def _todo_line(name: str, ok: bool, hint: str) -> str:
    status = "можно закрыть" if ok else "нужно проверить"
    return f"- {status}: {name} - {hint}."
