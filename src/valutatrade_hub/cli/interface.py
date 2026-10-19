"""Командный интерфейс ValutaTrade Hub.

CLI только разбирает аргументы и вызывает бизнес-логику из
``valutatrade_hub.core.usecases``; доменные исключения перехватываются и
превращаются в дружелюбные сообщения.

Строка ввода пользователя разбирается модулем :mod:`shlex`, а флаги
(``--username`` и т.п.) — небольшим реестром команд вместо ``argparse``.
"""

import shlex
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidPasswordError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
    ValutaTradeError,
)
from valutatrade_hub.logging_config import setup_logging

#: id текущего залогиненного пользователя (сессия CLI).
_current_user_id: int | None = None


def _require_login() -> int | None:
    """Проверяет, что пользователь залогинен.

    Returns:
        id пользователя или ``None`` (и печатает подсказку).
    """
    if _current_user_id is None:
        print("Сначала выполните login")
        return None
    return _current_user_id


def register_command(args: SimpleNamespace) -> None:
    """Команда регистрации нового пользователя."""
    try:
        user = usecases.register(username=args.username, password=args.password)
        quoted = shlex.quote(args.username)
        print(f"Пользователь '{args.username}' зарегистрирован (id={user.user_id}).")
        print(f"Войдите: login --username {quoted} --password ****")
    except UsernameAlreadyExistsError as exc:
        print(exc.message)
    except ValueError as exc:
        print(str(exc))
    except ValutaTradeError as exc:
        print(exc.message)


def login_command(args: SimpleNamespace) -> None:
    """Команда входа в систему."""
    global _current_user_id
    try:
        user = usecases.login(username=args.username, password=args.password)
        _current_user_id = user.user_id
        print(f"Вы вошли как '{args.username}'")
    except UserNotFoundError as exc:
        print(exc.message)
    except InvalidPasswordError as exc:
        print(exc.message)
    except ValutaTradeError as exc:
        print(exc.message)


def logout_command(_args: SimpleNamespace) -> None:
    """Команда выхода из системы."""
    global _current_user_id
    _current_user_id = None
    print("Вы вышли из системы")


def show_portfolio_command(args: SimpleNamespace) -> None:
    """Команда показа портфеля и итоговой стоимости."""
    user_id = _require_login()
    if user_id is None:
        return

    try:
        view = usecases.portfolio_view(user_id, base=args.base)
    except CurrencyNotFoundError as exc:
        print(exc.message)
        return

    user = usecases.get_user(user_id)
    if not view["rows"]:
        print(f"Портфель пользователя '{user.username}' пуст.")
        return

    print(f"Портфель пользователя '{user.username}' (база: {view['base']}):")
    for row in view["rows"]:
        if row["value"] is None:
            print(f"- {row['currency']}: {row['balance']:.4f}")
        else:
            print(
                f"- {row['currency']}: {row['balance']:.4f}  "
                f"→ {row['value']:.2f} {view['base']}"
            )
    print("-" * 33)
    print(f"ИТОГО: {view['total']:,.2f} {view['base']}")


def buy_command(args: SimpleNamespace) -> None:
    """Команда покупки валюты."""
    user_id = _require_login()
    if user_id is None:
        return

    try:
        result = usecases.buy(
            user_id=user_id,
            currency_code=args.currency,
            amount=args.amount,
        )
    except InsufficientFundsError as exc:
        print(exc.message)
        return
    except (CurrencyNotFoundError, ValueError) as exc:
        print(exc.message if isinstance(exc, ValutaTradeError) else str(exc))
        return

    print(
        f"Покупка выполнена: {result['amount']:.4f} {result['currency']} "
        f"по курсу {result['rate']:.2f} {result['base']}/{result['currency']}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {result['currency']}: было {result['balance_before']:.4f} "
        f"→ стало {result['balance_after']:.4f}"
    )
    print(f"Оценочная стоимость покупки: {result['value']:,.2f} {result['base']}")


