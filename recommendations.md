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
3. Собрать portable `.exe`. `[x]` Базовый PyInstaller `.exe` был собран и запущен на Windows.
4. Проверить запуск на чистой Windows-машине. `[ ]` Требует отдельной проверки установленного GitHub Release installer на основном ПК.
5. После стабилизации OCR/экономики решить, оставаться на Python или переносить shell в C#/Tauri.

## Функциональные приоритеты

### P0

- [x] Ручной/полуавтоматический scan текущей пары через CLI capture/crop scaffold.
- [x] Парсинг текстового `Market Ratio`.
- [x] OCR `Market Ratio` из изображения/crop. Проверено на сохраненных screenshots после установки Tesseract.
- [x] Ручная calibration область окна NPC Currency Exchange через JSON save/load.
- [x] Directed graph rates.
- [x] Direct arbitrage: `Exalted -> Item -> Divine -> Exalted`.
- [x] SQLite history.
- [x] CLI fallback.
- [x] Overlay table code.
- [x] Overlay runtime verification с установленным PySide6 в Linux/offscreen режиме.
- [x] Overlay runtime verification на Windows: базовый запуск `.exe` и окно подтверждены.
- [x] PyInstaller spec и PowerShell build script.
- [x] PyInstaller spec smoke-test на Linux.
- [x] Portable `.exe` build для тестирования без IDE.

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

## UX/UI backlog

Текущий overlay - технический прототип. Он подтверждает расчет и запуск, но не соответствует целевому UX в стиле POE Overlay 2. Его нужно развивать как отдельное приложение, а не просто таблицу.

### P0: базовая управляемость окна

- [x] Кнопка закрытия `X` в правом верхнем углу.
- [x] Кнопка свернуть/скрыть overlay.
- [x] Drag-to-move за верхнюю панель.
- [x] Resize grip или фиксированные compact/full размеры.
- [x] Видимый статус hotkeys в settings, но без перегруза основного окна.
- [x] Tray icon: show/hide, exit, settings.
- [x] Нормальное завершение приложения без Task Manager.
- [x] Настройка прозрачности overlay.
- [x] Переключатель `always on top`.

### P0: первый usable layout

- [x] Верхняя панель: app title, league/source status, last scan age, close/minimize/settings.
- [x] Action bar: `Scan Pair`, `Scan Chain`, `Refresh Candidates`, `Export`.
- [x] Таблица opportunities с колонками: icon path, path, input, output, net profit, ROI, profit/hour, confidence, age, risk.
- [x] Compact row mode для игры: меньше высота строк, скрываемые колонки.
- [x] Empty state: нет возможностей / нет live scan / OCR не настроен.
- [x] Error state: OCR failed, Tesseract missing, invalid crop, stale data.
- [x] Tooltip по каждой opportunity: источники курсов, формула profit, потери spread/rounding/gold/slippage.

### P1: игровые иконки и визуальная читаемость

- [x] Currency/item icons в строках таблицы, пока сгенерированные бейджи.
- [x] Локальный кеш иконок из poe.ninja/API.
- [x] Fallback icon для неизвестных items.
- [x] Цветовая кодировка: profit, risk, stale, low confidence.
- [x] Нормальное отображение длинных цепочек: `EX -> Omen -> DIV -> EX` + tooltip с full names.
- [x] User-friendly aliases: `Exalted`, `Divine`, `Chaos`, `Omen`.
- [x] Поддержка темной темы без монотонной серо-черной таблицы.
- [x] Не обрезать важные числа: profit/ROI должны быть видны без расширения окна.

### P1: фильтры и сортировка

