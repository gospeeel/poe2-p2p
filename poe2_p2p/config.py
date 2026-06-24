from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropRegion:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_csv(cls, value: str) -> "CropRegion":
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 4:
            raise ValueError("Crop region must use x,y,width,height format")
        x, y, width, height = (int(part) for part in parts)
        if width <= 0 or height <= 0:
            raise ValueError("Crop region width and height must be positive")
        return cls(x=x, y=y, width=width, height=height)

    def as_box(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def as_mss(self) -> dict[str, int]:
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height,
        }


# Screenshot_1/2 are 1280x720. This region targets the small Market Ratio text.
DEFAULT_MARKET_RATIO_REGION = CropRegion(x=385, y=122, width=90, height=18)