def sell_command(args: SimpleNamespace) -> None:
    """Команда продажи валюты."""
    user_id = _require_login()
    if user_id is None:
        return

    try:
        result = usecases.sell(
            user_id=user_id,
            currency_code=args.currency,
            amount=args.amount,
        )
    except InsufficientFundsError as exc:
        print(exc.message)
        return
    except (CurrencyNotFoundError, ValueError) as exc:
        print(exc.message if isinstance(exc, ValutaTradeError) else str(exc))
        return

    print(
        f"Продажа выполнена: {result['amount']:.4f} {result['currency']} "
        f"по курсу {result['rate']:.2f} {result['base']}/{result['currency']}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {result['currency']}: было {result['balance_before']:.4f} "
        f"→ стало {result['balance_after']:.4f}"
    )
    print(f"Оценочная выручка: {result['value']:,.2f} {result['base']}")


def get_rate_command(args: SimpleNamespace) -> None:
    """Команда получения курса одной валюты к другой."""
    try:
        result = usecases.get_rate(args.from_currency, args.to_currency)
    except CurrencyNotFoundError as exc:
        print(f"{exc.message}. Выполните 'help get-rate' или проверьте код.")
        return
    except ApiRequestError as exc:
        print(exc.message)
        return

    updated = result.get("updated_at") or "нет данных"
    print(
        f"Курс {result['from']}→{result['to']}: {result['rate']:.8f} "
        f"(обновлено: {updated})"
    )
    if result["rate"]:
        reverse = 1 / result["rate"]
        reverse_str = f"{reverse:.8f}" if reverse < 1 else f"{reverse:.2f}"
        print(f"Обратный курс {result['to']}→{result['from']}: {reverse_str}")


def update_rates_command(args: SimpleNamespace) -> None:
    """Команда обновления курсов через Parser Service."""
    try:
        from valutatrade_hub.parser_service.api_clients import (
            CoinGeckoClient,
            ExchangeRateApiClient,
        )
        from valutatrade_hub.parser_service.config import ParserConfig
        from valutatrade_hub.parser_service.storage import RatesStorage
        from valutatrade_hub.parser_service.updater import RatesUpdater
    except ImportError as exc:
        print(f"ERROR: Missing dependencies - {exc}")
        print("Please run: uv add requests")
        return

    config = ParserConfig()
    if not config.is_valid():
        print(f"WARNING: {config.get_warning_message()}")
        print("Some sources may not be available.\n")

    storage = RatesStorage(config)
    clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]
    updater = RatesUpdater(clients, storage, config)
    updater.run_update(source=args.source)


def _load_cache_pairs() -> dict[str, Any]:
    """Читает пары из кеша rates.json (пустой словарь при отсутствии)."""
    from valutatrade_hub.core.utils import load_json

    data = load_json("RATES_FILE", default={})
    if isinstance(data, dict):
        pairs = data.get("pairs")
        if isinstance(pairs, dict):
            return pairs
    return {}


def _cache_last_refresh() -> str:
    """Возвращает время последнего обновления кеша."""
    from valutatrade_hub.core.utils import load_json

    data = load_json("RATES_FILE", default={})
    if isinstance(data, dict):
        return str(data.get("last_refresh", ""))
    return ""


def _rates_to_usd(pairs: dict[str, Any]) -> dict[str, float]:
    """Собирает курсы ``{code: сколько USD стоит 1 единица}`` из пар кеша."""
    from valutatrade_hub.core.models import DEFAULT_RATES

    rates = dict(DEFAULT_RATES)
    for pair_key, payload in pairs.items():
        rate = payload.get("rate") if isinstance(payload, dict) else payload
        if rate is None:
            continue
        from_code, _, to_code = pair_key.partition("_")
        if to_code == "USD":
            rates[from_code] = float(rate)
    return rates


