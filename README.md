# ValutaTrade Hub

`finalproject_<фамилия>_<группа>` — консольное приложение, имитирующее
платформу отслеживания и симуляции торговли фиатными и крипто-валютами.
Проект реализован как полноценный Python-пакет и состоит из двух сервисов:

* **Core Service** — CLI, пользователи, портфели, кошельки, история операций;
* **Parser Service** — сбор актуальных курсов из внешних API (CoinGecko и
  ExchangeRate-API) с записью в локальный кеш.

## Технологии

* Python 3.12+
* [`uv`](https://docs.astral.sh/uv/) — управление зависимостями и сборка пакета;
* [`ruff`](https://docs.astral.sh/ruff/) — линтер и форматтер (PEP8);
* `requests` — обращения к внешним API;
* `prettytable` — форматированный вывод таблиц;
* стандартные модули: `json`, `shlex`, `hashlib`, `logging`, `tomllib`.

## Структура проекта

```
finalproject_Makeev_M26-555/
├── data/
│   ├── users.json            # список пользователей
│   ├── portfolios.json       # портфели и кошельки
│   ├── rates.json            # локальный кеш курсов для Core Service
│   └── exchange_rates.json   # история измерений Parser Service
├── src/
│   ├── finalproject_makeev_m26_555/
│   │   └── __init__.py       # обёртка-точка входа (`run`)
│   └── valutatrade_hub/
│       ├── __init__.py
│       ├── logging_config.py # настройка логов (формат, уровень, ротация)
│       ├── decorators.py     # @log_action
│       ├── core/
│       │   ├── currencies.py # Currency / FiatCurrency / CryptoCurrency + реестр
│       │   ├── exceptions.py # доменные исключения
│       │   ├── models.py     # User, Wallet, Portfolio
│       │   ├── usecases.py   # бизнес-логика (register/login/buy/sell/get_rate)
│       │   └── utils.py      # валидации и конвертации
│       ├── infra/
│       │   ├── settings.py   # Singleton SettingsLoader
│       │   └── database.py   # Singleton DatabaseManager (JSON-хранилище)
│       ├── parser_service/
│       │   ├── config.py     # конфигурация API и путей
│       │   ├── api_clients.py # BaseApiClient, CoinGeckoClient, ExchangeRateApiClient
│       │   ├── updater.py    # RatesUpdater.run_update()
│       │   ├── storage.py    # rates.json / exchange_rates.json (атомарная запись)
│       │   └── scheduler.py  # периодическое обновление
│       └── cli/
│           └── interface.py  # команды CLI (единственная точка входа для команд)
├── main.py
├── pyproject.toml
├── uv.lock
└── README.md
```

## Установка

```bash
uv sync
```

`uv sync` установит зависимости (`requests`, `prettytable`) и соберёт пакет.

## Запуск

Запускать CLI можно любым из способов:

```bash
uv run main.py <команда>
# или
uv run valutatrade <команда>
```

### Команды

| Команда | Назначение |
|---|---|
| `register --username <str> --password <str>` | регистрация пользователя |
| `login --username <str> --password <str>` | вход в систему |
| `logout` | выход из системы |
| `show-portfolio [--base <str>]` | портфель и итоговая стоимость |
| `buy --currency <str> --amount <float>` | покупка валюты |
| `sell --currency <str> --amount <float>` | продажа валюты |
| `get-rate --from <str> --to <str>` | курс одной валюты к другой |
| `update-rates [--source coingecko\|exchangerate]` | обновление курсов через Parser Service |
| `show-rates [--currency <str>] [--top <int>] [--base <str>]` | просмотр кеша курсов |

Пример полного цикла:

```bash
uv run main.py register --username alice --password 1234
uv run main.py login --username alice --password 1234
# (сессия CLI хранится в рамках одного запуска; для интерактивной работы
#  используйте оболочку или последовательный вызов команд в одном процессе)
uv run main.py update-rates
uv run main.py show-rates --top 3
uv run main.py get-rate --from BTC --to USD
```

> Примечание: сессия `login` хранится в памяти процесса. Чтобы выполнять
> `buy`/`sell`/`show-portfolio` после входа, запускайте команды в одном
> интерактивном процессе (см. пример ниже) либо в своей оболочке.

```python
from valutatrade_hub.cli import interface as cli

cli.main(["login", "--username", "alice", "--password", "1234"])
cli.main(["buy", "--currency", "BTC", "--amount", "0.05"])
cli.main(["show-portfolio"])
```

## Parser Service

### Ключ ExchangeRate-API

Ключ хранится **не в коде**, а в переменной окружения. Скопируйте пример и
заполните его:

```bash
# .env
EXCHANGERATE_API_KEY=ваш_ключ
```

Приложение автоматически подхватывает `.env` (файл исключён из git через
`.gitignore`). CoinGecko работает без ключа.

### Обновление курсов

```bash
uv run main.py update-rates                  # все источники
uv run main.py update-rates --source coingecko
```

Parser Service опрашивает клиентов, объединяет курсы, пишет кеш в
`data/rates.json` (атомарно: временный файл → `os.replace`) и ведёт историю в
`data/exchange_rates.json`. Падение одного источника не останавливает работу
остальных.

### Периодическое обновление (scheduler)

`update-rates` обновляет курсы один раз. Для регулярного фонового обновления
служит `valutatrade_hub.parser_service.scheduler.UpdateScheduler`: он вызывает
`RatesUpdater.run_update()` в отдельном демон-потоке через заданный интервал
(по умолчанию `DEFAULT_INTERVAL_SECONDS = 300` секунд).

```python
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import UpdateScheduler
from valutatrade_hub.parser_service.storage import RatesStorage

config = ParserConfig()
storage = RatesStorage(config)
clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]

scheduler = UpdateScheduler(clients, storage, config, interval_seconds=300)
scheduler.start()          # фоновое обновление каждые 300 с
# ... работа приложения ...
scheduler.stop()           # корректная остановка потока
```

Ключевые методы:

| Метод | Назначение |
|---|---|
| `run_once(source=None)` | однократное обновление (как у `update-rates`) |
| `start(source=None)` | запуск фонового обновления (повторный вызов безвреден) |
| `stop(timeout=5.0)` | остановка фонового потока |

Ошибки отдельного цикла обновления логируются и не приводят к падению
планировщика. Функция `run_scheduler(...)` запускает планировщик в блокирующем
режиме (останавливается по `Ctrl+C`) и удобна для ручного запуска отдельным
процессом.

### Формат `data/rates.json`

```json
{
  "pairs": {
    "EUR_USD": { "rate": 1.0786, "updated_at": "2025-10-10T12:00:00Z", "source": "ExchangeRate-API" },
    "BTC_USD": { "rate": 59337.21, "updated_at": "2025-10-10T12:00:00Z", "source": "CoinGecko" }
  },
  "source": "ParserService",
  "last_refresh": "2025-10-10T12:00:01Z"
}
```

### Кеш и TTL

Core Service читает именно `rates.json`. Актуальность значения определяется
порогом `RATES_TTL_SECONDS` (по умолчанию `300` секунд, задаётся в секции
`[tool.valutatrade]` в `pyproject.toml`). Если курс свежий — `get-rate` берёт
его из кеша. Если данных нет или они устарели, `get-rate` пытается обновить
кеш через Parser Service (тихо, без вывода прогресса), и только при неудаче
сообщает, что курс недоступен, и предлагает выполнить `update-rates`.

### Базовая валюта в `show-portfolio` и `show-rates`

* `show-portfolio --base <код>` приводит стоимость каждого кошелька и итог к
  указанной базовой валюте (по курсам из кеша и резервным `DEFAULT_RATES`).
* `show-rates --base <код>` пересчитывает курсы относительно указанной базы
  (например, `show-rates --base EUR` покажет `BTC_EUR`, `ETH_EUR`, ...).

## Архитектура и решения

* **Singleton** — `SettingsLoader` и `DatabaseManager` реализованы через
  `__new__`: для синглтона без наследования это простой и читаемый приём, не
  требующий метакласса.
* **Иерархия валют** — ABC `Currency` и наследники `FiatCurrency` /
  `CryptoCurrency` с полиморфным `get_display_info()` и фабрикой
  `get_currency(code)`.
* **Исключения** — `InsufficientFundsError`, `CurrencyNotFoundError`,
  `ApiRequestError` пробрасываются из ядра и перехватываются в CLI.
* **Декоратор `@log_action`** — трассирует `buy`/`sell`/`register`/`login` на
  уровне INFO, не глотает исключения; используется в `core/usecases.py`.
* **Логирование** — `logging_config.py`, формат `ISO timestamp LEVEL logger
  message`, ротация через `RotatingFileHandler` (`logs/actions.log`).

## Качество кода

```bash
uv run ruff check .
uv run ruff format .
```