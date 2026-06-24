from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QLabel,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import Opportunity


class OverlayWindow(QMainWindow):
    def __init__(self, opportunities: list[Opportunity]) -> None:
        super().__init__()
        self.opportunities = [item for item in opportunities if item.net_profit > 0]
        self.setWindowTitle("POE2 P2P")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(940, 280)

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)

        title = QLabel("POE2 P2P Arbitrage")
        title.setObjectName("title")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Path", "Input", "Output", "Net Profit", "ROI %", "Profit/h", "Risk", "Confidence"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.table)
        self.setCentralWidget(root)
        self.refresh_table()
        QShortcut("Esc", self, activated=self.close)
        QShortcut("Ctrl+R", self, activated=self.refresh_table)
        self.setStyleSheet(
            """
            #root {
                background: rgba(18, 20, 22, 220);
                border: 1px solid rgba(220, 220, 220, 80);
            }
            #title {
                color: #f0f0f0;
                font-size: 16px;
                font-weight: 600;
                padding: 4px;
            }
            QTableWidget {
                background: rgba(28, 31, 34, 230);
                color: #e8e8e8;
                gridline-color: rgba(255, 255, 255, 35);
                border: 0;
            }
            QHeaderView::section {
                background: rgba(40, 44, 48, 240);
                color: #ffffff;
                border: 0;
                padding: 5px;
            }
            """
        )

    def refresh_table(self) -> None:
        self.table.setRowCount(len(self.opportunities))
        for row, opportunity in enumerate(self.opportunities):
            values = [
                opportunity.path_label,
                f"{opportunity.input_amount:.2f} {opportunity.input_currency}",
                f"{opportunity.output_amount:.2f} {opportunity.input_currency}",
                f"{opportunity.net_profit:.2f}",
                f"{opportunity.roi_percent:.2f}",
                f"{opportunity.profit_per_hour:.2f}",
                opportunity.risk,
                f"{opportunity.confidence:.2f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {3, 4} and opportunity.net_profit > 0:
                    item.setForeground(Qt.GlobalColor.green)
                self.table.setItem(row, column, item)


def run_overlay(opportunities: list[Opportunity]) -> int:
    app = QApplication(sys.argv)
    window = OverlayWindow(opportunities)
    window.show()
    return app.exec()
