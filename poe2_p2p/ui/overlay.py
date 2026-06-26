from __future__ import annotations

import sys
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QLineEdit,
    QRubberBand,
    QSizeGrip,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..calibration import (
    LEFT_ITEM,
    MARKET_RATIO,
    REGION_LABELS,
    RIGHT_ITEM,
    default_calibration_profile,
    load_calibration_profile,
    load_region,
    save_calibration_profile,
)
from ..calculator import ArbitrageCalculator
from ..capture import CaptureDependencyError, capture_screen_region, crop_image_file
from ..config import DEFAULT_MARKET_RATIO_REGION, CropRegion
from ..diagnostics import run_diagnostics
from ..exporter import export_opportunities_csv
from ..icon_cache import IconCache
from ..logging_utils import LOG_DIR, LOG_FILE
from ..global_hotkeys import GlobalHotkeyManager
from ..models import (
    CHAIN_TYPE_LABELS,
    STRATEGY_TYPE_DESCRIPTIONS,
    STRATEGY_TYPE_LABELS,
    ChainType,
    Opportunity,
    RateEdge,
    StrategyType,
)
from ..ocr import OCRDependencyError, detect_tesseract_cmd, read_ratio_from_image, read_text_from_image
from ..poe_ninja import fetch_currency_candidates
from ..presets import STRATEGY_PRESETS
from ..settings import ACTION_LABELS, AppSettings, find_hotkey_conflicts, load_settings, save_settings
from ..storage import SQLiteStore
from ..updater import check_for_updates


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

