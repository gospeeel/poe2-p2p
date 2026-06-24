from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RatioValidation:
    ok: bool
    reason: str


def validate_ratio_range(
    observed_rate: float,
    expected_rate: float,
    tolerance_percent: float = 20.0,
) -> RatioValidation:
    if observed_rate <= 0:
        return RatioValidation(False, "observed rate must be positive")
    if expected_rate <= 0:
        return RatioValidation(False, "expected rate must be positive")

    delta_percent = abs(observed_rate - expected_rate) / expected_rate * 100
    if delta_percent <= tolerance_percent:
        return RatioValidation(True, f"within {delta_percent:.2f}% of expected rate")
    return RatioValidation(
        False,
        f"{delta_percent:.2f}% away from expected rate; tolerance is {tolerance_percent:.2f}%",
    )
