from __future__ import annotations

from .models import Candidate, RateEdge


VALUE_CURRENCY = "Divine Orb"
STORE_OF_VALUE_CURRENCY = "Mirror of Kalandra"
VALUATION_CURRENCIES = {
    "Exalted Orb",
    "Chaos Orb",
    VALUE_CURRENCY,
    STORE_OF_VALUE_CURRENCY,
}


def build_valuation_edges(
    candidates: list[Candidate],
    value_currency: str = VALUE_CURRENCY,
    source: str = "poe.ninja baseline",
) -> list[RateEdge]:
    values = _chaos_values(candidates)
    value_in_chaos = values.get(value_currency)
    if not value_in_chaos or value_in_chaos <= 0:
        return []

    edges: list[RateEdge] = []
    for name in sorted(VALUATION_CURRENCIES | {value_currency}):
        item_in_chaos = values.get(name)
        if not item_in_chaos or item_in_chaos <= 0 or name == value_currency:
            continue
        to_value = item_in_chaos / value_in_chaos
        if to_value <= 0:
            continue
        edges.append(RateEdge(name, value_currency, to_value, source, confidence=0.90))
        edges.append(RateEdge(value_currency, name, 1 / to_value, f"{source}:inverse", confidence=0.90))
    return edges


def value_amounts(
    candidates: list[Candidate],
    value_currency: str = VALUE_CURRENCY,
) -> dict[str, float]:
    values = _chaos_values(candidates)
    value_in_chaos = values.get(value_currency)
    if not value_in_chaos or value_in_chaos <= 0:
        return {}
    return {
        name: item_in_chaos / value_in_chaos
        for name, item_in_chaos in values.items()
        if item_in_chaos > 0
    }


def merge_valuation_edges(rates: list[RateEdge], valuation_edges: list[RateEdge]) -> list[RateEdge]:
    valuation_pairs = {
        (edge.from_currency, edge.to_currency)
        for edge in valuation_edges
    }
    live_rates = [
        rate
        for rate in rates
        if (rate.from_currency, rate.to_currency) not in valuation_pairs
        and not rate.source.startswith("poe.ninja baseline")
    ]
    return [*live_rates, *valuation_edges]


def _chaos_values(candidates: list[Candidate]) -> dict[str, float]:
    values = {
        candidate.name: candidate.value_in_chaos
        for candidate in candidates
        if candidate.value_in_chaos > 0
    }
    values.setdefault("Chaos Orb", 1.0)
    return values
