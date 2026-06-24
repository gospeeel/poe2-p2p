from __future__ import annotations

from .models import RateEdge

EXALTED = "Exalted Orb"
DIVINE = "Divine Orb"
OMEN_WHITTLING = "Omen of Whittling"


def screenshot_rates() -> list[RateEdge]:
    """Rates normalized from the included screenshots."""
    return [
        RateEdge(
            from_currency=OMEN_WHITTLING,
            to_currency=EXALTED,
            rate=2050.0,
            source="Screenshot_1.jpg",
            confidence=0.99,
        ),
        RateEdge(
            from_currency=EXALTED,
            to_currency=OMEN_WHITTLING,
            rate=1 / 2050.0,
            source="Screenshot_1.jpg:inverse",
            confidence=0.99,
        ),
        RateEdge(
            from_currency=OMEN_WHITTLING,
            to_currency=DIVINE,
            rate=6.34,
            source="Screenshot_2.jpg",
            confidence=0.99,
        ),
        RateEdge(
            from_currency=DIVINE,
            to_currency=OMEN_WHITTLING,
            rate=1 / 6.34,
            source="Screenshot_2.jpg:inverse",
            confidence=0.99,
        ),
        RateEdge(
            from_currency=DIVINE,
            to_currency=EXALTED,
            rate=352.0,
            source="manual_baseline",
            confidence=0.90,
        ),
        RateEdge(
            from_currency=EXALTED,
            to_currency=DIVINE,
            rate=1 / 352.0,
            source="manual_baseline:inverse",
            confidence=0.90,
        ),
    ]
