from __future__ import annotations

from .models import Opportunity


def rank_opportunities(
    opportunities: list[Opportunity],
    key: str = "net_profit",
) -> list[Opportunity]:
    keys = {
        "net_profit": lambda item: item.net_profit_value,
        "net_profit_value": lambda item: item.net_profit_value,
        "cycle_net_profit": lambda item: item.net_profit,
        "roi": lambda item: item.roi_percent,
        "profit_per_hour": lambda item: item.profit_per_hour_value,
        "profit_per_hour_value": lambda item: item.profit_per_hour_value,
        "cycle_profit_per_hour": lambda item: item.profit_per_hour,
        "score": lambda item: item.score,
        "confidence": lambda item: item.confidence,
    }
    try:
        getter = keys[key]
    except KeyError as error:
        available = ", ".join(sorted(keys))
        raise ValueError(f"Unknown ranking key {key!r}. Available: {available}") from error
    return sorted(opportunities, key=getter, reverse=True)
