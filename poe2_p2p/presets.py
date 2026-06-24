from __future__ import annotations

from dataclasses import dataclass

from .models import ChainType


@dataclass(frozen=True)
class Preset:
    name: str
    base_currency: str
    input_amount: float
    min_roi_percent: float
    max_hops: int
    chain_type: ChainType = ChainType.UNKNOWN


@dataclass(frozen=True)
class StrategyPreset:
    name: str
    label: str
    min_roi_percent: float
    min_confidence: float
    min_volume_score: float
    prefer_profit_per_hour: bool = True
    description: str = ""


DEFAULT_PRESETS = {
    "exalted-direct": Preset(
        name="exalted-direct",
        base_currency="Exalted Orb",
        input_amount=2050.0,
        min_roi_percent=1.0,
        max_hops=3,
        chain_type=ChainType.DIRECT,
    ),
    "divine-reverse": Preset(
        name="divine-reverse",
        base_currency="Divine Orb",
        input_amount=6.0,
        min_roi_percent=1.0,
        max_hops=3,
        chain_type=ChainType.REVERSE,
    ),
    "chaos-cross": Preset(
        name="chaos-cross",
        base_currency="Exalted Orb",
        input_amount=2050.0,
        min_roi_percent=0.5,
        max_hops=3,
        chain_type=ChainType.CROSS_CURRENCY,
    ),
    "triangular-research": Preset(
        name="triangular-research",
        base_currency="Exalted Orb",
        input_amount=2050.0,
        min_roi_percent=0.5,
        max_hops=4,
        chain_type=ChainType.TRIANGULAR,
    ),
    "multi-hop-research": Preset(
        name="multi-hop-research",
        base_currency="Exalted Orb",
        input_amount=2050.0,
        min_roi_percent=0.5,
        max_hops=5,
        chain_type=ChainType.MULTI_HOP,
    ),
}


STRATEGY_PRESETS = {
    "safe": StrategyPreset(
        name="safe",
        label="Безопасный",
        min_roi_percent=2.0,
        min_confidence=0.85,
        min_volume_score=0.0,
        description="Строже фильтрует рискованные связки и требует более высокой уверенности данных.",
    ),
    "balanced": StrategyPreset(
        name="balanced",
        label="Баланс",
        min_roi_percent=1.0,
        min_confidence=0.70,
        min_volume_score=0.0,
        description="Компромисс между количеством возможностей и риском ошибки.",
    ),
    "aggressive": StrategyPreset(
        name="aggressive",
        label="Агрессивный",
        min_roi_percent=0.5,
        min_confidence=0.0,
        min_volume_score=0.0,
        prefer_profit_per_hour=False,
        description="Показывает больше возможностей, включая рискованные и низкоуверенные.",
    ),
    "high-volume": StrategyPreset(
        name="high-volume",
        label="Большой объем",
        min_roi_percent=0.5,
        min_confidence=0.70,
        min_volume_score=10_000.0,
        description="Ищет не максимальный процент, а связки, которые проще исполнить большим объемом.",
    ),
    "high-roi": StrategyPreset(
        name="high-roi",
        label="Высокая доходность",
        min_roi_percent=5.0,
        min_confidence=0.60,
        min_volume_score=0.0,
        prefer_profit_per_hour=False,
        description="Фокус на высоком проценте прибыли, даже если объем меньше.",
    ),
}


def get_preset(name: str) -> Preset:
    try:
        return DEFAULT_PRESETS[name]
    except KeyError as error:
        available = ", ".join(sorted(DEFAULT_PRESETS))
        raise ValueError(f"Unknown preset {name!r}. Available: {available}") from error
