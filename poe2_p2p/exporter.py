from __future__ import annotations

import csv
from pathlib import Path

from .models import Opportunity


def export_opportunities_csv(opportunities: list[Opportunity], path: str | Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "path",
                "chain_type",
                "strategy_types",
                "input_currency",
                "input_amount",
                "output_amount",
                "gross_profit",
                "net_profit",
                "roi_percent",
                "profit_per_hour",
                "value_currency",
                "input_value",
                "output_value",
                "net_profit_value",
                "profit_per_hour_value",
                "mirror_value",
                "score",
                "confidence",
                "risk",
                "max_size",
                "age_seconds",
                "volume_score",
                "trend_percent",
                "execution_steps",
                "execution_time_seconds",
                "source",
            ]
        )
        for opportunity in opportunities:
            writer.writerow(
                [
                    opportunity.path_label,
                    opportunity.chain_type.value,
                    "|".join(item.value for item in opportunity.strategy_types),
                    opportunity.input_currency,
                    f"{opportunity.input_amount:.8f}",
                    f"{opportunity.output_amount:.8f}",
                    f"{opportunity.gross_profit:.8f}",
                    f"{opportunity.net_profit:.8f}",
                    f"{opportunity.roi_percent:.8f}",
                    f"{opportunity.profit_per_hour:.8f}",
                    opportunity.value_currency,
                    f"{opportunity.input_value:.8f}",
                    f"{opportunity.output_value:.8f}",
                    f"{opportunity.net_profit_value:.8f}",
                    f"{opportunity.profit_per_hour_value:.8f}",
                    "" if opportunity.mirror_value is None else f"{opportunity.mirror_value:.8f}",
                    f"{opportunity.score:.8f}",
                    f"{opportunity.confidence:.8f}",
                    opportunity.risk,
                    "" if opportunity.max_size is None else f"{opportunity.max_size:.8f}",
                    f"{opportunity.age_seconds:.8f}",
                    f"{opportunity.volume_score:.8f}",
                    f"{opportunity.trend_percent:.8f}",
                    opportunity.execution_steps,
                    f"{opportunity.execution_time_seconds:.8f}",
                    opportunity.source,
                ]
            )
