from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Opportunity, RateEdge


class SQLiteStore:
    def __init__(self, path: str | Path = "poe2_p2p.db") -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_currency TEXT NOT NULL,
                    to_currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    observed_stock REAL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    input_currency TEXT NOT NULL,
                    input_amount REAL NOT NULL,
                    output_amount REAL NOT NULL,
                    gross_profit REAL NOT NULL,
                    net_profit REAL NOT NULL,
                    roi_percent REAL NOT NULL,
                    confidence REAL NOT NULL,
                    profit_per_hour REAL DEFAULT 0 NOT NULL,
                    score REAL DEFAULT 0 NOT NULL,
                    risk TEXT DEFAULT 'unknown' NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_opportunity_columns(connection)

    @staticmethod
    def _ensure_opportunity_columns(connection: sqlite3.Connection) -> None:
        existing = {
            row[1]
            for row in connection.execute("PRAGMA table_info(opportunities)").fetchall()
        }
        migrations = {
            "profit_per_hour": "ALTER TABLE opportunities ADD COLUMN profit_per_hour REAL DEFAULT 0 NOT NULL",
            "score": "ALTER TABLE opportunities ADD COLUMN score REAL DEFAULT 0 NOT NULL",
            "risk": "ALTER TABLE opportunities ADD COLUMN risk TEXT DEFAULT 'unknown' NOT NULL",
        }
        for column, statement in migrations.items():
            if column not in existing:
                connection.execute(statement)

    def save_rates(self, rates: list[RateEdge]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO rates (
                    from_currency,
                    to_currency,
                    rate,
                    source,
                    confidence,
                    observed_stock,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        rate.from_currency,
                        rate.to_currency,
                        rate.rate,
                        rate.source,
                        rate.confidence,
                        rate.observed_stock,
                        rate.timestamp.isoformat(),
                    )
                    for rate in rates
                ],
            )

    def save_opportunities(self, opportunities: list[Opportunity]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO opportunities (
                    path,
                    input_currency,
                    input_amount,
                    output_amount,
                    gross_profit,
                    net_profit,
                    roi_percent,
                    confidence,
                    profit_per_hour,
                    score,
                    risk,
                    source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        opportunity.path_label,
                        opportunity.input_currency,
                        opportunity.input_amount,
                        opportunity.output_amount,
                        opportunity.gross_profit,
                        opportunity.net_profit,
                        opportunity.roi_percent,
                        opportunity.confidence,
                        opportunity.profit_per_hour,
                        opportunity.score,
                        opportunity.risk,
                        opportunity.source,
                    )
                    for opportunity in opportunities
                ],
            )

    def list_recent_opportunities(self, limit: int = 20) -> list[dict]:
        with self.connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    path,
                    input_currency,
                    input_amount,
                    output_amount,
                    net_profit,
                    roi_percent,
                    profit_per_hour,
                    score,
                    confidence,
                    risk,
                    created_at
                FROM opportunities
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def total_recorded_net_profit(self) -> float:
        with self.connect() as connection:
            value = connection.execute(
                "SELECT COALESCE(SUM(net_profit), 0) FROM opportunities"
            ).fetchone()[0]
        return float(value)
