from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from math import prod

from .models import ChainType, Opportunity, RateEdge


CORE_CURRENCIES = {"Exalted Orb", "Divine Orb", "Chaos Orb"}


class ArbitrageCalculator:
    def __init__(
        self,
        rates: list[RateEdge],
        slippage_buffer_percent: float = 0.0,
        spread_loss_percent: float = 0.0,
        rounding_loss_flat: float = 0.0,
        gold_cost_flat: float = 0.0,
        cycles_per_hour: float = 1.0,
        min_roi_percent: float = 0.0,
        min_net_profit: float = 0.0,
    ) -> None:
        self.rates = rates
        self.slippage_buffer_percent = slippage_buffer_percent
        self.spread_loss_percent = spread_loss_percent
        self.rounding_loss_flat = rounding_loss_flat
        self.gold_cost_flat = gold_cost_flat
        self.cycles_per_hour = cycles_per_hour
        self.min_roi_percent = min_roi_percent
        self.min_net_profit = min_net_profit
        self.graph: dict[str, list[RateEdge]] = defaultdict(list)
        for rate in rates:
            if rate.rate <= 0:
                continue
            self.graph[rate.from_currency].append(rate)

    def find_cycles(
        self,
        start_currency: str,
        input_amount: float,
        max_hops: int = 4,
    ) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        self._walk(
            start_currency=start_currency,
            current_currency=start_currency,
            input_amount=input_amount,
            current_amount=input_amount,
            max_hops=max_hops,
            path=(start_currency,),
            edges=(),
            opportunities=opportunities,
        )
        return sorted(opportunities, key=lambda item: item.net_profit, reverse=True)

    def _walk(
        self,
        start_currency: str,
        current_currency: str,
        input_amount: float,
        current_amount: float,
        max_hops: int,
        path: tuple[str, ...],
        edges: tuple[RateEdge, ...],
        opportunities: list[Opportunity],
    ) -> None:
        if len(edges) >= max_hops:
            return

        for edge in self.graph.get(current_currency, []):
            next_amount = edge.convert(current_amount)
            next_path = (*path, edge.to_currency)
            next_edges = (*edges, edge)

            if edge.to_currency == start_currency and len(next_edges) >= 2:
                opportunity = self._build_opportunity(
                    path=next_path,
                    input_currency=start_currency,
                    input_amount=input_amount,
                    output_amount=next_amount,
                    edges=next_edges,
                )
                if (
                    opportunity.roi_percent >= self.min_roi_percent
                    and opportunity.net_profit >= self.min_net_profit
                ):
                    opportunities.append(opportunity)
                continue

            if edge.to_currency in path:
                continue

            self._walk(
                start_currency=start_currency,
                current_currency=edge.to_currency,
                input_amount=input_amount,
                current_amount=next_amount,
                max_hops=max_hops,
                path=next_path,
                edges=next_edges,
                opportunities=opportunities,
            )

    def _build_opportunity(
        self,
        path: tuple[str, ...],
        input_currency: str,
        input_amount: float,
        output_amount: float,
        edges: tuple[RateEdge, ...],
    ) -> Opportunity:
        gross_profit = output_amount - input_amount
        variable_loss_percent = self.slippage_buffer_percent + self.spread_loss_percent
        variable_loss = max(gross_profit, 0.0) * (variable_loss_percent / 100)
        fixed_loss = self.rounding_loss_flat + self.gold_cost_flat
        net_profit = gross_profit - variable_loss - fixed_loss
        roi_percent = net_profit / input_amount * 100 if input_amount else 0.0
        confidence = prod(edge.confidence for edge in edges)
        profit_per_hour = net_profit * self.cycles_per_hour
        score = profit_per_hour * confidence
        source = ", ".join(edge.source for edge in edges)
        risk = self._risk_label(roi_percent=roi_percent, confidence=confidence)
        stocks = [edge.observed_stock for edge in edges if edge.observed_stock is not None]
        max_size = min(stocks) if stocks else None
        age_seconds = max(
            (datetime.now(UTC) - edge.timestamp).total_seconds()
            for edge in edges
        ) if edges else 0.0

        return Opportunity(
            path=path,
            input_currency=input_currency,
            input_amount=input_amount,
            output_amount=output_amount,
            gross_profit=gross_profit,
            net_profit=net_profit,
            roi_percent=roi_percent,
            confidence=confidence,
            source=source,
            profit_per_hour=profit_per_hour,
            score=score,
            risk=risk,
            chain_type=self._classify_chain(path),
            max_size=max_size,
            age_seconds=age_seconds,
            volume_score=0.0,
            execution_steps=len(edges),
        )

    @staticmethod
    def _risk_label(roi_percent: float, confidence: float) -> str:
        if confidence >= 0.95 and roi_percent >= 2:
            return "low"
        if confidence >= 0.85 and roi_percent >= 1:
            return "medium"
        return "high"

    @staticmethod
    def _classify_chain(path: tuple[str, ...]) -> ChainType:
        edges_count = max(len(path) - 1, 0)
        unique_nodes = set(path[:-1])
        if edges_count >= 5:
            return ChainType.MULTI_HOP
        if "Chaos Orb" in unique_nodes and unique_nodes.issubset(CORE_CURRENCIES):
            return ChainType.CROSS_CURRENCY
        if edges_count == 3 and path[0] == "Exalted Orb" and "Divine Orb" in unique_nodes:
            return ChainType.DIRECT
        if edges_count == 3 and path[0] == "Divine Orb" and "Exalted Orb" in unique_nodes:
            return ChainType.REVERSE
        if edges_count == 4:
            return ChainType.TRIANGULAR
        if "Chaos Orb" in unique_nodes:
            return ChainType.CROSS_CURRENCY
        return ChainType.UNKNOWN
