"""Командный интерфейс ValutaTrade Hub.

CLI только разбирает аргументы и вызывает бизнес-логику из
``valutatrade_hub.core.usecases``; доменные исключения перехватываются и
превращаются в дружелюбные сообщения.
"""

import argparse
import sys
from typing import Any

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


def register_command(args: argparse.Namespace) -> None:
    """Команда регистрации нового пользователя."""
    try:
        user = usecases.register(username=args.username, password=args.password)
        print(f"Пользователь '{args.username}' зарегистрирован (id={user.user_id}).")
        print(f"Войдите: login --username {args.username} --password ****")
    except UsernameAlreadyExistsError as exc:
        print(exc.message)
    except ValueError as exc:
        print(str(exc))
    except ValutaTradeError as exc:
        print(exc.message)


def login_command(args: argparse.Namespace) -> None:
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


def logout_command(_args: argparse.Namespace) -> None:
    """Команда выхода из системы."""
    global _current_user_id
    _current_user_id = None
    print("Вы вышли из системы")


def show_portfolio_command(args: argparse.Namespace) -> None:
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


def buy_command(args: argparse.Namespace) -> None:
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


def sell_command(args: argparse.Namespace) -> None:
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


def get_rate_command(args: argparse.Namespace) -> None:
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


def update_rates_command(args: argparse.Namespace) -> None:
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


def show_rates_command(args: argparse.Namespace) -> None:
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

    items = []
    for pair_key, payload in pairs.items():
        rate = payload.get("rate") if isinstance(payload, dict) else payload
        updated = payload.get("updated_at", "") if isinstance(payload, dict) else ""
        items.append((pair_key, float(rate), updated))

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


def _build_parser() -> argparse.ArgumentParser:
    """Собирает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="valutatrade",
        description="ValutaTrade Hub — симулятор валютного кошелька.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_register = subparsers.add_parser("register", help="Создать пользователя")
    p_register.add_argument("--username", required=True)
    p_register.add_argument("--password", required=True)
    p_register.set_defaults(func=register_command)

    p_login = subparsers.add_parser("login", help="Войти в систему")
    p_login.add_argument("--username", required=True)
    p_login.add_argument("--password", required=True)
    p_login.set_defaults(func=login_command)

    p_logout = subparsers.add_parser("logout", help="Выйти из системы")
    p_logout.set_defaults(func=logout_command)

    p_portfolio = subparsers.add_parser("show-portfolio", help="Показать портфель")
    p_portfolio.add_argument("--base", default="USD")
    p_portfolio.set_defaults(func=show_portfolio_command)

    p_buy = subparsers.add_parser("buy", help="Купить валюту")
    p_buy.add_argument("--currency", required=True)
    p_buy.add_argument("--amount", type=float, required=True)
    p_buy.set_defaults(func=buy_command)

    p_sell = subparsers.add_parser("sell", help="Продать валюту")
    p_sell.add_argument("--currency", required=True)
    p_sell.add_argument("--amount", type=float, required=True)
    p_sell.set_defaults(func=sell_command)

    p_rate = subparsers.add_parser("get-rate", help="Получить курс валюты")
    p_rate.add_argument("--from", dest="from_currency", required=True)
    p_rate.add_argument("--to", dest="to_currency", required=True)
    p_rate.set_defaults(func=get_rate_command)

    p_update = subparsers.add_parser("update-rates", help="Обновить курсы")
    p_update.add_argument(
        "--source",
        choices=["coingecko", "exchangerate"],
        default=None,
    )
    p_update.set_defaults(func=update_rates_command)

    p_show = subparsers.add_parser("show-rates", help="Показать курсы из кеша")
    p_show.add_argument("--currency", default=None)
    p_show.add_argument("--top", type=int, default=None)
    p_show.add_argument("--base", default=None)
    p_show.set_defaults(func=show_rates_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI.

    Returns:
        Код возврата (0 — успех).
    """
    setup_logging()
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
