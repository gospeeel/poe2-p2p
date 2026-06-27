from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ChainType(StrEnum):
    DIRECT = "direct"
    REVERSE = "reverse"
    TRIANGULAR = "triangular"
    CROSS_CURRENCY = "cross_currency"
    MULTI_HOP = "multi_hop"
    UNKNOWN = "unknown"


CHAIN_TYPE_LABELS = {
    ChainType.DIRECT: "прямая",
    ChainType.REVERSE: "обратная",
    ChainType.TRIANGULAR: "треугольная",
    ChainType.CROSS_CURRENCY: "через Chaos",
    ChainType.MULTI_HOP: "многошаговая",
    ChainType.UNKNOWN: "неизвестно",
}


class StrategyType(StrEnum):
    SPREAD_CAPTURE = "spread_capture"
    STABLE_HUB = "stable_hub"
    DIVINE_HUB = "divine_hub"
    BASKET = "basket"
    TREND_CONFIRMED = "trend_confirmed"
    MEAN_REVERSION = "mean_reversion"
    LIQUIDITY_FIRST = "liquidity_first"
    LOW_CAP_HIGH_ROI = "low_cap_high_roi"
    SAME_FAMILY = "same_family"
    CURRENCY_TRIANGLE = "currency_triangle"
    FOUR_HOP_HUB = "four_hop_hub"
    FIVE_HOP_RESEARCH = "five_hop_research"
    GENERIC = "generic"


STRATEGY_TYPE_LABELS = {
    StrategyType.SPREAD_CAPTURE: "спред",
    StrategyType.STABLE_HUB: "стабильный hub",
    StrategyType.DIVINE_HUB: "Divine hub",
    StrategyType.BASKET: "корзина",
    StrategyType.TREND_CONFIRMED: "тренд",
    StrategyType.MEAN_REVERSION: "возврат к среднему",
    StrategyType.LIQUIDITY_FIRST: "ликвидность",
    StrategyType.LOW_CAP_HIGH_ROI: "высокий ROI",
    StrategyType.SAME_FAMILY: "одна семья",
    StrategyType.CURRENCY_TRIANGLE: "валютный треугольник",
    StrategyType.FOUR_HOP_HUB: "4 шага через hub",
    StrategyType.FIVE_HOP_RESEARCH: "5 шагов research",
    StrategyType.GENERIC: "общая",
}


STRATEGY_TYPE_DESCRIPTIONS = {
    StrategyType.SPREAD_CAPTURE: "Положительный цикл между двумя валютами за счет bid/ask разницы.",
    StrategyType.STABLE_HUB: "Маршрут через Exalted/Chaos как стабильный hub для исполнения.",
    StrategyType.DIVINE_HUB: "Маршрут через Divine/Chaos как дорогой hub для крупных циклов.",
    StrategyType.BASKET: "Корзина похожих Omen/Rune/Essence предметов против одной базовой валюты.",
    StrategyType.TREND_CONFIRMED: "Профит подтвержден положительным трендом и объемом.",
    StrategyType.MEAN_REVERSION: "NPC/live цена заметно ниже базовой цены, ожидается возврат к среднему.",
    StrategyType.LIQUIDITY_FIRST: "Приоритет не максимальному ROI, а исполнимому profit/hour при большом объеме.",
    StrategyType.LOW_CAP_HIGH_ROI: "Рискованный малый объем с высоким ROI.",
    StrategyType.SAME_FAMILY: "Обмен внутри одной семьи предметов через hub-валюту.",
    StrategyType.CURRENCY_TRIANGLE: "Треугольник Exalted/Chaos/Divine без предметной ноги.",
    StrategyType.FOUR_HOP_HUB: "Четырехшаговый маршрут через предметы и hub-валюту.",
    StrategyType.FIVE_HOP_RESEARCH: "Пятишаговый исследовательский маршрут с повышенным риском исполнения.",
    StrategyType.GENERIC: "Связка не попала в более точную стратегическую категорию.",
}


@dataclass(frozen=True)
class RateEdge:
    from_currency: str
    to_currency: str
    rate: float
    source: str
    confidence: float = 1.0
    observed_stock: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def convert(self, amount: float) -> float:
        return amount * self.rate


@dataclass(frozen=True)
class OpportunityStep:
    from_currency: str
    to_currency: str
    input_amount: float
    output_amount: float
    rate: float
    source: str
    confidence: float
    observed_stock: float | None = None
    age_seconds: float = 0.0
    rounding_loss: float = 0.0
    gold_cost: float = 0.0
    stale_penalty: float = 0.0
    confidence_penalty: float = 0.0


@dataclass(frozen=True)
class Opportunity:
    path: tuple[str, ...]
    input_currency: str
    input_amount: float
    output_amount: float
    gross_profit: float
    net_profit: float
    roi_percent: float
    confidence: float
    source: str
    profit_per_hour: float = 0.0
    score: float = 0.0
    risk: str = "unknown"
    max_size: float | None = None
    chain_type: ChainType = ChainType.UNKNOWN
    age_seconds: float = 0.0
    volume_score: float = 0.0
    execution_steps: int = 0
    execution_time_seconds: float = 0.0
    steps: tuple[OpportunityStep, ...] = ()
    risk_reasons: tuple[str, ...] = ()
    strategy_types: tuple[StrategyType, ...] = (StrategyType.GENERIC,)
    trend_percent: float = 0.0
    baseline_delta_percent: float = 0.0
    value_currency: str = "Divine Orb"
    input_value: float = 0.0
    output_value: float = 0.0
    net_profit_value: float = 0.0
    profit_per_hour_value: float = 0.0
    mirror_value: float | None = None

    @property
    def path_label(self) -> str:
        return " -> ".join(self.path)

    @property
    def strategy_label(self) -> str:
        return ", ".join(STRATEGY_TYPE_LABELS.get(item, item.value) for item in self.strategy_types)


@dataclass(frozen=True)
class Candidate:
    name: str
    value_in_chaos: float
    volume_per_hour: float
    seven_day_change_percent: float = 0.0
    popularity_rank: int | None = None
    image_url: str | None = None

    @property
    def volume_score(self) -> float:
        return self.value_in_chaos * self.volume_per_hour