- [x] Фильтр по base currency: Exalted, Divine, Chaos.
- [x] Фильтр по chain type: direct, reverse, triangular, cross-currency, multi-hop.
- [x] Фильтр по economic strategy: spread, hub, basket, liquidity, high ROI, currency triangle.
- [x] Фильтр `min ROI`.
- [x] Фильтр `min net profit`.
- [x] Фильтр `min profit/hour`.
- [x] Фильтр `min confidence`.
- [x] Фильтр `max age`.
- [x] Фильтр `min volume/liquidity`.
- [x] Сортировка по profit, ROI, profit/hour, confidence.
- [x] Quick presets: safe / balanced / aggressive.

### P1: hotkeys/binds

- [x] Global hotkey `Scan Pair`.
- [x] Global hotkey `Toggle Overlay`.
- [x] Global hotkey `Scan Candidate List`.
- [x] Global hotkey `Pause/Resume`.
- [x] Settings UI для изменения биндов.
- [x] Проверка конфликтов hotkeys.
- [x] Сохранение hotkeys в config.
- [x] Visual feedback после hotkey: scan started, scan success, scan failed.

### P1: UX gap после первого `.exe` скриншота

- [x] Настоящие иконки валют в каждом узле маршрута из локального кеша, fallback для неизвестных items.
- [x] Компактная строка маршрута с иконками `Exalted -> Omen -> Divine -> Exalted` и раскрытием полного названия по tooltip.
- [x] Иконки на основных кнопках: scan, candidates, export, settings, minimize, close.
- [x] Подключить кнопку `Экспорт` к реальному CSV save dialog, а не placeholder.
- [x] Подключить кнопку `Кандидаты` к live poe.ninja/API списку внутри UI.
- [x] Подключить `Скан пары` к live capture -> OCR внутри UI.
- [ ] Подключить `Скан пары` к capture -> OCR -> расчету без CLI.
- [ ] Подключить `Скан цепочки` к guided flow по нескольким NPC парам.
- [x] Сделать game-friendly compact mode: меньше текста, больше чисел/иконок, без горизонтальной перегрузки.
- [x] Добавить clear empty/loading/success states для основных кнопок действия.
- [x] Добавить закрепление окна и режим пропуска кликов, если Windows-окно поверх POE2 позволит это безопасно.
- [ ] Добавить настройку размера шрифта и масштаба таблицы под 1080p/1440p/4K.

### P1: calibration UX

- [ ] Calibration mode с выделением области `Market Ratio`.
- [x] Preview crop перед сохранением.
- [x] OCR preview: raw text, parsed ratio, confidence.
- [x] Кнопки `Retry`, `Accept`, `Adjust`.
- [ ] Отдельные регионы для item names, ratio, amount fields, red current value.
- [ ] Профили resolution/UI scale.

### P2: рабочие views

- [x] `Opportunities` view.
- [x] `Live Scan` view.
- [x] `Candidates` view.
- [x] `History` view внутри приложения вместо только HTML export.
- [x] `Settings` view.
- [x] `Debug OCR` view для crop/preprocessing/recognized text.
- [x] `Economy Graph` view для диагностики цепочек.

### P2: installer/user polish

- [x] GitHub Release installer artifact.
- [x] App icon для `.exe`, installer и ярлыков.
- [x] Version display внутри приложения.
- [x] Auto-update check через GitHub Releases.
- [x] First-run wizard: Tesseract status, calibration, hotkeys, league.
- [x] Crash/error log file и кнопка открыть logs.

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

## Экономические связки и стратегии

Текущий `ArbitrageCalculator` технически умеет искать циклы в directed graph глубиной до N ребер. Это покрывает прямые, треугольные и multi-hop цепочки как общий механизм, но не хватает стратегических presets, explainability, liquidity-aware scoring и UI-фильтров по типам цепочек.

### Из исходной спецификации

