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

    @property
    def path_label(self) -> str:
        return " -> ".join(self.path)


@dataclass(frozen=True)
class Candidate:
    name: str
    value_in_chaos: float
    volume_per_hour: float
    seven_day_change_percent: float = 0.0
    popularity_rank: int | None = None

    @property
    def volume_score(self) -> float:
        return self.value_in_chaos * self.volume_per_hour