def show_rates_command(args: SimpleNamespace) -> None:
    """Команда показа курсов из локального кеша."""
    pairs = _load_cache_pairs()
    if not pairs:
        print(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )
        return

    if args.currency:
        code = args.currency.upper()
        filtered = {
            key: value for key, value in pairs.items() if key.split("_")[0] == code
        }
        if not filtered:
            print(f"Курс для '{code}' не найден в кеше.")
            return
        pairs = filtered

    base = None
    base_rate = 1.0
    if args.base:
        base = args.base.upper()
        usd_rates = _rates_to_usd(_load_cache_pairs())
        base_rate = usd_rates.get(base)
        if not base_rate:
            print(f"Курс для '{base}' не найден в кеше.")
            return

    items = []
    for pair_key, payload in pairs.items():
        rate = payload.get("rate") if isinstance(payload, dict) else payload
        updated = payload.get("updated_at", "") if isinstance(payload, dict) else ""
        value = float(rate)
        if base is not None:
            from_code = pair_key.split("_")[0]
            pair_key = f"{from_code}_{base}"
            value = value / base_rate
        items.append((pair_key, value, updated))

    if args.top:
        items.sort(key=lambda item: item[1], reverse=True)
        items = items[: args.top]
    else:
        items.sort(key=lambda item: item[0])

    last_refresh = _cache_last_refresh()
    table = PrettyTable()
    table.field_names = ["Pair", "Rate", "Updated"]
    for pair_key, rate, updated in items:
        table.add_row([pair_key, rate, updated or "-"])
    print(f"Rates from cache (updated at {last_refresh}):")
    print(table)


@dataclass(frozen=True)
class _Option:
    """Описание одного флага команды (``--name``)."""

    #: Имя без ведущих дефисов (например, ``"username"``).
    name: str
    #: Имя атрибута в ``SimpleNamespace`` (по умолчанию — ``name``).
    dest: str = ""
    #: Обязателен ли флаг.
    required: bool = False
    #: Преобразователь типа (``str``/``float``/``int``); ``None`` — строка.
    type: Callable[[str], Any] | None = None
    #: Значение по умолчанию.
    default: Any = None
    #: Допустимые значения (для валидации, как ``choices`` в argparse).
    choices: tuple[str, ...] | None = None


@dataclass(frozen=True)
class _Command:
    """Описание команды: обработчик, флаги и подсказка."""

    handler: Callable[[SimpleNamespace], None]
    options: tuple[_Option, ...] = ()
    help: str = ""


#: Реестр команд CLI: имя → описание.
COMMANDS: dict[str, _Command] = {
    "register": _Command(
        handler=register_command,
        help="Создать пользователя",
        options=(
            _Option("username", required=True),
            _Option("password", required=True),
        ),
    ),
    "login": _Command(
        handler=login_command,
        help="Войти в систему",
        options=(
            _Option("username", required=True),
            _Option("password", required=True),
        ),
    ),
    "logout": _Command(handler=logout_command, help="Выйти из системы"),
    "show-portfolio": _Command(
        handler=show_portfolio_command,
        help="Показать портфель",
        options=(_Option("base", default="USD"),),
    ),
    "buy": _Command(
        handler=buy_command,
        help="Купить валюту",
        options=(
            _Option("currency", required=True),
            _Option("amount", type=float, required=True),
        ),
    ),
    "sell": _Command(
        handler=sell_command,
        help="Продать валюту",
        options=(
            _Option("currency", required=True),
            _Option("amount", type=float, required=True),
        ),
    ),
    "get-rate": _Command(
        handler=get_rate_command,
        help="Получить курс валюты",
        options=(
            _Option("from", dest="from_currency", required=True),
            _Option("to", dest="to_currency", required=True),
        ),
    ),
    "update-rates": _Command(
        handler=update_rates_command,
        help="Обновить курсы",
        options=(
            _Option("source", default=None, choices=("coingecko", "exchangerate")),
        ),
    ),
    "show-rates": _Command(
        handler=show_rates_command,
        help="Показать курсы из кеша",
        options=(
            _Option("currency", default=None),
            _Option("top", type=int, default=None),
            _Option("base", default=None),
        ),
    ),
}

__all__ = ["COMMANDS", "main", "run_command"]


class _UsageError(Exception):
    """Ошибка разбора аргументов: неизвестный флаг, пропуск обязательного и т.п."""


def _tokenize(raw: str | list[str]) -> list[str]:
    """Разбивает строку на токены через ``shlex``.

    Строка ``'buy --currency BTC --amount 0.05'`` превращается в список
    аргументов; кавычки поддерживаются (``--password "a b"``).

    Args:
        raw: Строка команды или уже готовый список токенов.

    Returns:
        Список токенов.

    Raises:
        _UsageError: Если кавычки в строке не закрыты.
    """
    if isinstance(raw, str):
        try:
            return shlex.split(raw)
        except ValueError as exc:
            raise _UsageError(f"Некорректная строка команды: {exc}") from exc
    return list(raw)