- [x] Chain 1: `Exalted -> Item -> Divine -> Exalted` через graph cycle.
- [x] Chain 2: `Divine -> Item -> Exalted -> Divine` через graph cycle/preset.
- [x] Chain 3: triangular arbitrage `Exalted -> Item A -> Divine -> Item B -> Exalted` как multi-edge cycle.
- [x] Chain 4: cross-currency via chaos `Exalted -> Chaos -> Divine -> Exalted` как graph cycle.
- [x] Chain 5: multi-hop `Exalted -> Item A -> Chaos -> Item B -> Divine -> Exalted` как graph cycle depth 5.
- [x] Явная классификация найденной цепочки по типу: direct/reverse/triangular/cross-currency/multi-hop.
- [x] Отдельный UI-фильтр по chain type.
- [x] Отдельные presets для каждого chain type.
- [x] Explain view: какая часть profit пришла из какого ребра.

### Дополнительные связки, которые стоит добавить

- [x] Spread capture: `Currency A -> Currency B -> Currency A`, если NPC bid/ask на разных направлениях дает положительный цикл.
- [x] Stable hub arbitrage: `Exalted -> Chaos -> Item -> Exalted`.
- [x] Divine hub arbitrage: `Divine -> Chaos -> Item -> Divine`.
- [x] Omen/Rune/Essence basket arbitrage: несколько похожих items против одной базовой валюты.
- [x] Trend-confirmed flip: live profit + positive 7d trend + high volume. Классификатор есть, полноценное срабатывание требует live trend data.
- [x] Mean-reversion candidate: live NPC price сильно ниже poe.ninja baseline. Классификатор есть, полноценное срабатывание требует baseline delta.
- [x] Liquidity-first route: не максимальный ROI, а максимальный `profit/hour` при большом volume.
- [x] Low-cap high-ROI route: отдельный risky режим для малых объемов.
- [x] Same-family swaps: rune -> rune, essence -> essence, omen -> omen через Divine/Exalted hub.
- [x] Currency triangle: `Exalted -> Chaos -> Divine -> Exalted`, `Divine -> Chaos -> Exalted -> Divine`.
- [x] Four-hop hub: `Exalted -> Item A -> Chaos -> Item B -> Exalted`.
- [x] Five-hop research: `Base -> Item A -> Hub 1 -> Item B -> Hub 2 -> Base`.

### Экономические проверки, которых еще не хватает

- [x] Market depth / stock limit для каждого ребра через `observed_stock` в `RateEdge`/`OpportunityStep`.
- [x] Max executable size для всей цепочки через минимальный stock по ребрам.
- [ ] Rounding loss по каждому шагу, а не только flat estimate.
- [ ] Gold cost model по шагам.
- [ ] Stale-data penalty.
- [ ] OCR confidence penalty по конкретному ребру.
- [x] Liquidity factor из observed stock/API-полей, если источник их передает.
- [ ] Trend factor из poe.ninja/API в live opportunities.
- [ ] Execution time estimate: clicks/steps per cycle.
- [ ] Profit/hour с учетом execution time, а не только `cycles_per_hour` вручную.
- [ ] Kill-switch: скрывать цепочки с отрицательным net после всех потерь.
- [ ] Minimum bankroll filter: сколько валюты нужно для meaningful cycle.
- [x] Risk labels: low/medium/high с понятной причиной.

### Следующий экономический milestone

- [x] Добавить `ChainType` enum.
- [x] Классифицировать opportunities после поиска цикла.
- [x] Добавить `StrategyPreset`: safe, balanced, aggressive, high-volume, high-roi.
- [x] Выводить `max_size`, `age`, `volume_score`, `execution_steps`.
- [x] Добавить тестовые sample chains для Chain 1-5.
- [x] Добавить unit tests на классификацию и scoring.

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
- [x] OCR ratio на сохраненных screenshots.
- [ ] OCR ratio на live screenshots.

### Milestone 3

- [x] Shortlist candidates через poe.ninja/API client, runtime verified на current overview endpoint.
- [ ] Live NPC validation.

### Milestone 4

- [x] Graph search по расширенным циклам.
- [x] Profit/hour ranking.
- [x] History dashboard через HTML export.
