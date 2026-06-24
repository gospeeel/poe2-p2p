# POE2 P2P Currency Arbitrage Overlay

## Цель

Легковесное desktop-приложение в стиле POE Overlay 2, которое помогает находить экономически выгодные связки в NPC Currency Exchange Path of Exile 2.

Первичная ценность приложения - не автоматизация кликов сама по себе, а быстрый расчет исполнимой экономической выгоды:

- снять live ratio из окна NPC Currency Exchange;
- нормализовать пары в единый граф обменов;
- найти прямой, треугольный и multi-hop арбитраж;
- отфильтровать ложные возможности по ликвидности, spread, rounding и confidence OCR;
- показать результат в компактном overlay-окне поверх игры.

## Источники данных

### 1. NPC Currency Exchange

Главный источник для исполнимой цены прямо сейчас.

Со скриншотов:

- `Screenshot_1.jpg`: `Omen of Whittling` стоит `2050 Exalted Orb`, ratio `1 : 2050`.
- `Screenshot_2.jpg`: `1 Omen of Whittling` стоит примерно `6.34 Divine Orb`, ratio `6.34 : 1`.
- `Screenshot_3.jpg`: пример ручного расчета: `6.40 Divine * 352 Exalted = 2252.8 Exalted`, покупка около `2200 Exalted`, положительный оборотный profit.

Важно: направление ratio нужно хранить явно. Ошибка в направлении сделки полностью ломает расчет.

### 2. poe.ninja

Вспомогательный источник:

- предварительный отбор кандидатов;
- нормализация цен в chaos/divine/exalted;
- тренды за 7 дней;
- объем и популярность;
- sanity-check OCR.

poe.ninja не должен считаться единственным источником исполнимой live-цены NPC.

### 3. Official Currency Exchange API

Вспомогательный исторический источник:

- hourly aggregate;
- volume;
- lowest/highest ratio;
- lowest/highest stock;
- проверка рыночного контекста.

Этот источник полезен для фильтрации и анализа, но не заменяет live NPC ratio.

## Основные сценарии

### Сценарий 1. Быстрый scan текущей пары

1. Пользователь открывает NPC Currency Exchange.
2. Нажимает hotkey `Scan Pair`.
3. Приложение читает crop окна обмена.
4. OCR/parser извлекает:
   - left item;
   - right item;
   - market ratio;
   - amount fields;
   - red current value;
   - confidence.
5. Пара сохраняется в SQLite.
6. Overlay обновляет таблицу возможностей.

### Сценарий 2. Проверка кандидатов

1. Приложение получает список экономически интересных валют из poe.ninja/API.
2. Пользователь или навигатор проходит пары в NPC exchange.
3. Приложение сканирует только ограниченный список, а не весь рынок.
4. Экономический граф пересчитывается после каждого нового ratio.

### Сценарий 3. Поиск арбитража

Поддерживаемые цепочки:

- Direct: `Exalted -> Item -> Divine -> Exalted`
- Reverse Direct: `Divine -> Item -> Exalted -> Divine`
- Cross-currency: `Exalted -> Chaos -> Divine -> Exalted`
- Triangular: `Exalted -> Item A -> Divine -> Item B -> Exalted`
- Multi-hop: цепочки глубиной 3-5 ребер с ограничением по ликвидности.

## Экономическая модель

Каждая live-пара хранится как направленное ребро:

```text
from_currency -> to_currency
rate
source
timestamp
ocr_confidence
observed_stock
```

Для `1 Omen = 2050 Exalted` создаются два ребра:

```text
Omen of Whittling -> Exalted Orb: 2050
Exalted Orb -> Omen of Whittling: 1 / 2050
```

Для `1 Omen = 6.34 Divine`:

```text
Omen of Whittling -> Divine Orb: 6.34
Divine Orb -> Omen of Whittling: 1 / 6.34
```

Пример:

```text
buy_price_exalted = 2050
sell_price_divine = 6.34
divine_to_exalted = 352

sell_value_exalted = 6.34 * 352 = 2231.68
profit_exalted = 2231.68 - 2050 = 181.68
roi = 181.68 / 2050 * 100 = 8.86%
```

Итоговый score:

```text
net_profit = gross_profit - spread_loss - rounding_loss - gold_cost - slippage_buffer
score = net_profit * liquidity_factor * confidence_factor * trend_factor
```

## Метрики для таблицы

Обязательные:

- `Path` - цепочка обменов.
- `Buy` - стоимость входа.
- `Sell` - ожидаемый выход.
- `Net Profit` - чистый profit после поправок.
- `ROI %` - доходность на один цикл.
- `Max Size` - примерный исполнимый объем.
- `Confidence` - уверенность OCR/данных.
- `Freshness` - возраст live ratio.

Дополнительные:

- `Volume Score` = `net_profit_percent * volume_per_hour`.
- `Trend Bonus` - бонус за подтвержденный рост.
- `Risk` - low/medium/high по stale data, low stock, OCR confidence.
- `Rounding Loss` - потери от целочисленных amount.

## Desktop overlay

MVP должен быть обычным desktop-приложением, не завязанным на Overwolf SDK.

Рекомендуемый стартовый стек:

- Python 3.11+
- PySide6 для overlay UI
- mss/Pillow для screen capture
- OpenCV для crop/preprocessing/template matching
- pytesseract или EasyOCR для fallback OCR
- SQLite для истории
- requests/httpx для poe.ninja/API

Причина: Python быстрее всего доведет OCR и экономическую модель до рабочего состояния. Если MVP подтвердит ценность, shell можно переписать на C#/.NET или Tauri/Rust.

## Модули приложения

```text
poe2_p2p/
  app.py                  # entrypoint
  config.py               # настройки, координаты crop, пороги
  models.py               # dataclass-модели
  parser.py               # ratio parser и OCR normalization
  calculator.py           # directed graph и arbitrage search
  storage.py              # SQLite
  sample_data.py          # данные со скриншотов для MVP
  ui/
    overlay.py            # PySide6 overlay window
```

## MVP

Первая рабочая версия:

1. Запускает overlay-окно с таблицей.
2. Загружает sample rates со скриншотов.
3. Считает прямую связку `Exalted -> Omen -> Divine -> Exalted`.
4. Показывает ROI, profit и confidence.
5. Сохраняет rates/opportunities в SQLite.
6. Имеет CLI fallback без UI.

После MVP:

1. Добавить screen capture crop.
2. Добавить OCR для ratio.
3. Добавить calibration mode.
4. Добавить hotkeys.
5. Добавить pre-filter из poe.ninja.
6. Добавить поиск циклов глубиной до 5.

## Риски реализации

- OCR может ошибаться на десятичной точке, порядке числа или направлении ratio.
- NPC ratio может измениться между scan и исполнением.
- Multi-hop profit может исчезать из-за rounding и недостаточного stock.
- Низколиквидные пары дают красивый ROI, но плохой фактический profit/hour.
- Полный scan рынка через UI будет медленным; нужен shortlist кандидатов.

## Критерии готовности

Для MVP:

- расчет по скриншотам дает ожидаемый profit около `181.68 Exalted` на `1 Omen` при `Divine = 352 Exalted`;
- CLI выводит opportunities;
- overlay запускается, если установлен PySide6;
- SQLite schema создается автоматически;
- отдельный документ с рекомендациями по стеку и экономике присутствует в корне проекта.

Для первой полезной версии:

- OCR confidence по ratio выше 95% на сохраненных скриншотах;
- scan одной пары занимает меньше 2 секунд;
- таблица показывает только opportunities с положительным net profit;
- каждый opportunity имеет объяснимую цепочку и источник каждого курса.
