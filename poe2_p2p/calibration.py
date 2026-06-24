from __future__ import annotations

import json
from pathlib import Path

from .config import CropRegion


def save_region(path: str | Path, region: CropRegion) -> None:
    data = {
        "x": region.x,
        "y": region.y,
        "width": region.width,
        "height": region.height,
    }
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_region(path: str | Path) -> CropRegion:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return CropRegion(
        x=int(data["x"]),
        y=int(data["y"]),
        width=int(data["width"]),
        height=int(data["height"]),
    )
