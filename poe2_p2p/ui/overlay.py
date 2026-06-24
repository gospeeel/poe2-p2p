from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizeGrip,
    QSlider,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..models import CHAIN_TYPE_LABELS, ChainType, Opportunity


ALIASES = {
    "Exalted Orb": "Exalted",
    "Divine Orb": "Divine",
    "Chaos Orb": "Chaos",
    "Omen of Whittling": "Omen of Whittling",
}

RISK_LABELS = {
    "low": "низкий",
    "medium": "средний",
    "high": "высокий",
    "unknown": "неизвестно",
}

CHAIN_FILTERS = {
    "Любой тип": None,
    "Прямая": ChainType.DIRECT,
    "Обратная": ChainType.REVERSE,
    "Треугольная": ChainType.TRIANGULAR,
    "Через Chaos": ChainType.CROSS_CURRENCY,
    "Многошаговая": ChainType.MULTI_HOP,
}

ICON_COLORS = {
    "Exalted Orb": ("#d9b15f", "EX"),
    "Divine Orb": ("#75a9ff", "DIV"),
    "Chaos Orb": ("#b168d6", "CH"),
    "Omen of Whittling": ("#7bd88f", "OM"),
}


class DelayedToolTipFilter(QWidget):
    def __init__(self, delay_ms: int = 2000) -> None:
        super().__init__()
        self.delay_ms = delay_ms
        self._target = None
        self._position = QPoint()
        self._text = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show_tooltip)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Enter:
            text = watched.toolTip()
            if text:
                watched.setToolTip("")
                watched.setProperty("_delayed_tooltip", text)
            text = watched.property("_delayed_tooltip") or ""
            if text:
                self._target = watched
                self._position = watched.mapToGlobal(watched.rect().center())
                self._text = text
                self._timer.start(self.delay_ms)
        elif event.type() in {
            QEvent.Type.Leave,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Hide,
        }:
            self._timer.stop()
            QToolTip.hideText()
        return False

    def _show_tooltip(self) -> None:
        if self._target and self._text:
            QToolTip.showText(self._position, self._text, self._target)


class TableDelayedToolTipFilter(QObject):
    def __init__(self, table: QTableWidget, delay_ms: int = 2000) -> None:
        super().__init__(table)
        self.table = table
        self.delay_ms = delay_ms
        self._position = QPoint()
        self._text = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show_tooltip)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.MouseMove:
            item = self.table.itemAt(event.position().toPoint())
            text = item.data(Qt.ItemDataRole.UserRole) if item else ""
            if text != self._text:
                self._timer.stop()
                QToolTip.hideText()
                self._text = text or ""
                if self._text:
                    self._position = self.table.viewport().mapToGlobal(event.position().toPoint())
                    self._timer.start(self.delay_ms)
        elif event.type() in {QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.Hide}:
            self._timer.stop()
            self._text = ""
            QToolTip.hideText()
        return False

    def _show_tooltip(self) -> None:
        if self._text:
            QToolTip.showText(self._position, self._text, self.table.viewport())


class TitleBar(QFrame):
    def __init__(self, window: "OverlayWindow") -> None:
        super().__init__()
        self.window = window
        self._drag_position: QPoint | None = None
        self.setObjectName("titleBar")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_position = None
        event.accept()


