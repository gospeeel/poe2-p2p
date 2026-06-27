from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from pathlib import Path
from typing import Iterator

from .models import Opportunity, RateEdge


class SQLiteStore:
    def __init__(self, path: str | Path = "poe2_p2p.db") -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        with self.connection() as connection:
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
                    chain_type TEXT DEFAULT 'unknown' NOT NULL,
                    strategy_types TEXT DEFAULT 'generic' NOT NULL,
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
                    max_size REAL,
                    age_seconds REAL DEFAULT 0 NOT NULL,
                    volume_score REAL DEFAULT 0 NOT NULL,
                    trend_percent REAL DEFAULT 0 NOT NULL,
                    execution_steps INTEGER DEFAULT 0 NOT NULL,
                    execution_time_seconds REAL DEFAULT 0 NOT NULL,
                    value_currency TEXT DEFAULT 'Divine Orb' NOT NULL,
                    input_value REAL DEFAULT 0 NOT NULL,
                    output_value REAL DEFAULT 0 NOT NULL,
                    net_profit_value REAL DEFAULT 0 NOT NULL,
                    profit_per_hour_value REAL DEFAULT 0 NOT NULL,
                    mirror_value REAL,
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
            "chain_type": "ALTER TABLE opportunities ADD COLUMN chain_type TEXT DEFAULT 'unknown' NOT NULL",
            "strategy_types": "ALTER TABLE opportunities ADD COLUMN strategy_types TEXT DEFAULT 'generic' NOT NULL",
            "max_size": "ALTER TABLE opportunities ADD COLUMN max_size REAL",
            "age_seconds": "ALTER TABLE opportunities ADD COLUMN age_seconds REAL DEFAULT 0 NOT NULL",
            "volume_score": "ALTER TABLE opportunities ADD COLUMN volume_score REAL DEFAULT 0 NOT NULL",
            "trend_percent": "ALTER TABLE opportunities ADD COLUMN trend_percent REAL DEFAULT 0 NOT NULL",
            "execution_steps": "ALTER TABLE opportunities ADD COLUMN execution_steps INTEGER DEFAULT 0 NOT NULL",
            "execution_time_seconds": "ALTER TABLE opportunities ADD COLUMN execution_time_seconds REAL DEFAULT 0 NOT NULL",
            "value_currency": "ALTER TABLE opportunities ADD COLUMN value_currency TEXT DEFAULT 'Divine Orb' NOT NULL",
            "input_value": "ALTER TABLE opportunities ADD COLUMN input_value REAL DEFAULT 0 NOT NULL",
            "output_value": "ALTER TABLE opportunities ADD COLUMN output_value REAL DEFAULT 0 NOT NULL",
            "net_profit_value": "ALTER TABLE opportunities ADD COLUMN net_profit_value REAL DEFAULT 0 NOT NULL",
            "profit_per_hour_value": "ALTER TABLE opportunities ADD COLUMN profit_per_hour_value REAL DEFAULT 0 NOT NULL",
            "mirror_value": "ALTER TABLE opportunities ADD COLUMN mirror_value REAL",
        }
        for column, statement in migrations.items():
            if column not in existing:
                connection.execute(statement)

    def save_rates(self, rates: list[RateEdge]) -> None:
        with self.connection() as connection:
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
        with self.connection() as connection:
            connection.executemany(
                """
                INSERT INTO opportunities (
                    path,
                    chain_type,
                    strategy_types,
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
                    max_size,
                    age_seconds,
                    volume_score,
                    trend_percent,
                    execution_steps,
                    execution_time_seconds,
                    value_currency,
                    input_value,
                    output_value,
                    net_profit_value,
                    profit_per_hour_value,
                    mirror_value,
                    source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        opportunity.path_label,
                        opportunity.chain_type.value,
                        "|".join(item.value for item in opportunity.strategy_types),
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
                        opportunity.max_size,
                        opportunity.age_seconds,
                        opportunity.volume_score,
                        opportunity.trend_percent,
                        opportunity.execution_steps,
                        opportunity.execution_time_seconds,
                        opportunity.value_currency,
                        opportunity.input_value,
                        opportunity.output_value,
                        opportunity.net_profit_value,
                        opportunity.profit_per_hour_value,
                        opportunity.mirror_value,
                        opportunity.source,
                    )
                    for opportunity in opportunities
                ],
            )

    def list_recent_opportunities(self, limit: int = 20) -> list[dict]:
        with self.connection() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    path,
                    chain_type,
                    strategy_types,
                    input_currency,
                    input_amount,
                    output_amount,
                    net_profit,
                    roi_percent,
                    profit_per_hour,
                    score,
                    confidence,
                    risk,
                    max_size,
                    age_seconds,
                    volume_score,
                    trend_percent,
                    execution_steps,
                    execution_time_seconds,
                    value_currency,
                    input_value,
                    output_value,
                    net_profit_value,
                    profit_per_hour_value,
                    mirror_value,
                    created_at
                FROM opportunities
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def total_recorded_net_profit(self) -> float:
        with self.connection() as connection:
            value = connection.execute(
                "SELECT COALESCE(SUM(net_profit), 0) FROM opportunities"
            ).fetchone()[0]
        return float(value)

    def total_recorded_net_profit_value(self) -> float:
        with self.connection() as connection:
            value = connection.execute(
                "SELECT COALESCE(SUM(net_profit_value), 0) FROM opportunities"
            ).fetchone()[0]
        return float(value)
