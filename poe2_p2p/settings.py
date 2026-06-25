from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


DEFAULT_SETTINGS_PATH = Path("settings.json")


@dataclass
class AppSettings:
    hotkeys: dict[str, str] = field(
        default_factory=lambda: {
            "scan_pair": "Ctrl+1",
            "toggle_overlay": "Ctrl+H",
            "scan_candidates": "Ctrl+2",
            "pause_resume": "Ctrl+P",
        }
    )
    opacity: int = 94
    always_on_top: bool = True
    click_through: bool = False
    ui_scale_percent: int = 100
    first_run_complete: bool = False
    league: str = "Runes of Aldur"


ACTION_LABELS = {
    "scan_pair": "Скан пары",
    "toggle_overlay": "Показать/скрыть окно",
    "scan_candidates": "Скан кандидатов",
    "pause_resume": "Пауза/продолжить",
}


def load_settings(path: str | Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    settings_path = Path(path)
    if not settings_path.exists():
        return AppSettings()
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    settings = AppSettings()
    settings.hotkeys.update(data.get("hotkeys", {}))
    settings.opacity = int(data.get("opacity", settings.opacity))
    settings.always_on_top = bool(data.get("always_on_top", settings.always_on_top))
    settings.click_through = bool(data.get("click_through", settings.click_through))
    settings.ui_scale_percent = int(data.get("ui_scale_percent", settings.ui_scale_percent))
    settings.first_run_complete = bool(data.get("first_run_complete", settings.first_run_complete))
    settings.league = str(data.get("league", settings.league))
    return settings


def save_settings(settings: AppSettings, path: str | Path = DEFAULT_SETTINGS_PATH) -> None:
    Path(path).write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_hotkey_conflicts(hotkeys: dict[str, str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for action, value in hotkeys.items():
        normalized = value.strip().lower()
        if not normalized:
            continue
        buckets.setdefault(normalized, []).append(action)
    return {key: actions for key, actions in buckets.items() if len(actions) > 1}
