# Рекомендации по стеку, функционалу и экономике

## Главный продуктовый фокус

Приложение должно отвечать на один вопрос: какую связку сейчас выгоднее выполнить с учетом исполнимости, объема и риска ошибки?

Поэтому приоритеты такие:

1. Экономическая корректность.
2. Надежность live ratio.
3. Быстрый scan ограниченного списка кандидатов.
4. Удобный overlay.
5. Расширенная автоматизация.

## Рекомендуемый стек

### MVP

Лучший стартовый вариант:

```text
Python 3.11+
PySide6
mss
Pillow
opencv-python
pytesseract или easyocr
SQLite
requests/httpx
```

Почему:

- минимальное время до рабочего прототипа;
- OCR/OpenCV в Python развивать проще;
- SQLite достаточно для истории rates/opportunities;
- PySide6 дает нормальное desktop-окно, always-on-top и таблицы;
- экономическую модель легко тестировать отдельно от UI.

### Production после проверки MVP

Если приложение подтверждает ценность:

- C#/.NET WPF или WinUI - лучший вариант для Windows-only overlay;
- Tauri/Rust - хороший вариант для легкого cross-platform UI;
- Python оставить как research/prototyping слой для OCR и экономики.

Electron не рекомендуется как основной вариант, если важна легковесность.

Overwolf SDK стоит рассматривать только если нужна публикация внутри их ecosystem. Для приватного инструмента он избыточен.

## Сборка в exe

Финальная цель для пользователя - запуск приложения обычным `.exe` без ручного запуска Python-команд.

### MVP packaging

Для текущего Python-прототипа самый быстрый путь:

```text
PyInstaller
```

Ожидаемый результат:

```text
dist/POE2-P2P/POE2-P2P.exe
```

Плюсы:

- быстро подключается;
- нормально собирает PySide6 desktop-приложения;
- подходит для раннего тестирования overlay, OCR и экономической модели.

Минусы:

- exe/папка будут крупнее нативного приложения;
- антивирусы иногда подозрительно относятся к PyInstaller bundles;
- нужно отдельно проверить упаковку `tesseract`, если OCR будет завязан на системный binary.

### Production packaging

Если MVP подтвердит экономическую пользу, более чистые варианты:

- C#/.NET WPF/WinUI + single-file publish для Windows-only приложения;
- Tauri/Rust + MSI/NSIS installer для легкого desktop-дистрибутива;
- Python core оставить как reference/prototype или вынести только OCR/исследования.

### Рекомендуемая стратегия

1. Сначала довести Python MVP до полезного состояния.
2. Добавить `pyinstaller.spec`. `[x]`
3. Собрать portable `.exe`. `[ ]` Требует Windows-среды сборки.
4. Проверить запуск на чистой Windows-машине. `[ ]` Требует Windows runtime.
5. После стабилизации OCR/экономики решить, оставаться на Python или переносить shell в C#/Tauri.

## Функциональные приоритеты

### P0

- [x] Ручной/полуавтоматический scan текущей пары через CLI capture/crop scaffold.
- [x] Парсинг текстового `Market Ratio`.
- [ ] OCR `Market Ratio` из изображения/crop. Код есть, runtime требует установленный Tesseract OCR.
- [x] Ручная calibration область окна NPC Currency Exchange через JSON save/load.
- [x] Directed graph rates.
- [x] Direct arbitrage: `Exalted -> Item -> Divine -> Exalted`.
- [x] SQLite history.
- [x] CLI fallback.
- [x] Overlay table code.
- [x] Overlay runtime verification с установленным PySide6 в Linux/offscreen режиме.
- [ ] Overlay runtime verification на Windows.
- [x] PyInstaller spec и PowerShell build script.
- [x] PyInstaller spec smoke-test на Linux.
- [ ] Portable `.exe` build для тестирования без IDE.

### P1