STRATEGY_FILTERS = {
    "Любая стратегия": None,
    **{STRATEGY_TYPE_LABELS[strategy]: strategy for strategy in StrategyType},
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


class RegionSelectionOverlay(QWidget):
    def __init__(self, callback, parent=None) -> None:
        super().__init__(parent)
        self.callback = callback
        self.origin = QPoint()
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.setWindowTitle("Выделение области")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowOpacity(0.25)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setStyleSheet("background: rgba(20, 120, 220, 80);")

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.origin = event.position().toPoint()
        self.rubber_band.setGeometry(QRect(self.origin, QSize()))
        self.rubber_band.show()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.rubber_band.isVisible():
            self.rubber_band.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        rect = QRect(self.origin, event.position().toPoint()).normalized()
        self.rubber_band.hide()
        if rect.width() > 0 and rect.height() > 0:
            self.callback(CropRegion(rect.x(), rect.y(), rect.width(), rect.height()))
        self.close()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        hint = QLabel("Настройки overlay, биндов и служебных проверок.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        self.always_on_top_input = QCheckBox("Окно остается поверх POE2")
        self.always_on_top_input.setChecked(settings.always_on_top)
        form.addRow("Поверх игры", self.always_on_top_input)

        self.click_through_input = QCheckBox("Мышь проходит через overlay в игру")
        self.click_through_input.setChecked(settings.click_through)
        form.addRow("Клики сквозь", self.click_through_input)

        self.opacity_input = QSpinBox()
        self.opacity_input.setRange(70, 100)
        self.opacity_input.setSuffix("%")
        self.opacity_input.setValue(settings.opacity)
        form.addRow("Прозрачность", self.opacity_input)

        self.hotkey_inputs: dict[str, QLineEdit] = {}
        for action, label in ACTION_LABELS.items():
            edit = QLineEdit(settings.hotkeys.get(action, ""))
            edit.setPlaceholderText("Например Ctrl+1")
            self.hotkey_inputs[action] = edit
            form.addRow(label, edit)
        self.ui_scale_input = QSpinBox()
        self.ui_scale_input.setRange(85, 125)
        self.ui_scale_input.setSingleStep(5)
        self.ui_scale_input.setSuffix("%")
        self.ui_scale_input.setValue(settings.ui_scale_percent)
        self.ui_scale_input.setToolTip("Масштаб таблицы и текста. 100% подходит как базовый размер, 110-125% удобнее для 1440p/4K.")
        form.addRow("Масштаб интерфейса", self.ui_scale_input)
        layout.addLayout(form)

        self.conflict_label = QLabel("")
        self.conflict_label.setObjectName("error")
        self.conflict_label.hide()
        layout.addWidget(self.conflict_label)

        if parent is not None:
            tools = QHBoxLayout()
            for label, method_name in [
                ("Калибровка", "open_calibration"),
                ("Диагностика", "run_diagnostics"),
                ("Логи", "open_logs"),
                ("Обновления", "check_updates"),
            ]:
                if hasattr(parent, method_name):
                    button = QPushButton(label)
                    button.clicked.connect(getattr(parent, method_name))
                    tools.addWidget(button)
            layout.addLayout(tools)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        hotkeys = {action: edit.text().strip() for action, edit in self.hotkey_inputs.items()}
        conflicts = find_hotkey_conflicts(hotkeys)
        if conflicts:
            values = ", ".join(conflicts)
            self.conflict_label.setText(f"Конфликт биндов: {values}")
            self.conflict_label.show()
            return
        self.settings.hotkeys = hotkeys
        self.settings.ui_scale_percent = self.ui_scale_input.value()
        self.settings.always_on_top = self.always_on_top_input.isChecked()
        self.settings.click_through = self.click_through_input.isChecked()
        self.settings.opacity = self.opacity_input.value()
        super().accept()


class CalibrationDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Калибровка OCR")
        self.setMinimumWidth(560)
        self.calibration_path = Path("calibration.json")
        self.profile = (
            load_calibration_profile(self.calibration_path)
            if self.calibration_path.exists()
            else default_calibration_profile()
        )
        self.current_region_key = MARKET_RATIO
        self.region = self.profile.regions[MARKET_RATIO]
        layout = QVBoxLayout(self)

        hint = QLabel(
            "Открой NPC Currency Exchange в игре и укажи область Market Ratio. "
            "Кнопки проверки снимают область прямо с экрана; файл нужен только для разработки."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        profile_form = QFormLayout()
        self.profile_name = QLineEdit(self.profile.name)
        self.resolution_width = self._spin(self.profile.resolution_width)
        self.resolution_height = self._spin(self.profile.resolution_height)
        self.profile_scale = QSpinBox()
        self.profile_scale.setRange(50, 200)
        self.profile_scale.setSuffix("%")
        self.profile_scale.setValue(self.profile.ui_scale_percent)
        profile_form.addRow("Профиль", self.profile_name)
        profile_form.addRow("Ширина экрана", self.resolution_width)
        profile_form.addRow("Высота экрана", self.resolution_height)
        profile_form.addRow("Масштаб UI игры", self.profile_scale)
        layout.addLayout(profile_form)

        self.use_file_input = QCheckBox("Использовать файл скриншота для разработки")
        self.use_file_input.toggled.connect(self.toggle_file_input)
        layout.addWidget(self.use_file_input)

        self.file_widget = QWidget()
        file_row = QHBoxLayout(self.file_widget)
        file_row.setContentsMargins(0, 0, 0, 0)
        self.image_path = QLineEdit("Screenshot_1.jpg")
        browse = QPushButton("Файл")
        browse.clicked.connect(self.choose_file)
        file_row.addWidget(QLabel("Скриншот"))
        file_row.addWidget(self.image_path, 1)
        file_row.addWidget(browse)
        layout.addWidget(self.file_widget)
        self.file_widget.hide()

        form = QFormLayout()
        self.region_selector = QComboBox()
        for key, label in REGION_LABELS.items():
            self.region_selector.addItem(label, key)
        self.region_selector.currentIndexChanged.connect(self.change_region)
        form.addRow("Область", self.region_selector)
        self.x_input = self._spin(self.region.x)
        self.y_input = self._spin(self.region.y)
        self.width_input = self._spin(self.region.width)
        self.height_input = self._spin(self.region.height)
        form.addRow("X", self.x_input)
        form.addRow("Y", self.y_input)
        form.addRow("Ширина", self.width_input)
        form.addRow("Высота", self.height_input)
        layout.addLayout(form)

        self.preview = QLabel("Предпросмотр появится после проверки.")
        self.preview.setObjectName("empty")
        self.preview.setMinimumHeight(120)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)

        self.result = QLabel("")
        self.result.setWordWrap(True)
        layout.addWidget(self.result)

        actions = QHBoxLayout()
        self.tooltip_filter = DelayedToolTipFilter()
        select_button = QPushButton("Выделить мышью")
        select_button.clicked.connect(self.select_region_with_mouse)
        select_button.setToolTip(
            "Откроет прозрачный слой поверх экрана. Зажми левую кнопку мыши, "
            "выдели прямоугольник нужной области и отпусти кнопку."
        )
        select_button.installEventFilter(self.tooltip_filter)
        preview_button = QPushButton("Проверить из игры")
        preview_button.clicked.connect(self.update_preview)
        ocr_button = QPushButton("Распознать")
        ocr_button.clicked.connect(self.run_ocr)
        accept_button = QPushButton("Принять")
        accept_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        for button in [select_button, preview_button, ocr_button, accept_button, cancel_button]:
            actions.addWidget(button)
        layout.addLayout(actions)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбери скриншот для разработки",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp)",
        )
        if path:
            self.image_path.setText(path)

    def toggle_file_input(self, checked: bool) -> None:
        self.file_widget.setVisible(checked)
        source = "файл скриншота" if checked else "живой экран"
        self.result.setText(f"Источник проверки: {source}.")

    def update_preview(self) -> None:
        region = self._region_from_inputs()
        output = "_calibration_preview.png"
        try:
            self._capture_calibration_preview(region, output)
        except (CaptureDependencyError, ValueError, FileNotFoundError) as error:
            self.result.setText(f"Не удалось получить область: {error}")
            return
        pixmap = QPixmap(output)
        self.preview.setPixmap(pixmap.scaled(420, 120, Qt.AspectRatioMode.KeepAspectRatio))
        source = "скриншот" if self.use_file_input.isChecked() else "экран игры"
        self.result.setText(f"Источник: {source}. Область: {region.x},{region.y},{region.width},{region.height}")

    def run_ocr(self) -> None:
        self.update_preview()
        try:
            from ..ocr import OCRDependencyError, read_ratio_from_image

            result = read_ratio_from_image("_calibration_preview.png")
        except (OCRDependencyError, ValueError, FileNotFoundError) as error:
            self.result.setText(f"Распознавание не сработало: {error}")
            return
        left, right = result.ratio
        self.result.setText(
            f"Распознано: {result.raw_text}\n"
            f"Курс: {left:g} : {right:g}\n"
            f"Уверенность: {result.confidence:.2f}"
        )

    def _capture_calibration_preview(self, region: CropRegion, output: str) -> None:
        if self.use_file_input.isChecked():
            crop_image_file(self.image_path.text(), region, output)
            return
        parent = self.parentWidget()
        parent_was_visible = bool(parent and parent.isVisible())
        self.hide()
        if parent_was_visible:
            parent.hide()
        QApplication.processEvents()
        time.sleep(0.35)
        try:
            capture_screen_region(region, output)
        finally:
            if parent_was_visible:
                parent.show()
            self.show()
            self.raise_()
            QApplication.processEvents()

    def accept(self) -> None:
        self._store_current_region()
        self.profile.name = self.profile_name.text().strip() or "Основной"
        self.profile.resolution_width = self.resolution_width.value()
        self.profile.resolution_height = self.resolution_height.value()
        self.profile.ui_scale_percent = self.profile_scale.value()
        save_calibration_profile(self.calibration_path, self.profile)
        super().accept()

    def select_region_with_mouse(self) -> None:
        self.selector = RegionSelectionOverlay(self.apply_mouse_region, self)
        self.selector.showFullScreen()
        self.result.setText("Выдели область мышью. Esc отменяет выбор.")

    def apply_mouse_region(self, region: CropRegion) -> None:
        self.x_input.setValue(region.x)
        self.y_input.setValue(region.y)
        self.width_input.setValue(region.width)
        self.height_input.setValue(region.height)
        self._store_current_region()
        label = REGION_LABELS.get(self.current_region_key, self.current_region_key)
        self.result.setText(
            f"Область {label} выбрана мышью: {region.x},{region.y},{region.width},{region.height}"
        )

    def change_region(self) -> None:
        self._store_current_region()
        key = self.region_selector.currentData()
        self.current_region_key = str(key)
        region = self.profile.regions.get(self.current_region_key, DEFAULT_MARKET_RATIO_REGION)
        self.x_input.setValue(region.x)
        self.y_input.setValue(region.y)
        self.width_input.setValue(region.width)
        self.height_input.setValue(region.height)
        self.result.setText(f"Выбрана область: {REGION_LABELS.get(self.current_region_key, self.current_region_key)}")

    def _store_current_region(self) -> None:
        if hasattr(self, "x_input"):
            self.profile.regions[self.current_region_key] = self._region_from_inputs()

    def _region_from_inputs(self) -> CropRegion:
        return CropRegion(
            x=self.x_input.value(),
            y=self.y_input.value(),
            width=self.width_input.value(),
            height=self.height_input.value(),
        )

    @staticmethod
    def _spin(value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 10000)
        spin.setValue(value)
        return spin


class FirstRunDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Первый запуск")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        tesseract = detect_tesseract_cmd()
        tesseract_status = f"найден: {tesseract}" if tesseract else "не найден"
        intro = QLabel(
            "Быстрая настройка POE2 P2P.\n\n"
            f"Tesseract OCR: {tesseract_status}\n"
            "После этого стоит открыть `Калибровка` и проверить область Market Ratio."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.league_input = QLineEdit(settings.league)
        form.addRow("Лига poe.ninja", self.league_input)
        layout.addLayout(form)

        hotkeys = QLabel(
            "Бинды по умолчанию:\n"
            "Скан пары: Ctrl+1\n"
            "Показать/скрыть окно: Ctrl+H\n"
            "Скан кандидатов: Ctrl+2\n"
            "Пауза/продолжить: Ctrl+P"
        )
        hotkeys.setWordWrap(True)
        layout.addWidget(hotkeys)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Готово")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Позже")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self.settings.league = self.league_input.text().strip() or self.settings.league
        self.settings.first_run_complete = True
        save_settings(self.settings)
        super().accept()


class OverlayWindow(QMainWindow):
    def __init__(self, opportunities: list[Opportunity]) -> None:
        super().__init__()
        self.opportunities = [item for item in opportunities if item.net_profit > 0]
        self.live_rates = self._rates_from_opportunities(opportunities)
        self.filtered_opportunities: list[Opportunity] = []
        self.chain_scan_active = False
        self.chain_scan_steps: list[str] = []
        self.candidate_trends: dict[str, float] = {}
        self.compact_mode = False
        self.filters_expanded = False
        self.settings = load_settings()
        self.icon_cache = IconCache()
        self.missing_icon_downloads: set[str] = set()
        self.paused = False
        self.tooltip_filter = DelayedToolTipFilter()
        self.setWindowTitle("POE2 P2P")
        self.setWindowIcon(self._build_icon())
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        if self.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(760, 260)
        self.resize(1120, 420)
        self.setWindowOpacity(self.settings.opacity / 100)

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
        self._build_auxiliary_tabs()
        self._build_footer()
        self._build_tray()
        self._install_shortcuts()
        self._install_global_hotkeys()
        self._apply_style()
        self._apply_ui_scale()
        self.apply_filters()
        if not self.settings.first_run_complete and os.environ.get("POE2_P2P_SKIP_FIRST_RUN") != "1":
            QTimer.singleShot(300, self.open_first_run_wizard)

    def _build_title_bar(self) -> None:
        self.title_bar = TitleBar(self)
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel(f"POE2 P2P v{__version__}")
        title.setObjectName("title")
        subtitle = QLabel("Источник: live scan / кеш кандидатов | Последнее обновление: сейчас")
        subtitle.setObjectName("subtitle")
        subtitle.installEventFilter(self.tooltip_filter)
        subtitle.setToolTip(
            "Кнопка `Скан пары` снимает текущую область Market Ratio с экрана. "
            "Стартовые строки нужны только как пример до первого live scan."
        )

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        settings_button = self._button("Настройки", self.open_settings)
        compact_button = self._button("Компактно", self.toggle_compact_mode)
        minimize_button = self._button("Скрыть", self.hide_to_tray)
        close_button = self._button("X", self.close)
        settings_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        compact_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton))
        minimize_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        close_button.setObjectName("dangerButton")

        layout.addLayout(title_box, 1)
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
            ("Скан пары", self.scan_pair, QStyle.StandardPixmap.SP_BrowserReload, "Снять текущий Market Ratio из окна NPC Currency Exchange."),
            ("Скан цепочки", self.scan_chain, QStyle.StandardPixmap.SP_ArrowForward, "Проверить несколько шагов связки, например Exalted -> Item -> Divine -> Exalted."),
            ("Фильтры", self.toggle_filters, QStyle.StandardPixmap.SP_FileDialogListView, "Показать или скрыть расширенные фильтры связок."),
            ("Калибровка", self.open_calibration, QStyle.StandardPixmap.SP_FileDialogDetailedView, "Настроить область экрана, из которой OCR читает Market Ratio."),
            ("Кандидаты", self.refresh_candidates, QStyle.StandardPixmap.SP_FileDialogContentsView, "Обновить список валют и предметов, которые стоит проверить первыми."),
            ("Экспорт", self.export_opportunities, QStyle.StandardPixmap.SP_DialogSaveButton, "Сохранить найденные возможности в CSV или отчет."),
        ]
        for label, callback, icon, tip in actions:
            button = self._button(label, callback)
            button.setIcon(self.style().standardIcon(icon))
            self._delayed_tip(button, tip)
            layout.addWidget(button)
        layout.addStretch(1)
        self.layout.addWidget(bar)

    def _build_filter_bar(self) -> None:
        bar = QFrame()
        self.filter_bar = bar
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

        self.strategy_filter = QComboBox()
        self.strategy_filter.addItems(list(STRATEGY_FILTERS))
        self.strategy_filter.currentIndexChanged.connect(self.apply_filters)
        self._delayed_tip(
            self.strategy_filter,
            "Экономический смысл связки: спред, ликвидность, валютный треугольник, корзина или другой режим исполнения.",
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

        self.max_age_filter = QDoubleSpinBox()
        self.max_age_filter.setRange(0, 10_000)
        self.max_age_filter.setDecimals(0)
        self.max_age_filter.setSuffix(" сек")
        self.max_age_filter.setValue(0)
        self.max_age_filter.valueChanged.connect(self.apply_filters)
        self._delayed_tip(self.max_age_filter, "Максимальный возраст данных. 0 означает не фильтровать по возрасту.")

        self.min_volume_filter = QDoubleSpinBox()
        self.min_volume_filter.setRange(0, 1_000_000_000)
        self.min_volume_filter.setDecimals(0)
        self.min_volume_filter.setPrefix("Объем ")
        self.min_volume_filter.valueChanged.connect(self.apply_filters)
        self._delayed_tip(self.min_volume_filter, "Минимальная оценка объема. Чем выше объем, тем проще исполнить связку.")

        self.sort_filter = QComboBox()
        self.sort_filter.addItems(["Профит", "Доходность", "Профит/ч", "Уверенность"])
        self.sort_filter.currentIndexChanged.connect(self.apply_filters)
        self._delayed_tip(self.sort_filter, "Порядок сортировки найденных связок.")

        self.quick_preset = QComboBox()
        self.quick_preset.addItems(["Свои фильтры", *(preset.label for preset in STRATEGY_PRESETS.values())])
        self.quick_preset.currentIndexChanged.connect(self.apply_quick_preset)
        self._delayed_tip(
            self.quick_preset,
            "Быстрые наборы фильтров. Безопасный строже к уверенности, агрессивный показывает больше рискованных связок.",
        )

        for label, widget in [
            ("База", self.base_filter),
            ("Тип", self.chain_filter),
            ("Стратегия", self.strategy_filter),
            ("Мин.", self.min_roi_filter),
            ("Профит", self.min_profit_filter),
            ("Профит/ч", self.min_profit_hour_filter),
            ("Возраст", self.max_age_filter),
            ("Объем", self.min_volume_filter),
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
        bar.hide()

    def _build_status(self) -> None:
        self.status_label = QLabel("Готово. Открой NPC Currency Exchange и нажми `Скан пары`.")
        self.status_label.setObjectName("status")
        self._delayed_tip(
            self.status_label,
            "Статус последнего действия. Здесь будет видно, удалось ли сканирование, OCR и пересчет связок.",
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
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs")
        self.opportunities_tab = QWidget()
        opportunities_layout = QVBoxLayout(self.opportunities_tab)
        opportunities_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Иконки",
                "Маршрут",
                "Вход",
                "Выход",
                "Профит",
                "Доходность",
                "Профит/ч",
                "Риск",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setIconSize(QSize(220, 40))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)
        self.table.itemSelectionChanged.connect(self.update_explain_view)
        self.table_tooltip_filter = TableDelayedToolTipFilter(self.table)
        self.table.viewport().installEventFilter(self.table_tooltip_filter)
        opportunities_layout.addWidget(self.table, 1)

        self.empty_label = QLabel("Пока нет подходящих возможностей. Ослабь фильтры или выполни сканирование.")
        self.empty_label.setObjectName("empty")
        self.empty_label.hide()
        opportunities_layout.addWidget(self.empty_label)
        self.tabs.addTab(self.opportunities_tab, "Связки")
        self.layout.addWidget(self.tabs, 1)

    def _build_auxiliary_tabs(self) -> None:
        self.live_scan_view = self._text_tab(
            "Скан",
            "Открой NPC Currency Exchange в игре и нажми `Скан пары`.\n\n"
            "Здесь появится OCR-текст, распознанный курс, названия сторон и результат пересчета.",
            "Сканирование показывает, что приложение реально прочитало из окна NPC Currency Exchange.",
        )
        self.candidates_view = self._text_tab(
            "Кандидаты",
            "Нажми `Кандидаты`, чтобы обновить список через poe.ninja/API.\n\n"
            "Здесь появятся валюты и предметы с высокой оценкой объема, трендом и spread.",
            "Кандидаты - это список валют и предметов, которые стоит проверить в NPC первыми.",
        )
        self.history_view = self._text_tab(
            "История",
            self._history_text(),
            "История помогает понять, какие связки повторяются и сколько профита они давали раньше.",
        )
        self.explain_view = self._text_tab(
            "Разбор",
            "Выбери связку в таблице, чтобы увидеть расчет по шагам.",
            "Разбор показывает, какой курс использовался на каждом шаге и откуда берется итоговый профит.",
        )
        self.ocr_debug_view = self._text_tab(
            "OCR",
            "Отладка OCR пока доступна через калибровку.\n\n"
            "Здесь будет предпросмотр снимка области, исходный текст, распознанный курс и уверенность.",
            "OCR отладка нужна, чтобы быстро находить ошибки распознавания цифр и десятичных точек.",
        )
        self.graph_view = self._text_tab(
            "Граф",
            self._graph_text(),
            "Граф показывает валюты как точки, а курсы обмена как ребра. Арбитраж - это прибыльный цикл в таком графе.",
        )

    def _text_tab(self, title: str, text: str, tooltip: str) -> QTextEdit:
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        self._delayed_tip(view, tooltip)
        self.tabs.addTab(view, title)
        return view

    def _settings_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        text = QLabel(
            "Основные настройки уже доступны через диалог.\n\n"
            "Следующие настройки: тема, глобальные бинды, OCR, профиль экрана и лига."
        )
        text.setWordWrap(True)
        button = QPushButton("Открыть настройки")
        button.clicked.connect(self.open_settings)
        update_button = QPushButton("Проверить обновления")
        update_button.clicked.connect(self.check_updates)
        self._delayed_tip(
            update_button,
            "Проверяет GitHub Releases и сообщает, есть ли новый установщик.",
        )
        first_run_button = QPushButton("Первый запуск")
        first_run_button.clicked.connect(self.open_first_run_wizard)
        self._delayed_tip(first_run_button, "Повторно открыть мастер первого запуска.")
        logs_button = QPushButton("Открыть логи")
        logs_button.clicked.connect(self.open_logs)
        self._delayed_tip(logs_button, "Открыть папку с файлом журнала ошибок.")
        diagnostics_button = QPushButton("Диагностика")
        diagnostics_button.clicked.connect(self.run_diagnostics)
        self._delayed_tip(
            diagnostics_button,
            "Создать отчет о запуске, Tesseract, калибровке, снимке экрана и OCR. "
            "Этот отчет нужен для проверки оставшихся Windows и живых пунктов.",
        )
        layout.addWidget(text)
        layout.addWidget(button)
        layout.addWidget(update_button)
        layout.addWidget(first_run_button)
        layout.addWidget(logs_button)
        layout.addWidget(diagnostics_button)
        layout.addStretch(1)
        self._delayed_tip(tab, "Раздел настроек приложения: бинды, OCR, внешний вид и профиль игры.")
        self.tabs.addTab(tab, "Настройки")
        return tab

    def _history_text(self) -> str:
        try:
            rows = SQLiteStore().list_recent_opportunities(10)
        except Exception:
            rows = []
        if not rows:
            return "История пока пустая. Запусти расчет или сканирование, чтобы появились записи."
        lines = []
        for row in rows:
            lines.append(
                f"{row['created_at']} | {row['path']} | профит {row['net_profit']:.2f} | доходность {row['roi_percent']:.2f}%"
            )
        return "\n".join(lines)

    def _graph_text(self) -> str:
        lines = ["Текущий граф тестовых связок:"]
        for opportunity in self.opportunities:
            lines.append(f"- {self._path_label(opportunity)}")
        return "\n".join(lines)

    def _build_footer(self) -> None:
        footer = QHBoxLayout()
        self.hotkeys_label = QLabel("Бинды: Esc - закрыть | Ctrl+R - обновить | Ctrl+H - скрыть | Ctrl+M - компактно")
        self.hotkeys_label.setObjectName("footer")
        self._refresh_hotkeys_label()
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
        self.click_through_action = QAction("Клики сквозь", self)
        self.click_through_action.setCheckable(True)
        self.click_through_action.setChecked(self.settings.click_through)
        self.click_through_action.triggered.connect(self.set_click_through)
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addAction(self.click_through_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("POE2 P2P")
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self._apply_click_through()

    def _install_shortcuts(self) -> None:
        QShortcut("Esc", self, activated=self.close)
        QShortcut("Ctrl+R", self, activated=self.apply_filters)
        QShortcut("Ctrl+H", self, activated=self.hide_to_tray)
        QShortcut("Ctrl+M", self, activated=self.toggle_compact_mode)

    def _install_global_hotkeys(self) -> None:
        self.hotkey_manager = GlobalHotkeyManager(
            self.settings.hotkeys,
            {
                "scan_pair": lambda: QTimer.singleShot(0, self.scan_pair),
                "toggle_overlay": lambda: QTimer.singleShot(0, self.toggle_overlay_visibility),
                "scan_candidates": lambda: QTimer.singleShot(0, self.refresh_candidates),
                "pause_resume": lambda: QTimer.singleShot(0, self.toggle_pause),
            },
            lambda message: QTimer.singleShot(0, lambda: self.status_label.setText(message)),
        )
        self.hotkey_manager.start()

    def apply_filters(self) -> None:
        visible = []
        base = self.base_filter.currentText() if hasattr(self, "base_filter") else "Любая база"
        chain_type = CHAIN_FILTERS.get(self.chain_filter.currentText()) if hasattr(self, "chain_filter") else None
        strategy_type = STRATEGY_FILTERS.get(self.strategy_filter.currentText()) if hasattr(self, "strategy_filter") else None
        min_roi = self.min_roi_filter.value() if hasattr(self, "min_roi_filter") else 0
        min_confidence = self.min_confidence_filter.value() if hasattr(self, "min_confidence_filter") else 0
        min_profit = self.min_profit_filter.value() if hasattr(self, "min_profit_filter") else 0
        min_profit_hour = self.min_profit_hour_filter.value() if hasattr(self, "min_profit_hour_filter") else 0
        max_age = self.max_age_filter.value() if hasattr(self, "max_age_filter") else 0
        min_volume = self.min_volume_filter.value() if hasattr(self, "min_volume_filter") else 0
        for opportunity in self.opportunities:
            if base != "Любая база" and not opportunity.path_label.startswith(base):
                continue
            if chain_type is not None and opportunity.chain_type != chain_type:
                continue
            if strategy_type is not None and strategy_type not in opportunity.strategy_types:
                continue
            if opportunity.roi_percent < min_roi:
                continue
            if opportunity.net_profit < min_profit:
                continue
            if opportunity.profit_per_hour < min_profit_hour:
                continue
            if max_age and opportunity.age_seconds > max_age:
                continue
            if opportunity.volume_score < min_volume:
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
                "",
                self._path_label(opportunity),
                f"{opportunity.input_amount:.2f} {self._alias(opportunity.input_currency)}",
                f"{opportunity.output_amount:.2f} {self._alias(opportunity.input_currency)}",
                f"{opportunity.net_profit:.2f}",
                f"{opportunity.roi_percent:.2f}%",
                f"{opportunity.profit_per_hour:.2f}",
                RISK_LABELS.get(opportunity.risk, opportunity.risk),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, self._opportunity_tooltip(opportunity))
                if column == 0:
                    item.setIcon(self._route_icon(opportunity))
                if column in {4, 5} and opportunity.net_profit > 0:
                    item.setForeground(QColor("#4bd16f"))
                if column == 7 and opportunity.risk == "high":
                    item.setForeground(QColor("#ff6b6b"))
                self.table.setItem(row, column, item)
            base_height = 32 if self.compact_mode else 48
            self.table.setRowHeight(row, max(30, int(base_height * self._ui_scale())))
        if opportunities:
            self.table.selectRow(0)
        else:
            self.update_explain_view()

    def apply_quick_preset(self) -> None:
        preset = self.quick_preset.currentText()
        strategy = next((item for item in STRATEGY_PRESETS.values() if item.label == preset), None)
        if strategy:
            self.min_roi_filter.setValue(strategy.min_roi_percent)
            self.min_confidence_filter.setValue(strategy.min_confidence)
            self.min_volume_filter.setValue(strategy.min_volume_score)
            self.sort_filter.setCurrentText("Профит/ч" if strategy.prefer_profit_per_hour else "Доходность")
            self.status_label.setText(strategy.description)
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
        self.resize(780, 240) if self.compact_mode else self.resize(1120, 420)
        self._apply_compact_layout()
        self.apply_filters()
        self.status_label.setText("Компактный режим включен." if self.compact_mode else "Полный режим включен.")

    def toggle_filters(self) -> None:
        self.filters_expanded = not self.filters_expanded
        self.filter_bar.setVisible(self.filters_expanded and not self.compact_mode)
        self.status_label.setText("Фильтры показаны." if self.filters_expanded else "Фильтры скрыты.")

    def _apply_compact_layout(self) -> None:
        compact_hidden_columns = {2, 3, 6}
        for column in range(self.table.columnCount()):
            self.table.setColumnHidden(column, self.compact_mode and column in compact_hidden_columns)
        self.table.horizontalHeader().setVisible(not self.compact_mode)
        self.tabs.tabBar().setVisible(not self.compact_mode)
        self.filter_bar.setVisible(self.filters_expanded and not self.compact_mode)
        if self.compact_mode:
            self.tabs.setCurrentWidget(self.opportunities_tab)

    def toggle_always_on_top(self) -> None:
        self.set_always_on_top(not self.settings.always_on_top)

    def set_always_on_top(self, enabled: bool) -> None:
        self.settings.always_on_top = bool(enabled)
        save_settings(self.settings)
        flags = self.windowFlags()
        if self.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def toggle_click_through(self) -> None:
        self.set_click_through(not self.settings.click_through)

    def set_click_through(self, enabled: bool) -> None:
        self.settings.click_through = bool(enabled)
        if hasattr(self, "click_through"):
            self._sync_checked(self.click_through, enabled)
        if hasattr(self, "click_through_action"):
            self._sync_checked(self.click_through_action, enabled)
        self._apply_click_through()
        save_settings(self.settings)
        self.status_label.setText(
            "Клики сквозь включены. Выключить можно через значок в трее."
            if enabled
            else "Клики сквозь выключены."
        )

    def _apply_click_through(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.settings.click_through)

    @staticmethod
    def _sync_checked(widget, enabled: bool) -> None:
        previous = widget.blockSignals(True)
        widget.setChecked(enabled)
        widget.blockSignals(previous)

    def update_opacity(self, value: int) -> None:
        self.settings.opacity = value
        self.setWindowOpacity(value / 100)
        save_settings(self.settings)

    def _ui_scale(self) -> float:
        return max(0.85, min(self.settings.ui_scale_percent / 100, 1.25))

    def _apply_ui_scale(self) -> None:
        scale = self._ui_scale()
        font = self.font()
        font.setPointSizeF(10 * scale)
        self.setFont(font)

        table_font = self.table.font()
        table_font.setPointSizeF(9.5 * scale)
        self.table.setFont(table_font)

        header_font = self.table.horizontalHeader().font()
        header_font.setPointSizeF(9 * scale)
        self.table.horizontalHeader().setFont(header_font)

        self.table.setIconSize(QSize(max(180, int(220 * scale)), max(34, int(40 * scale))))

    def hide_to_tray(self) -> None:
        self.hide()
        if self.tray.isVisible():
            self.tray.showMessage("POE2 P2P", "Overlay скрыт. Вернуть можно через значок в трее.")

    def toggle_overlay_visibility(self) -> None:
        if self.isVisible():
            self.hide_to_tray()
        else:
            self.showNormal()
            self.status_label.setText("Окно показано через бинд.")

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.status_label.setText("Пауза включена." if self.paused else "Пауза выключена.")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        dialog.setStyleSheet(self.styleSheet())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_settings(self.settings)
            self.setWindowOpacity(self.settings.opacity / 100)
            self.set_always_on_top(self.settings.always_on_top)
            self.set_click_through(self.settings.click_through)
            self._apply_ui_scale()
            self.apply_filters()
            self.status_label.setText("Настройки сохранены.")
            self._refresh_hotkeys_label()
            self.hotkey_manager.restart(self.settings.hotkeys)

    def open_calibration(self) -> None:
        dialog = CalibrationDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Калибровка сохранена в calibration.json.")

    def check_updates(self) -> None:
        status = check_for_updates()
        self.status_label.setText(status.message)
        if status.download_url:
            self._delayed_tip(self.status_label, f"Ссылка на релиз: {status.download_url}")

    def open_first_run_wizard(self) -> None:
        dialog = FirstRunDialog(self.settings, self)
        dialog.setStyleSheet(self.styleSheet())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Первичная настройка сохранена.")

    def open_logs(self) -> None:
        LOG_DIR.mkdir(exist_ok=True)
        if not LOG_FILE.exists():
            LOG_FILE.write_text("Лог пока пуст.\n", encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR.resolve())))
        self.status_label.setText(f"Папка логов: {LOG_DIR.resolve()}")

    def run_diagnostics(self) -> None:
        report = run_diagnostics(live_capture=True)
        self.ocr_debug_view.setPlainText(report.text)
        self.tabs.setCurrentWidget(self.ocr_debug_view)
        self.status_label.setText(f"Диагностика завершена. Отчет: {report.report_path}")

    def scan_pair(self) -> None:
        self.clear_error()
        self.status_label.setText("Скан пары: снимаю область Market Ratio.")
        QApplication.processEvents()

        profile = self._load_scan_profile()
        region = profile.regions[MARKET_RATIO]
        temp_path = None
        try:
            with NamedTemporaryFile(prefix="poe2_p2p_ratio_", suffix=".png", delete=False) as file:
                temp_path = Path(file.name)
            capture_screen_region(region, temp_path)
            result = read_ratio_from_image(temp_path)
        except (CaptureDependencyError, OCRDependencyError, ValueError) as error:
            self.show_error(f"Скан пары не выполнен: {error}")
            self.status_label.setText("Скан пары завершился ошибкой. Проверь калибровку и Tesseract.")
            return
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

        left, right = result.ratio
        left_name = self._scan_region_text(profile, LEFT_ITEM)
        right_name = self._scan_region_text(profile, RIGHT_ITEM)
        recalculated = False
        if left_name and right_name:
            new_edges = self._edges_from_scanned_ratio(left_name, right_name, result.ratio, result.confidence)
            self.live_rates.extend(new_edges)
            if self.chain_scan_active:
                self.chain_scan_steps.append(f"{left_name} -> {right_name}: {left:g} : {right:g}")
            recalculated = self._recalculate_opportunities()
        text = (
            "Последний скан Market Ratio\n\n"
            f"Область: x={region.x}, y={region.y}, width={region.width}, height={region.height}\n"
            f"OCR текст: {result.raw_text or 'пусто'}\n"
            f"Распознанный курс: {left:g} : {right:g}\n"
            f"Левая сторона: {left_name or 'не распознано'}\n"
            f"Правая сторона: {right_name or 'не распознано'}\n"
            f"Уверенность: {result.confidence:.2f}\n\n"
            + (
                "Курс добавлен в граф, таблица пересчитана."
                if recalculated
                else "Курс прочитан, но для пересчета нужны распознанные названия обеих сторон и прибыльный цикл."
            )
        )
        self.live_scan_view.setPlainText(text)
        self.ocr_debug_view.setPlainText(text)
        self.status_label.setText(
            f"Скан пары выполнен: {left:g} : {right:g}. "
            + (
                f"Шаг цепочки сохранен: {len(self.chain_scan_steps)}."
                if self.chain_scan_active and left_name and right_name
                else ("Таблица пересчитана." if recalculated else "Ожидаю полный цикл для расчета.")
            )
        )

    def scan_chain(self) -> None:
        if not self.chain_scan_active:
            self.chain_scan_active = True
            self.chain_scan_steps = []
            text = (
                "Пошаговый скан цепочки начат.\n\n"
                "1. Открой первую пару в NPC Currency Exchange.\n"
                "2. Нажми `Скан пары`.\n"
                "3. Перейди к следующей паре и повтори.\n"
                "4. Нажми `Скан цепочки` еще раз, чтобы завершить и пересчитать таблицу."
            )
            self.live_scan_view.setPlainText(text)
            self.tabs.setCurrentWidget(self.live_scan_view)
            self.status_label.setText("Скан цепочки начат. Нажимай `Скан пары` для каждого шага.")
            return

        self.chain_scan_active = False
        recalculated = self._recalculate_opportunities()
        lines = [
            "Пошаговый скан цепочки завершен.",
            "",
            f"Сохранено шагов: {len(self.chain_scan_steps)}",
            "",
            *self.chain_scan_steps,
        ]
        self.live_scan_view.setPlainText("\n".join(lines))
        self.status_label.setText(
            "Скан цепочки завершен, таблица пересчитана."
            if recalculated
            else "Скан цепочки завершен, прибыльный цикл пока не найден."
        )

    def refresh_candidates(self) -> None:
        self.clear_error()
        self.status_label.setText("Обновляю кандидатов через poe.ninja.")
        QApplication.processEvents()
        try:
            candidates = fetch_currency_candidates(league=self.settings.league, limit=25)
        except Exception as error:
            self.show_error(f"Не удалось обновить кандидатов: {error}")
            self.status_label.setText("Кандидаты не обновлены. Проверь сеть, league и доступность poe.ninja.")
            return

        if not candidates:
            self.candidates_view.setPlainText("poe.ninja не вернул подходящих кандидатов.")
            self.status_label.setText("Кандидаты не найдены.")
            return

        self.candidate_trends = {
            candidate.name: candidate.seven_day_change_percent
            for candidate in candidates
        }
        try:
            cached_icons = self.icon_cache.cache_candidates(candidates)
        except RuntimeError:
            cached_icons = 0
        except Exception:
            cached_icons = 0
        lines = [
            "Кандидаты для проверки в NPC Currency Exchange",
            "",
            "Сначала проверяй верхние строки: у них выше сочетание объема, цены в Chaos и тренда.",
            "",
        ]
        for index, candidate in enumerate(candidates, start=1):
            lines.append(
                f"{index}. {candidate.name} | Chaos {candidate.value_in_chaos:.2f} | "
                f"объем/ч {candidate.volume_per_hour:.0f} | 7д {candidate.seven_day_change_percent:.1f}% | "
                f"оценка {candidate.volume_score:.0f}"
            )
        self.candidates_view.setPlainText("\n".join(lines))
        self.tabs.setCurrentWidget(self.candidates_view)
        self.status_label.setText(f"Кандидаты обновлены: {len(candidates)} позиций, новых иконок: {cached_icons}.")

    def export_opportunities(self) -> None:
        rows = self.filtered_opportunities or self.opportunities
        if not rows:
            self.show_error("Нет связок для экспорта.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить связки",
            "poe2-p2p-opportunities.csv",
            "CSV (*.csv)",
        )
        if not path:
            self.status_label.setText("Экспорт отменен.")
            return
        try:
            export_opportunities_csv(rows, path)
        except OSError as error:
            self.show_error(f"Не удалось сохранить CSV: {error}")
            return
        self.status_label.setText(f"Экспортировано связок: {len(rows)} -> {path}")

    @staticmethod
    def _load_scan_region() -> CropRegion:
        calibration_path = Path("calibration.json")
        if calibration_path.exists():
            return load_region(calibration_path)
        return DEFAULT_MARKET_RATIO_REGION

    @staticmethod
    def _load_scan_profile():
        calibration_path = Path("calibration.json")
        if calibration_path.exists():
            return load_calibration_profile(calibration_path)
        return default_calibration_profile()

    def _scan_region_text(self, profile, region_key: str) -> str:
        region = profile.regions.get(region_key)
        if not region:
            return ""
        temp_path = None
        try:
            with NamedTemporaryFile(prefix="poe2_p2p_text_", suffix=".png", delete=False) as file:
                temp_path = Path(file.name)
            capture_screen_region(region, temp_path)
            result = read_text_from_image(temp_path)
        except (CaptureDependencyError, OCRDependencyError, ValueError):
            return ""
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
        return self._normalize_currency_name(result.raw_text)

    def _edges_from_scanned_ratio(
        self,
        left_name: str,
        right_name: str,
        ratio: tuple[float, float],
        confidence: float,
    ) -> list[RateEdge]:
        left, right = ratio
        if left <= 0 or right <= 0:
            return []
        forward = right / left
        return [
            RateEdge(left_name, right_name, forward, "OCR из игры", confidence=confidence),
            RateEdge(right_name, left_name, 1 / forward, "OCR из игры:обратный курс", confidence=confidence),
        ]

    def _recalculate_opportunities(self) -> bool:
        if not self.live_rates:
            return False
        starts = ("Exalted Orb", "Divine Orb", "Chaos Orb")
        input_amounts = {"Exalted Orb": 2050.0, "Divine Orb": 10.0, "Chaos Orb": 1000.0}
        calculator = ArbitrageCalculator(self.live_rates, trend_by_currency=self.candidate_trends)
        opportunities = []
        for start in starts:
            opportunities.extend(
                calculator.find_cycles(start, input_amounts[start], max_hops=5)
            )
        profitable = [item for item in opportunities if item.net_profit > 0]
        if not profitable:
            return False
        self.opportunities = profitable
        self.apply_filters()
        return True

    @staticmethod
    def _rates_from_opportunities(opportunities: list[Opportunity]) -> list[RateEdge]:
        rates = []
        for opportunity in opportunities:
            for step in opportunity.steps:
                rates.append(
                    RateEdge(
                        step.from_currency,
                        step.to_currency,
                        step.rate,
                        step.source,
                        confidence=step.confidence,
                        observed_stock=step.observed_stock,
                    )
                )
        return rates

    @staticmethod
    def _normalize_currency_name(value: str) -> str:
        cleaned = " ".join(value.replace("\n", " ").split()).strip(" :")
        lowered = cleaned.lower()
        aliases = {
            "exalted": "Exalted Orb",
            "exalted orb": "Exalted Orb",
            "divine": "Divine Orb",
            "divine orb": "Divine Orb",
            "chaos": "Chaos Orb",
            "chaos orb": "Chaos Orb",
        }
        return aliases.get(lowered, cleaned)

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.hide()

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal() if self.isHidden() else self.hide()

    def _refresh_hotkeys_label(self) -> None:
        parts = [f"{ACTION_LABELS[action]}: {value}" for action, value in self.settings.hotkeys.items()]
        self.hotkeys_label.setText("Бинды: " + " | ".join(parts))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.hotkey_manager.stop()
        if hasattr(self, "tray"):
            self.tray.hide()
        super().closeEvent(event)

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

    def _route_icon(self, opportunity: Opportunity) -> QIcon:
        scale = self._ui_scale()
        size = max(30, int(36 * scale))
        gap = max(5, int(7 * scale))
        width = min(len(opportunity.path) * (size + gap), 240)
        height = max(36, int(42 * scale))
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = 0
        for index, part in enumerate(opportunity.path):
            if x + size > width:
                break
            node = self._icon_for_currency(part).pixmap(size, size)
            painter.drawPixmap(x, max(0, (height - size) // 2), node)
            x += size
            if index < len(opportunity.path) - 1 and x + gap <= width:
                painter.setPen(QColor("#8b96a3"))
                painter.drawLine(x, height // 2, x + gap - 1, height // 2)
                x += gap
        painter.end()
        return QIcon(pixmap)

    def _icon_for_currency(self, name: str) -> QIcon:
        cached = self.icon_cache.cached_icon_path(name)
        if cached:
            return QIcon(str(cached))
        if name not in self.missing_icon_downloads:
            try:
                self.icon_cache.cache_static_icons([name])
            except RuntimeError:
                self.missing_icon_downloads.add(name)
            except Exception:
                self.missing_icon_downloads.add(name)
            else:
                cached = self.icon_cache.cached_icon_path(name)
                if cached:
                    return QIcon(str(cached))
                self.missing_icon_downloads.add(name)
        color, text = ICON_COLORS.get(name, ("#6f7b88", "IT"))
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 36, 36)
        painter.setPen(QColor("#101316"))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _alias(name: str) -> str:
        return ALIASES.get(name, name)

    def _opportunity_tooltip(self, opportunity: Opportunity) -> str:
        risk_reasons = "; ".join(opportunity.risk_reasons) if opportunity.risk_reasons else "нет данных"
        strategy_descriptions = "; ".join(
            STRATEGY_TYPE_DESCRIPTIONS.get(strategy, strategy.value)
            for strategy in opportunity.strategy_types
        )
        return (
            f"Связка: {self._path_label(opportunity)}\n"
            f"Тип: {CHAIN_TYPE_LABELS.get(opportunity.chain_type, 'неизвестно')}\n"
            f"Стратегия: {opportunity.strategy_label}\n"
            f"Вход: {opportunity.input_amount:.2f} {self._alias(opportunity.input_currency)}\n"
            f"Выход: {opportunity.output_amount:.2f} {self._alias(opportunity.input_currency)}\n"
            f"Чистый профит: {opportunity.net_profit:.2f}\n"
            f"Доходность: {opportunity.roi_percent:.2f}%\n"
            f"Уверенность данных: {opportunity.confidence:.2f}\n"
            f"Возраст данных: {self._age_label(opportunity.age_seconds)}\n"
            f"Оценка объема: {opportunity.volume_score:.0f}\n"
            f"Тренд: {opportunity.trend_percent:.1f}%\n"
            f"Максимальный размер: {'нет данных' if opportunity.max_size is None else f'{opportunity.max_size:.0f}'}\n"
            f"Шагов исполнения: {opportunity.execution_steps}\n"
            f"Время исполнения: {opportunity.execution_time_seconds:.1f} сек\n"
            f"Смысл стратегии: {strategy_descriptions}\n"
            f"Причины риска: {risk_reasons}\n"
            f"Источник курсов: {opportunity.source}\n\n"
            "Доходность показывает прибыль одного полного цикла в процентах. "
            "Профит/ч зависит от скорости исполнения и будет точнее после сканирования игры."
        )

    @staticmethod
    def _age_label(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f} сек"
        return f"{seconds / 60:.1f} мин"

    def update_explain_view(self) -> None:
        if not hasattr(self, "explain_view"):
            return
        selected = self.table.selectedItems()
        if not selected:
            self.explain_view.setPlainText("Выбери связку в таблице, чтобы увидеть расчет по шагам.")
            return
        row = selected[0].row()
        if row >= len(self.filtered_opportunities):
            return
        opportunity = self.filtered_opportunities[row]
        self.explain_view.setPlainText(self._explain_text(opportunity))

    def _explain_text(self, opportunity: Opportunity) -> str:
        lines = [
            f"Связка: {self._path_label(opportunity)}",
            f"Тип: {CHAIN_TYPE_LABELS.get(opportunity.chain_type, 'неизвестно')}",
            f"Стратегия: {opportunity.strategy_label}",
            "",
            "Шаги:",
        ]
        for index, step in enumerate(opportunity.steps, start=1):
            lines.append(
                f"{index}. {self._alias(step.from_currency)} -> {self._alias(step.to_currency)} | "
                f"вход {step.input_amount:.4f}, выход {step.output_amount:.4f}, курс {step.rate:.8f}"
            )
            lines.append(
                f"   источник: {step.source}; уверенность: {step.confidence:.2f}; "
                f"возраст: {self._age_label(step.age_seconds)}; "
                f"объем: {'нет данных' if step.observed_stock is None else f'{step.observed_stock:.0f}'}"
            )
            losses = step.rounding_loss + step.gold_cost + step.stale_penalty + step.confidence_penalty
            if losses > 0:
                lines.append(
                    f"   потери шага: округление {step.rounding_loss:.4f}; "
                    f"золото {step.gold_cost:.4f}; устаревание {step.stale_penalty:.4f}; "
                    f"низкая уверенность {step.confidence_penalty:.4f}"
                )
        lines.extend(
            [
                "",
                "Итог:",
                f"Вход: {opportunity.input_amount:.4f} {self._alias(opportunity.input_currency)}",
                f"Выход: {opportunity.output_amount:.4f} {self._alias(opportunity.input_currency)}",
                f"Валовый профит: {opportunity.gross_profit:.4f}",
                f"Чистый профит: {opportunity.net_profit:.4f}",
                f"Доходность: {opportunity.roi_percent:.2f}%",
                f"Профит/ч: {opportunity.profit_per_hour:.4f}",
                f"Тренд: {opportunity.trend_percent:.1f}%",
                f"Время исполнения: {opportunity.execution_time_seconds:.1f} сек",
                "",
                "Экономический смысл:",
            ]
        )
        for strategy in opportunity.strategy_types:
            description = STRATEGY_TYPE_DESCRIPTIONS.get(strategy, strategy.value)
            label = STRATEGY_TYPE_LABELS.get(strategy, strategy.value)
            lines.append(f"- {label}: {description}")
        lines.extend(
            [
                "",
                "Причины риска:",
            ]
        )
        for reason in opportunity.risk_reasons or ("нет данных",):
            lines.append(f"- {reason}")
        return "\n".join(lines)

    @staticmethod
    def _build_icon() -> QIcon:
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "app_icon.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
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
from .. import __version__