def _parse_options(command: _Command, tokens: list[str]) -> SimpleNamespace:
    """Разбирает флаги ``--name value`` в объект ``SimpleNamespace``.

    Raises:
        _UsageError: При неизвестном флаге, отсутствии значения, неверном
            типе, недопустимом значении или пропуске обязательного флага.
    """
    by_name = {option.name: option for option in command.options}
    values: dict[str, Any] = {option.name: option.default for option in command.options}
    seen: set[str] = set()

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            raise _UsageError(f"Неожиданный аргумент: '{token}'")

        name = token[2:]
        if "=" in name:
            name, _, inline = name.partition("=")
        else:
            inline = None

        option = by_name.get(name)
        if option is None:
            raise _UsageError(f"Неизвестный флаг: '{token}'")

        if inline is not None:
            raw_value = inline
        else:
            index += 1
            if index >= len(tokens):
                raise _UsageError(f"Для флага '--{name}' не указано значение")
            raw_value = tokens[index]

        if option.type is not None:
            try:
                raw_value = option.type(raw_value)
            except (TypeError, ValueError) as exc:
                type_name = getattr(option.type, "__name__", str(option.type))
                raise _UsageError(
                    f"Флаг '--{name}' ожидает значение типа {type_name}"
                ) from exc

        if option.choices is not None and raw_value not in option.choices:
            allowed = ", ".join(option.choices)
            raise _UsageError(f"Флаг '--{name}' должен быть одним из: {allowed}")

        values[option.name] = raw_value
        seen.add(option.name)
        index += 1

    missing = [
        option.name
        for option in command.options
        if option.required and option.name not in seen
    ]
    if missing:
        flags = ", ".join(f"--{name}" for name in missing)
        raise _UsageError(f"Отсутствует обязательный флаг: {flags}")

    resolved = {
        (option.dest or option.name): values[option.name] for option in command.options
    }
    return SimpleNamespace(**resolved)


def run_command(raw: str | list[str]) -> int:
    """Разбирает строку команды и выполняет соответствующий обработчик.

    Args:
        raw: Строка вида ``"buy --currency BTC --amount 0.05"`` или список
            токенов.

    Returns:
        Код возврата (0 — успех, 2 — ошибка разбора аргументов).
    """
    setup_logging()
    tokens = _tokenize(raw)
    if not tokens:
        print_help()
        return 1

    name, *rest = tokens
    command = COMMANDS.get(name)
    if command is None:
        print(f"Неизвестная команда: '{name}'")
        print_help()
        return 2

    try:
        args = _parse_options(command, rest)
    except _UsageError as exc:
        print(f"Ошибка аргументов: {exc}")
        print(f"Использование: {_usage(name)}")
        return 2

    command.handler(args)
    return 0


def _usage(name: str) -> str:
    """Собирает строку использования команды для подсказок об ошибках."""
    command = COMMANDS.get(name)
    if command is None:
        return name
    parts = [name]
    for option in command.options:
        flag = f"--{option.name}"
        if option.required:
            parts.append(f"{flag} <{_type_label(option)}>")
        else:
            parts.append(f"[{flag}]")
    return " ".join(parts)


def _type_label(option: _Option) -> str:
    """Человекочитаемое имя типа для подсказки использования."""
    if option.type is float:
        return "float"
    if option.type is int:
        return "int"
    return "str"


def print_help() -> None:
    """Печатает список доступных команд."""
    print("ValutaTrade Hub — симулятор валютного кошелька.")
    print("Доступные команды:")
    for name, command in COMMANDS.items():
        print(f"  {_usage(name):<45} {command.help}")


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI.

    Args:
        argv: Аргументы без имени программы. Если не переданы, берётся
            ``sys.argv[1:]`` и склеивается в строку для ``shlex``.

    Returns:
        Код возврата (0 — успех).
    """
    if argv is None:
        argv = sys.argv[1:]
    return run_command(argv)


if __name__ == "__main__":
    sys.exit(main())
