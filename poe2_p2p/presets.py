from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    name: str
    base_currency: str
    input_amount: float
    min_roi_percent: float
    max_hops: int


DEFAULT_PRESETS = {
    "exalted-direct": Preset(
        name="exalted-direct",
        base_currency="Exalted Orb",
        input_amount=2050.0,
        min_roi_percent=1.0,
        max_hops=3,
    ),
    "divine-direct": Preset(
        name="divine-direct",
        base_currency="Divine Orb",
        input_amount=6.0,
        min_roi_percent=1.0,
        max_hops=3,
    ),
    "multi-hop-research": Preset(
        name="multi-hop-research",
        base_currency="Exalted Orb",
        input_amount=2050.0,
        min_roi_percent=0.5,
        max_hops=5,
    ),
}


def get_preset(name: str) -> Preset:
    try:
        return DEFAULT_PRESETS[name]
    except KeyError as error:
        available = ", ".join(sorted(DEFAULT_PRESETS))
        raise ValueError(f"Unknown preset {name!r}. Available: {available}") from error
