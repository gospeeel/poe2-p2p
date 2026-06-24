from __future__ import annotations

import re


RATIO_PATTERN = re.compile(r"(?P<left>\d+(?:[.,]\d+)?)\s*:\s*(?P<right>\d+(?:[.,]\d+)?)")


def parse_ratio(text: str) -> tuple[float, float]:
    normalized = text.strip().replace(",", ".")
    match = RATIO_PATTERN.search(normalized)
    if not match:
        raise ValueError(f"Could not parse market ratio from: {text!r}")
    return float(match.group("left")), float(match.group("right"))


def normalize_ratio_to_edges(
    left_item: str,
    right_item: str,
    ratio_text: str,
    source: str,
    confidence: float,
):
    from .models import RateEdge

    left_amount, right_amount = parse_ratio(ratio_text)
    if left_amount <= 0 or right_amount <= 0:
        raise ValueError(f"Ratio amounts must be positive: {ratio_text!r}")

    rate_left_to_right = right_amount / left_amount
    rate_right_to_left = left_amount / right_amount

    return [
        RateEdge(left_item, right_item, rate_left_to_right, source, confidence),
        RateEdge(right_item, left_item, rate_right_to_left, f"{source}:inverse", confidence),
    ]
