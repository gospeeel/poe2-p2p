from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from math import prod

from .economic_strategies import classify_strategies
from .models import ChainType, Opportunity, OpportunityStep, RateEdge


DIVINE_ORB = "Divine Orb"
MIRROR_OF_KALANDRA = "Mirror of Kalandra"
CORE_CURRENCIES = {"Exalted Orb", DIVINE_ORB, "Chaos Orb"}


class ArbitrageCalculator:
    def __init__(
        self,
        rates: list[RateEdge],
        slippage_buffer_percent: float = 0.0,
        spread_loss_percent: float = 0.0,
        rounding_loss_flat: float = 0.0,
        gold_cost_flat: float = 0.0,
        rounding_loss_per_step: float = 0.0,
        gold_cost_per_step: float = 0.0,
        stale_after_seconds: float = 120.0,
        stale_penalty_percent: float = 0.0,
        low_confidence_penalty_percent: float = 0.0,
        seconds_per_step: float = 0.0,
        min_bankroll: float = 0.0,
        trend_by_currency: dict[str, float] | None = None,
        cycles_per_hour: float = 1.0,
        min_roi_percent: float = 0.0,
        min_net_profit: float = 0.0,
        value_currency: str = DIVINE_ORB,
        store_of_value_currency: str = MIRROR_OF_KALANDRA,
    ) -> None:
        self.rates = rates
        self.slippage_buffer_percent = slippage_buffer_percent
        self.spread_loss_percent = spread_loss_percent
        self.rounding_loss_flat = rounding_loss_flat
        self.gold_cost_flat = gold_cost_flat
        self.rounding_loss_per_step = rounding_loss_per_step
        self.gold_cost_per_step = gold_cost_per_step
        self.stale_after_seconds = stale_after_seconds
        self.stale_penalty_percent = stale_penalty_percent
        self.low_confidence_penalty_percent = low_confidence_penalty_percent
        self.seconds_per_step = seconds_per_step
        self.min_bankroll = min_bankroll
        self.trend_by_currency = trend_by_currency or {}
        self.cycles_per_hour = cycles_per_hour
        self.min_roi_percent = min_roi_percent
        self.min_net_profit = min_net_profit
        self.value_currency = value_currency
        self.store_of_value_currency = store_of_value_currency
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
        if input_amount < self.min_bankroll:
            return []
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
        return sorted(opportunities, key=lambda item: item.net_profit_value, reverse=True)

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
                    and opportunity.net_profit_value >= self.min_net_profit
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
        step_rounding_loss = len(edges) * self.rounding_loss_per_step
        step_gold_cost = len(edges) * self.gold_cost_per_step
        stale_edges = [
            edge for edge in edges
            if (datetime.now(UTC) - edge.timestamp).total_seconds() > self.stale_after_seconds
        ]
        stale_penalty = max(gross_profit, 0.0) * (self.stale_penalty_percent / 100) * len(stale_edges)
        low_confidence_edges = [edge for edge in edges if edge.confidence < 0.85]
        confidence_penalty = max(gross_profit, 0.0) * (self.low_confidence_penalty_percent / 100) * len(low_confidence_edges)
        fixed_loss = (
            self.rounding_loss_flat
            + self.gold_cost_flat
            + step_rounding_loss
            + step_gold_cost
            + stale_penalty
            + confidence_penalty
        )
        net_profit = gross_profit - variable_loss - fixed_loss
        roi_percent = net_profit / input_amount * 100 if input_amount else 0.0
        confidence = prod(edge.confidence for edge in edges)
        execution_time_seconds = len(edges) * self.seconds_per_step if self.seconds_per_step > 0 else 0.0
        profit_per_hour = (
            net_profit * 3600 / execution_time_seconds
            if execution_time_seconds > 0
            else net_profit * self.cycles_per_hour
        )
        value_rate = self._conversion_rate(input_currency, self.value_currency)
        input_value = input_amount * value_rate
        output_value = output_amount * value_rate
        net_profit_value = net_profit * value_rate
        profit_per_hour_value = profit_per_hour * value_rate
        mirror_rate = self._conversion_rate(self.value_currency, self.store_of_value_currency)
        mirror_value = net_profit_value * mirror_rate if mirror_rate > 0 else None
        trend_values = [
            self.trend_by_currency[node]
            for node in path[:-1]
            if node in self.trend_by_currency
        ]
        trend_percent = sum(trend_values) / len(trend_values) if trend_values else 0.0
        trend_factor = 1 + max(trend_percent, 0.0) / 100
        score = profit_per_hour_value * confidence * trend_factor
        source = ", ".join(edge.source for edge in edges)
        stocks = [edge.observed_stock for edge in edges if edge.observed_stock is not None]
        max_size = min(stocks) if stocks else None
        volume_score = sum(stocks) if stocks else 0.0
        age_seconds = max(
            (datetime.now(UTC) - edge.timestamp).total_seconds()
            for edge in edges
        ) if edges else 0.0
        steps = self._build_steps(
            input_amount,
            edges,
            stale_edges=tuple(stale_edges),
            low_confidence_edges=tuple(low_confidence_edges),
            gross_profit=max(gross_profit, 0.0),
        )
        risk, risk_reasons = self._risk_label(
            roi_percent=roi_percent,
            confidence=confidence,
            age_seconds=age_seconds,
            max_size=max_size,
            net_profit=net_profit,
            variable_loss=variable_loss,
            fixed_loss=fixed_loss,
        )

        opportunity = Opportunity(
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
            volume_score=volume_score,
            execution_steps=len(edges),
            execution_time_seconds=execution_time_seconds,
            steps=steps,
            risk_reasons=risk_reasons,
            trend_percent=trend_percent,
            value_currency=self.value_currency,
            input_value=input_value,
            output_value=output_value,
            net_profit_value=net_profit_value,
            profit_per_hour_value=profit_per_hour_value,
            mirror_value=mirror_value,
        )
        return replace(opportunity, strategy_types=classify_strategies(opportunity))

    def _conversion_rate(self, from_currency: str, to_currency: str) -> float:
        if from_currency == to_currency:
            return 1.0
        direct = self._direct_conversion_rate(from_currency, to_currency)
        if direct is not None:
            return direct
        # Two-hop conversion is enough for current hub currencies and keeps valuation predictable.
        for first in self.graph.get(from_currency, []):
            second = self._direct_conversion_rate(first.to_currency, to_currency)
            if second is not None:
                return first.rate * second
        return 0.0

    def _direct_conversion_rate(self, from_currency: str, to_currency: str) -> float | None:
        for edge in self.graph.get(from_currency, []):
            if edge.to_currency == to_currency:
                return edge.rate
        return None

    def _build_steps(
        self,
        input_amount: float,
        edges: tuple[RateEdge, ...],
        stale_edges: tuple[RateEdge, ...],
        low_confidence_edges: tuple[RateEdge, ...],
        gross_profit: float,
    ) -> tuple[OpportunityStep, ...]:
        steps = []
        current_amount = input_amount
        now = datetime.now(UTC)
        stale_edge_set = set(stale_edges)
        low_confidence_edge_set = set(low_confidence_edges)
        for edge in edges:
            output_amount = edge.convert(current_amount)
            steps.append(
                OpportunityStep(
                    from_currency=edge.from_currency,
                    to_currency=edge.to_currency,
                    input_amount=current_amount,
                    output_amount=output_amount,
                    rate=edge.rate,
                    source=edge.source,
                    confidence=edge.confidence,
                    observed_stock=edge.observed_stock,
                    age_seconds=(now - edge.timestamp).total_seconds(),
                    rounding_loss=self.rounding_loss_per_step,
                    gold_cost=self.gold_cost_per_step,
                    stale_penalty=(
                        gross_profit * (self.stale_penalty_percent / 100)
                        if edge in stale_edge_set
                        else 0.0
                    ),
                    confidence_penalty=(
                        gross_profit * (self.low_confidence_penalty_percent / 100)
                        if edge in low_confidence_edge_set
                        else 0.0
                    ),
                )
            )
            current_amount = output_amount
        return tuple(steps)

    @staticmethod
    def _risk_label(
        roi_percent: float,
        confidence: float,
        age_seconds: float,
        max_size: float | None,
        net_profit: float,
        variable_loss: float,
        fixed_loss: float,
    ) -> tuple[str, tuple[str, ...]]:
        reasons = []
        if confidence < 0.85:
            reasons.append("низкая уверенность OCR/данных")
        if age_seconds > 120:
            reasons.append("курс старше 120 секунд")
        if max_size is None:
            reasons.append("нет данных по доступному объему")
        if net_profit <= 0:
            reasons.append("чистый профит не положительный")
        if variable_loss + fixed_loss > 0:
            reasons.append("есть потери на spread, округление или стоимость действий")

        if confidence >= 0.95 and roi_percent >= 2 and age_seconds <= 120:
            return "low", tuple(reasons or ["нет явных факторов риска"])
        if confidence >= 0.85 and roi_percent >= 1:
            return "medium", tuple(reasons or ["умеренный риск исполнения"])
        return "high", tuple(reasons or ["высокий риск по доходности или уверенности"])

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
