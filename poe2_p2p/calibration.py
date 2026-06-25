from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from .config import DEFAULT_MARKET_RATIO_REGION, CropRegion


MARKET_RATIO = "market_ratio"
LEFT_ITEM = "left_item"
RIGHT_ITEM = "right_item"
LEFT_AMOUNT = "left_amount"
RIGHT_AMOUNT = "right_amount"
CURRENT_VALUE = "current_value"

REGION_LABELS = {
    MARKET_RATIO: "Market Ratio",
    LEFT_ITEM: "Левый предмет",
    RIGHT_ITEM: "Правый предмет",
    LEFT_AMOUNT: "Левое количество",
    RIGHT_AMOUNT: "Правое количество",
    CURRENT_VALUE: "Красное текущее значение",
}


@dataclass
class CalibrationProfile:
    name: str = "Основной"
    resolution_width: int = 1280
    resolution_height: int = 720
    ui_scale_percent: int = 100
    regions: dict[str, CropRegion] = field(
        default_factory=lambda: {MARKET_RATIO: DEFAULT_MARKET_RATIO_REGION}
    )


def save_region(path: str | Path, region: CropRegion) -> None:
    profile = default_calibration_profile()
    profile.regions[MARKET_RATIO] = region
    save_calibration_profile(path, profile)


def load_region(path: str | Path) -> CropRegion:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "regions" in data:
        profile = _profile_from_dict(data)
        return profile.regions.get(MARKET_RATIO, DEFAULT_MARKET_RATIO_REGION)
    return CropRegion(
        x=int(data["x"]),
        y=int(data["y"]),
        width=int(data["width"]),
        height=int(data["height"]),
    )


def default_calibration_profile() -> CalibrationProfile:
    return CalibrationProfile(
        regions={
            MARKET_RATIO: DEFAULT_MARKET_RATIO_REGION,
            LEFT_ITEM: CropRegion(220, 88, 145, 24),
            RIGHT_ITEM: CropRegion(490, 88, 145, 24),
            LEFT_AMOUNT: CropRegion(250, 122, 70, 20),
            RIGHT_AMOUNT: CropRegion(580, 122, 70, 20),
            CURRENT_VALUE: CropRegion(610, 146, 80, 20),
        }
    )


def save_calibration_profile(path: str | Path, profile: CalibrationProfile) -> None:
    data = {
        "name": profile.name,
        "resolution_width": profile.resolution_width,
        "resolution_height": profile.resolution_height,
        "ui_scale_percent": profile.ui_scale_percent,
        "regions": {
            key: {
                "x": region.x,
                "y": region.y,
                "width": region.width,
                "height": region.height,
            }
            for key, region in profile.regions.items()
        },
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_calibration_profile(path: str | Path) -> CalibrationProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "regions" not in data:
        profile = default_calibration_profile()
        profile.regions[MARKET_RATIO] = CropRegion(
            x=int(data["x"]),
            y=int(data["y"]),
            width=int(data["width"]),
            height=int(data["height"]),
        )
        return profile
    return _profile_from_dict(data)


def _profile_from_dict(data: dict) -> CalibrationProfile:
    profile = CalibrationProfile(
        name=str(data.get("name") or "Основной"),
        resolution_width=int(data.get("resolution_width") or 1280),
        resolution_height=int(data.get("resolution_height") or 720),
        ui_scale_percent=int(data.get("ui_scale_percent") or 100),
        regions={},
    )
    defaults = default_calibration_profile().regions
    raw_regions = data.get("regions") or {}
    for key, default_region in defaults.items():
        raw = raw_regions.get(key)
        if not raw:
            profile.regions[key] = default_region
            continue
        profile.regions[key] = CropRegion(
            x=int(raw["x"]),
            y=int(raw["y"]),
            width=int(raw["width"]),
            height=int(raw["height"]),
        )
    return profile
