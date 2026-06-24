from __future__ import annotations

from .models import Opportunity, StrategyType


CORE_CURRENCIES = {"Exalted Orb", "Divine Orb", "Chaos Orb"}
FAMILY_KEYWORDS = ("Omen", "Rune", "Essence")
BASKET_KEYWORDS = ("Omen", "Rune", "Essence")
HUB_CURRENCIES = {"Exalted Orb", "Divine Orb", "Chaos Orb"}


def classify_strategies(opportunity: Opportunity) -> tuple[StrategyType, ...]:
    path = opportunity.path
    nodes = set(path[:-1])
    edges_count = max(len(path) - 1, 0)
    strategies: list[StrategyType] = []

    if edges_count == 2 and path[0] == path[-1]:
        strategies.append(StrategyType.SPREAD_CAPTURE)

    if path[0] == "Exalted Orb" and path[-1] == "Exalted Orb" and "Chaos Orb" in nodes:
        strategies.append(StrategyType.STABLE_HUB)

    if path[0] == "Divine Orb" and path[-1] == "Divine Orb" and "Chaos Orb" in nodes:
        strategies.append(StrategyType.DIVINE_HUB)

    if any(_contains_keyword(node, BASKET_KEYWORDS) for node in nodes - HUB_CURRENCIES):
        strategies.append(StrategyType.BASKET)

    if opportunity.trend_percent > 0 and opportunity.volume_score > 0 and opportunity.net_profit > 0:
        strategies.append(StrategyType.TREND_CONFIRMED)

    if opportunity.baseline_delta_percent <= -10 and opportunity.net_profit > 0:
        strategies.append(StrategyType.MEAN_REVERSION)

    if opportunity.volume_score >= 10_000 and opportunity.profit_per_hour > 0:
        strategies.append(StrategyType.LIQUIDITY_FIRST)

    if 0 < opportunity.volume_score < 10_000 and opportunity.roi_percent >= 5:
        strategies.append(StrategyType.LOW_CAP_HIGH_ROI)

    if _same_family_nodes(nodes):
        strategies.append(StrategyType.SAME_FAMILY)

    if edges_count == 3 and nodes.issubset(CORE_CURRENCIES) and {"Chaos Orb", "Divine Orb", "Exalted Orb"}.issubset(nodes):
        strategies.append(StrategyType.CURRENCY_TRIANGLE)

    if edges_count == 4 and _has_item_leg(nodes) and nodes.intersection(HUB_CURRENCIES):
        strategies.append(StrategyType.FOUR_HOP_HUB)

    if edges_count >= 5:
        strategies.append(StrategyType.FIVE_HOP_RESEARCH)

    return tuple(dict.fromkeys(strategies)) or (StrategyType.GENERIC,)


def _contains_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in value.lower() for keyword in keywords)


def _same_family_nodes(nodes: set[str]) -> bool:
    for keyword in FAMILY_KEYWORDS:
        matches = [node for node in nodes if keyword.lower() in node.lower()]
        if len(matches) >= 2:
            return True
    return False


def _has_item_leg(nodes: set[str]) -> bool:
    return bool(nodes - HUB_CURRENCIES)