class OverlayWindow(QMainWindow):
    def __init__(self, opportunities: list[Opportunity]) -> None:
        super().__init__()
        self.opportunities = [item for item in opportunities if item.net_profit > 0]
        self.filtered_opportunities: list[Opportunity] = []
        self.compact_mode = False
        self.tooltip_filter = DelayedToolTipFilter()
        self.setWindowTitle("POE2 P2P")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(760, 260)
        self.resize(1120, 420)
        self.setWindowOpacity(0.94)

        self.root = QWidget()
        self.root.setObjectName("root")
        self.layout = QVBoxLayout(self.root)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)
        self.setCentralWidget(self.root)

        self._build_title_bar()
        self._build_action_bar()
        self._build_filter_bar()
        self._build_status()
        self._build_table()
        self._build_footer()
        self._build_tray()
        self._install_shortcuts()
        self._apply_style()
        self.apply_filters()

    def _build_title_bar(self) -> None:
        self.title_bar = TitleBar(self)
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel("POE2 P2P")
        title.setObjectName("title")
        subtitle = QLabel("Источник: пример со скриншотов | Последнее обновление: сейчас")
        subtitle.setObjectName("subtitle")
        subtitle.installEventFilter(self.tooltip_filter)
        subtitle.setToolTip(
            "Пока таблица использует тестовые курсы со скриншотов. "
            "Live scan будет подключен следующим этапом."
        )

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.always_on_top = QCheckBox("Поверх игры")
        self.always_on_top.setChecked(True)
        self.always_on_top.stateChanged.connect(self.toggle_always_on_top)
        self._delayed_tip(
            self.always_on_top,
            "Если включено, окно остается поверх POE2. "
            "Отключи, если мешает другим окнам.",
        )

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(70, 100)
        self.opacity_slider.setValue(94)
        self.opacity_slider.setFixedWidth(110)
        self.opacity_slider.valueChanged.connect(lambda value: self.setWindowOpacity(value / 100))
        self._delayed_tip(self.opacity_slider, "Прозрачность окна: 70-100%.")

        settings_button = self._button("Настройки", self.show_settings_placeholder)
        compact_button = self._button("Компактно", self.toggle_compact_mode)
        minimize_button = self._button("Скрыть", self.hide_to_tray)
        close_button = self._button("X", self.close)
        close_button.setObjectName("dangerButton")

        layout.addLayout(title_box, 1)
        layout.addWidget(self.always_on_top)
        layout.addWidget(QLabel("Прозрачность"))
        layout.addWidget(self.opacity_slider)
        layout.addWidget(settings_button)
        layout.addWidget(compact_button)
        layout.addWidget(minimize_button)
        layout.addWidget(close_button)
        self.layout.addWidget(self.title_bar)

    def _build_action_bar(self) -> None:
        bar = QFrame()
        bar.setObjectName("panel")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)

        actions = [
            ("Скан пары", self.scan_pair_placeholder, "Снять текущий Market Ratio из окна NPC Currency Exchange."),
            ("Скан цепочки", self.scan_chain_placeholder, "Проверить несколько шагов связки, например Exalted -> Item -> Divine -> Exalted."),
            ("Кандидаты", self.refresh_candidates_placeholder, "Обновить список валют и items, которые стоит проверить первыми."),
            ("Экспорт", self.export_placeholder, "Сохранить найденные возможности в CSV или отчет."),
        ]
        for label, callback, tip in actions:
            button = self._button(label, callback)
            self._delayed_tip(button, tip)
            layout.addWidget(button)
        layout.addStretch(1)
        self.layout.addWidget(bar)

    def _build_filter_bar(self) -> None:
        bar = QFrame()
        bar.setObjectName("panel")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)

        self.base_filter = QComboBox()
        self.base_filter.addItems(["Любая база", "Exalted", "Divine", "Chaos"])
        self.base_filter.currentIndexChanged.connect(self.apply_filters)
        self._delayed_tip(self.base_filter, "Фильтр по валюте, от которой начинается и к которой возвращается связка.")

        self.chain_filter = QComboBox()
        self.chain_filter.addItems(list(CHAIN_FILTERS))
        self.chain_filter.currentIndexChanged.connect(self.apply_filters)
        self._delayed_tip(
            self.chain_filter,
            "Тип экономической связки. Например, треугольная цепочка использует две разные сделки между базовой валютой и hub-валютой.",
        )

        self.min_roi_filter = QDoubleSpinBox()
        self.min_roi_filter.setRange(0, 999)
        self.min_roi_filter.setDecimals(1)
        self.min_roi_filter.setSuffix("% доход")
        self.min_roi_filter.valueChanged.connect(self.apply_filters)
        self._delayed_tip(self.min_roi_filter, "Показывать только связки с доходностью выше указанного процента.")

        self.min_confidence_filter = QDoubleSpinBox()
        self.min_confidence_filter.setRange(0, 1)
        self.min_confidence_filter.setDecimals(2)
        self.min_confidence_filter.setSingleStep(0.05)
        self.min_confidence_filter.setPrefix("Уверенность ")
        self.min_confidence_filter.valueChanged.connect(self.apply_filters)
        self._delayed_tip(
            self.min_confidence_filter,
            "Минимальная уверенность данных. Низкая уверенность часто означает риск OCR-ошибки.",
        )

        self.min_profit_filter = QDoubleSpinBox()
        self.min_profit_filter.setRange(0, 1_000_000)
        self.min_profit_filter.setDecimals(0)
        self.min_profit_filter.setPrefix("Профит ")
        self.min_profit_filter.valueChanged.connect(self.apply_filters)
        self._delayed_tip(self.min_profit_filter, "Показывать только связки с чистым профитом выше указанного.")

        self.min_profit_hour_filter = QDoubleSpinBox()
        self.min_profit_hour_filter.setRange(0, 1_000_000)
        self.min_profit_hour_filter.setDecimals(0)
        self.min_profit_hour_filter.setPrefix("Профит/ч ")
        self.min_profit_hour_filter.valueChanged.connect(self.apply_filters)
        self._delayed_tip(self.min_profit_hour_filter, "Показывать только связки с расчетным профитом в час выше указанного.")

        self.sort_filter = QComboBox()
        self.sort_filter.addItems(["Профит", "Доходность", "Профит/ч", "Уверенность"])
        self.sort_filter.currentIndexChanged.connect(self.apply_filters)
        self._delayed_tip(self.sort_filter, "Порядок сортировки найденных связок.")

        self.quick_preset = QComboBox()
        self.quick_preset.addItems(["Свои фильтры", "Безопасный", "Баланс", "Агрессивный"])
        self.quick_preset.currentIndexChanged.connect(self.apply_quick_preset)
        self._delayed_tip(
            self.quick_preset,
            "Быстрые наборы фильтров. Безопасный строже к уверенности, агрессивный показывает больше рискованных связок.",
        )

        for label, widget in [
            ("База", self.base_filter),
            ("Тип", self.chain_filter),
            ("Мин.", self.min_roi_filter),
            ("Профит", self.min_profit_filter),
            ("Профит/ч", self.min_profit_hour_filter),
            ("OCR", self.min_confidence_filter),
            ("Сортировка", self.sort_filter),
            ("Пресет", self.quick_preset),
        ]:
            text = QLabel(label)
            text.setObjectName("filterLabel")
            layout.addWidget(text)
            layout.addWidget(widget)
        layout.addStretch(1)
        self.layout.addWidget(bar)

    def _build_status(self) -> None:
        self.status_label = QLabel("Готово. Используются тестовые данные; сканирование игры еще не подключено.")
        self.status_label.setObjectName("status")
        self._delayed_tip(
            self.status_label,
            "Статус последнего действия. Здесь будет видно, удался ли scan, OCR и пересчет связок.",
        )
        self.layout.addWidget(self.status_label)
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.hide()
        self._delayed_tip(
            self.error_label,
            "Здесь появляются ошибки OCR, неверной области сканирования, отсутствующего Tesseract или устаревших данных.",
        )
        self.layout.addWidget(self.error_label)

    def _build_table(self) -> None:
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            [
                "Иконки",
                "Маршрут",
                "Тип",
                "Вход",
                "Выход",
                "Профит",
                "Доходность",
                "Профит/ч",
                "Уверенность",
                "Риск",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)
        self.table_tooltip_filter = TableDelayedToolTipFilter(self.table)
        self.table.viewport().installEventFilter(self.table_tooltip_filter)
        self.layout.addWidget(self.table, 1)

        self.empty_label = QLabel("Пока нет подходящих возможностей. Ослабь фильтры или выполни scan.")
        self.empty_label.setObjectName("empty")
        self.empty_label.hide()
        self.layout.addWidget(self.empty_label)

    def _build_footer(self) -> None:
        footer = QHBoxLayout()
        self.hotkeys_label = QLabel("Бинды: Esc - закрыть | Ctrl+R - обновить | Ctrl+H - скрыть | Ctrl+M - компактно")
        self.hotkeys_label.setObjectName("footer")
        self._delayed_tip(
            self.hotkeys_label,
            "Это локальные бинды активного окна. Глобальные бинды поверх игры будут добавлены отдельно.",
        )
        footer.addWidget(self.hotkeys_label)
        footer.addStretch(1)
        footer.addWidget(QSizeGrip(self))
        self.layout.addLayout(footer)

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self._build_icon(), self)
        menu = QMenu()
        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.showNormal)
        hide_action = QAction("Скрыть", self)
        hide_action.triggered.connect(self.hide)
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("POE2 P2P")
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _install_shortcuts(self) -> None:
        QShortcut("Esc", self, activated=self.close)
        QShortcut("Ctrl+R", self, activated=self.apply_filters)
        QShortcut("Ctrl+H", self, activated=self.hide_to_tray)
        QShortcut("Ctrl+M", self, activated=self.toggle_compact_mode)

    def apply_filters(self) -> None:
        visible = []
        base = self.base_filter.currentText() if hasattr(self, "base_filter") else "Любая база"
        chain_type = CHAIN_FILTERS.get(self.chain_filter.currentText()) if hasattr(self, "chain_filter") else None
        min_roi = self.min_roi_filter.value() if hasattr(self, "min_roi_filter") else 0
        min_confidence = self.min_confidence_filter.value() if hasattr(self, "min_confidence_filter") else 0
        min_profit = self.min_profit_filter.value() if hasattr(self, "min_profit_filter") else 0
        min_profit_hour = self.min_profit_hour_filter.value() if hasattr(self, "min_profit_hour_filter") else 0
        for opportunity in self.opportunities:
            if base != "Любая база" and not opportunity.path_label.startswith(base):
                continue
            if chain_type is not None and opportunity.chain_type != chain_type:
                continue
            if opportunity.roi_percent < min_roi:
                continue
            if opportunity.net_profit < min_profit:
                continue
            if opportunity.profit_per_hour < min_profit_hour:
                continue
            if opportunity.confidence < min_confidence:
                continue
            visible.append(opportunity)
        visible = self._sort_opportunities(visible)
        self.filtered_opportunities = visible
        self._render_rows(visible)
        self.status_label.setText(f"Показано связок: {len(visible)} из {len(self.opportunities)}")

    def _render_rows(self, opportunities: list[Opportunity]) -> None:
        self.table.setRowCount(len(opportunities))
        self.empty_label.setVisible(not opportunities)
        self.table.setVisible(bool(opportunities))
        for row, opportunity in enumerate(opportunities):
            values = [
                self._path_icons(opportunity),
                self._path_label(opportunity),
                CHAIN_TYPE_LABELS.get(opportunity.chain_type, "неизвестно"),
                f"{opportunity.input_amount:.2f} {self._alias(opportunity.input_currency)}",
                f"{opportunity.output_amount:.2f} {self._alias(opportunity.input_currency)}",
                f"{opportunity.net_profit:.2f}",
                f"{opportunity.roi_percent:.2f}%",
                f"{opportunity.profit_per_hour:.2f}",
                f"{opportunity.confidence:.2f}",
                RISK_LABELS.get(opportunity.risk, opportunity.risk),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, self._opportunity_tooltip(opportunity))
                if column == 0:
                    item.setIcon(self._icon_for_currency(opportunity.path[0]))
                if column in {5, 6} and opportunity.net_profit > 0:
                    item.setForeground(QColor("#4bd16f"))
                if column == 9 and opportunity.risk == "high":
                    item.setForeground(QColor("#ff6b6b"))
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 24 if self.compact_mode else 34)

    def apply_quick_preset(self) -> None:
        preset = self.quick_preset.currentText()
        if preset == "Безопасный":
            self.min_roi_filter.setValue(2.0)
            self.min_confidence_filter.setValue(0.85)
        elif preset == "Баланс":
            self.min_roi_filter.setValue(1.0)
            self.min_confidence_filter.setValue(0.70)
        elif preset == "Агрессивный":
            self.min_roi_filter.setValue(0.5)
            self.min_confidence_filter.setValue(0.00)
        self.apply_filters()

    def _sort_opportunities(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        if not hasattr(self, "sort_filter"):
            return opportunities
        sort = self.sort_filter.currentText()
        keys = {
            "Профит": lambda item: item.net_profit,
            "Доходность": lambda item: item.roi_percent,
            "Профит/ч": lambda item: item.profit_per_hour,
            "Уверенность": lambda item: item.confidence,
        }
        return sorted(opportunities, key=keys.get(sort, keys["Профит"]), reverse=True)

    def toggle_compact_mode(self) -> None:
        self.compact_mode = not self.compact_mode
        self.resize(860, 260) if self.compact_mode else self.resize(1120, 420)
        self.apply_filters()
        self.status_label.setText("Компактный режим включен." if self.compact_mode else "Полный режим включен.")

    def toggle_always_on_top(self) -> None:
        flags = self.windowFlags()
        if self.always_on_top.isChecked():
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def hide_to_tray(self) -> None:
        self.hide()
        if self.tray.isVisible():
            self.tray.showMessage("POE2 P2P", "Overlay скрыт. Вернуть можно через значок в трее.")

    def show_settings_placeholder(self) -> None:
        self.status_label.setText("Настройки будут добавлены следующим этапом: бинды, фильтры, OCR и тема.")

    def scan_pair_placeholder(self) -> None:
        self.show_error("Скан пары еще не подключен: нужен следующий этап снимка области игры + OCR.")
        self.status_label.setText("Скан пары еще не подключен. Следующий этап: снимок области игры + OCR.")

    def scan_chain_placeholder(self) -> None:
        self.status_label.setText("Скан цепочки еще не подключен. Сейчас доступны расчетные примеры.")

    def refresh_candidates_placeholder(self) -> None:
        self.status_label.setText("Кандидаты обновляются через poe.ninja в CLI; UI-подключение будет следующим.")

    def export_placeholder(self) -> None:
        self.status_label.setText("Экспорт доступен через CLI. UI-кнопка будет подключена к CSV следующим этапом.")

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.hide()

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal() if self.isHidden() else self.hide()

    def _button(self, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def _delayed_tip(self, widget: QWidget, text: str) -> None:
        widget.setToolTip(text)
        widget.installEventFilter(self.tooltip_filter)

    def _path_label(self, opportunity: Opportunity) -> str:
        return " -> ".join(self._alias(part) for part in opportunity.path)

    def _path_icons(self, opportunity: Opportunity) -> str:
        icons = []
        for part in opportunity.path:
            if part == "Exalted Orb":
                icons.append("EX")
            elif part == "Divine Orb":
                icons.append("DIV")
            elif part == "Chaos Orb":
                icons.append("CH")
            else:
                icons.append("IT")
        return " ".join(icons)

    def _icon_for_currency(self, name: str) -> QIcon:
        color, text = ICON_COLORS.get(name, ("#6f7b88", "IT"))
        pixmap = QPixmap(28, 28)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 26, 26)
        painter.setPen(QColor("#101316"))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _alias(name: str) -> str:
        return ALIASES.get(name, name)

    def _opportunity_tooltip(self, opportunity: Opportunity) -> str:
        return (
            f"Связка: {self._path_label(opportunity)}\n"
            f"Тип: {CHAIN_TYPE_LABELS.get(opportunity.chain_type, 'неизвестно')}\n"
            f"Вход: {opportunity.input_amount:.2f} {self._alias(opportunity.input_currency)}\n"
            f"Выход: {opportunity.output_amount:.2f} {self._alias(opportunity.input_currency)}\n"
            f"Чистый профит: {opportunity.net_profit:.2f}\n"
            f"Доходность: {opportunity.roi_percent:.2f}%\n"
            f"Уверенность данных: {opportunity.confidence:.2f}\n"
            f"Источник курсов: {opportunity.source}\n\n"
            "Доходность показывает прибыль одного полного цикла в процентах. "
            "Профит/ч зависит от скорости исполнения и будет точнее после сканирования игры."
        )

    @staticmethod
    def _build_icon() -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#2f8cff"))
        return QIcon(pixmap)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #root {
                background: rgba(17, 20, 23, 235);
                border: 1px solid rgba(125, 140, 160, 130);
            }
            #titleBar, #panel {
                background: rgba(34, 39, 45, 220);
                border: 1px solid rgba(255, 255, 255, 26);
            }
            #title {
                color: #f4f6f8;
                font-size: 17px;
                font-weight: 700;
            }
            #subtitle, #footer, #status, #filterLabel {
                color: #b7c0ca;
                font-size: 12px;
            }
            #error {
                color: #ffd0d0;
                background: rgba(98, 36, 45, 210);
                border: 1px solid rgba(255, 110, 120, 110);
                padding: 6px;
            }
            #empty {
                color: #d0d6dd;
                padding: 24px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton {
                background: #2c3440;
                color: #eef2f6;
                border: 1px solid #465363;
                padding: 5px 9px;
                min-height: 22px;
            }
            QPushButton:hover {
                background: #384555;
            }
            #dangerButton {
                background: #5a2630;
                border-color: #8b3b47;
            }
            QComboBox, QDoubleSpinBox {
                background: #161a1f;
                color: #eef2f6;
                border: 1px solid #465363;
                padding: 4px;
            }
            QTableWidget {
                background: rgba(22, 26, 30, 238);
                alternate-background-color: rgba(28, 33, 38, 238);
                color: #e8edf2;
                gridline-color: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 28);
            }
            QHeaderView::section {
                background: #2b333d;
                color: #ffffff;
                border: 0;
                border-right: 1px solid rgba(255, 255, 255, 30);
                padding: 6px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #465363;
            }
            QSlider::handle:horizontal {
                width: 12px;
                background: #d8dee6;
                margin: -5px 0;
            }
            """
        )


def run_overlay(opportunities: list[Opportunity]) -> int:
    app = QApplication(sys.argv)
    window = OverlayWindow(opportunities)
    window.show()
    return app.exec()
