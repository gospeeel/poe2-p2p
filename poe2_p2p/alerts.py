from __future__ import annotations

from .models import Opportunity


def filter_profit_alerts(
    opportunities: list[Opportunity],
    min_net_profit: float = 0.0,
    min_roi_percent: float = 0.0,
) -> list[Opportunity]:
    return [
        opportunity
        for opportunity in opportunities
        if opportunity.net_profit_value >= min_net_profit
        and opportunity.roi_percent >= min_roi_percent
    ]