- [x] OCR confidence scaffold и sanity-check ratio по expected range.
- [x] Hotkeys scaffold в overlay: `Esc` close, `Ctrl+R` refresh.
- [x] Shortlist кандидатов на основе volume/trend/spread.
- [x] Triangular arbitrage.
- [x] Rounding/slippage/gold-cost model.
- [x] Export CSV.

### P2

- [x] Multi-hop graph search глубиной 4-5.
- [x] Alert system.
- [x] Historical profit tracking через SQLite history CLI.
- [x] Сравнение profit/hour по стратегиям.
- [x] Presets под разные лиги/режимы расчета.

## Экономическая выгодность

### Что считать выгодной связкой

Связка выгодна только если выполняется условие:

```text
expected_net_profit > минимальный profit threshold
expected_profit_per_hour > альтернативный способ фарма/трейда
max_executable_size >= минимальный размер сделки
data_confidence >= порог надежности
```

Красивый ROI сам по себе недостаточен. Нужны:

- volume;
- stock;
- скорость исполнения;
- малый spread;
- актуальность ratio;
- повторяемость сделки.

### Формула score

```text
gross_profit = output_value_base - input_value_base
net_profit = gross_profit - spread_loss - rounding_loss - gold_cost - slippage_buffer

roi_percent = net_profit / input_value_base * 100
profit_per_hour = net_profit_per_cycle * cycles_per_hour

score =
  profit_per_hour
  * liquidity_factor
  * confidence_factor
  * freshness_factor
  * execution_factor
```

### Фильтры

Отбрасывать opportunity, если:

- ROI меньше 1-2% после поправок;
- OCR confidence ниже 0.95 для чисел;
- live scan старше 60-120 секунд;
- связка требует больше 3-5 действий и profit маленький;
- max executable size слишком низкий;
- spread/rounding съедает больше 30-40% gross profit.

### Самые перспективные связки

В первую очередь проверять:

- `Exalted -> high-volume item -> Divine -> Exalted`
- `Divine -> high-volume item -> Exalted -> Divine`
- `Exalted -> Chaos -> Divine -> Exalted`
- `Exalted -> Omen/Rune/Essence -> Divine -> Exalted`
- пары с резким 7-day trend и большим volume.

Низколиквидные предметы использовать осторожно: они часто дают высокий ROI на бумаге и плохой profit/hour в реальности.

## OCR и данные

### Надежный порядок разработки

1. Сначала парсинг ratio из сохраненных скриншотов.
2. Затем crop по фиксированным координатам.
3. Затем calibration UI.
4. Затем live screen capture.
5. Только после этого навигация по списку валют.

### Проверка OCR

Каждый прочитанный ratio должен проходить проверки:

- число не нулевое;
- decimal separator нормализован;
- ratio попадает в ожидаемый диапазон из poe.ninja/API;
- направление пары совпадает с item labels;
- повторное чтение дает тот же результат или близкое значение.

## UI рекомендации

Overlay должен быть компактным:

- always-on-top;
- прозрачность 85-95%;
- таблица без лишних карточек;
- горячие клавиши;
- цвет profit/risk;
- ручное подтверждение сомнительных OCR значений.

Минимальная таблица:

```text
Path | Input | Output | Net Profit | ROI % | Max Size | Confidence | Age
```

## Roadmap

### Milestone 1

- [x] Рабочий расчет по данным со скриншотов.
- [x] CLI вывод.
- [x] Overlay UI code.
- [x] Overlay runtime verification в Linux/offscreen режиме.
- [ ] Overlay runtime verification на Windows.

### Milestone 2

- [x] Screen capture/crop scaffold.
- [x] Screen capture/crop region runtime verification на сохраненном screenshot.
- [ ] OCR ratio на сохраненных screenshots. Требует системный `tesseract`.
- [ ] OCR ratio на live screenshots.

### Milestone 3

- [x] Shortlist candidates через poe.ninja/API client, runtime verified на current overview endpoint.
- [ ] Live NPC validation.

### Milestone 4

- [x] Graph search по расширенным циклам.
- [x] Profit/hour ranking.
- [x] History dashboard через HTML export.
