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
                "input_currency",
                "input_amount",
                "output_amount",
                "gross_profit",
                "net_profit",
                "roi_percent",
                "profit_per_hour",
                "score",
                "confidence",
                "risk",
                "source",
            ]
        )
        for opportunity in opportunities:
            writer.writerow(
                [
                    opportunity.path_label,
                    opportunity.input_currency,
                    f"{opportunity.input_amount:.8f}",
                    f"{opportunity.output_amount:.8f}",
                    f"{opportunity.gross_profit:.8f}",
                    f"{opportunity.net_profit:.8f}",
                    f"{opportunity.roi_percent:.8f}",
                    f"{opportunity.profit_per_hour:.8f}",
                    f"{opportunity.score:.8f}",
                    f"{opportunity.confidence:.8f}",
                    opportunity.risk,
                    opportunity.source,
                ]
            )
