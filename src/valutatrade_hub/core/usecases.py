"""Бизнес-логика приложения: регистрация, вход, портфель, buy/sell, курс."""

import logging
from datetime import datetime
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InvalidPasswordError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from valutatrade_hub.core.models import DEFAULT_RATES, Portfolio, User
from valutatrade_hub.core.utils import (
    find_by,
    get_next_id,
    load_json,
    save_json,
    validate_amount,
    validate_currency_code,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import suppress_console

logger = logging.getLogger("valutatrade_hub.core.usecases")

BASE_CURRENCY = "USD"


def _settings() -> SettingsLoader:
    return SettingsLoader()


def _now_iso() -> str:
    return datetime.now().isoformat()


@log_action(verbose=True)
def register(username: str, password: str) -> User:
    """Создаёт нового пользователя и пустой портфель.

    Raises:
        UsernameAlreadyExistsError: Если имя занято.
        ValueError: Если имя пустое или пароль слишком короткий.
    """
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = load_json("USERS_FILE")
    if find_by(users, username=username) is not None:
        raise UsernameAlreadyExistsError(username)

    user = User.create(
        user_id=get_next_id(users),
        username=username.strip(),
        password=password,
    )

    users.append(user.to_dict())
    save_json("USERS_FILE", users)

    portfolios = load_json("PORTFOLIOS_FILE")
    portfolios.append(Portfolio(user.user_id).to_dict())
    save_json("PORTFOLIOS_FILE", portfolios)

    return user


@log_action(verbose=True)
def login(username: str, password: str) -> User:
    """Аутентифицирует пользователя.

    Raises:
        UserNotFoundError: Если пользователь не найден.
        InvalidPasswordError: Если пароль неверный.
    """
    users = load_json("USERS_FILE")
    user_data = find_by(users, username=username)
    if user_data is None:
        raise UserNotFoundError(username)

    user = User.from_dict(user_data)
    if not user.verify_password(password):
        raise InvalidPasswordError(username)
    return user


def get_user(user_id: int) -> User:
    """Возвращает пользователя по id или бросает ``UserNotFoundError``."""
    users = load_json("USERS_FILE")
    data = find_by(users, user_id=user_id)
    if data is None:
        raise UserNotFoundError(str(user_id))
    return User.from_dict(data)


def get_portfolio(user_id: int) -> Portfolio:
    """Загружает портфель пользователя (создаёт пустой при отсутствии)."""
    portfolios = load_json("PORTFOLIOS_FILE")
    data = find_by(portfolios, user_id=user_id)
    if data is None:
        portfolio = Portfolio(user_id)
        portfolios.append(portfolio.to_dict())
        save_json("PORTFOLIOS_FILE", portfolios)
        return portfolio
    return Portfolio.from_dict(data)


def _save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет изменения портфеля в хранилище."""
    portfolios = load_json("PORTFOLIOS_FILE")
    for index, item in enumerate(portfolios):
        if item.get("user_id") == portfolio.user_id:
            portfolios[index] = portfolio.to_dict()
            break
    else:
        portfolios.append(portfolio.to_dict())
    save_json("PORTFOLIOS_FILE", portfolios)


def load_cached_rates() -> dict[str, dict[str, Any]]:
    """Читает пары курсов из локального кеша rates.json."""
    data = load_json("RATES_FILE", default={})
    if not isinstance(data, dict):
        return {}
    pairs = data.get("pairs", {})
    return pairs if isinstance(pairs, dict) else {}


def _rates_to_usd() -> dict[str, float]:
    """Собирает курсы вида ``{code: сколько USD стоит 1 единица}``.

    Берёт данные из кеша rates.json, дополняя резервными ``DEFAULT_RATES``.
    """
    rates = dict(DEFAULT_RATES)
    for pair_key, payload in load_cached_rates().items():
        if not isinstance(payload, dict):
            continue
        rate = payload.get("rate")
        if rate is None:
            continue
        from_code, _, to_code = pair_key.partition("_")
        if to_code != BASE_CURRENCY:
            continue
        rates[from_code] = float(rate)
    return rates


def refresh_rates(source: str | None = None) -> dict[str, Any]:
    """Обновляет кеш курсов через Parser Service.

    Args:
        source: Опциональный фильтр источника ("coingecko"/"exchangerate").

    Raises:
        ApiRequestError: Если не удалось обновить ни одного курса.
    """
    from valutatrade_hub.parser_service.api_clients import (
        CoinGeckoClient,
        ExchangeRateApiClient,
    )
    from valutatrade_hub.parser_service.config import ParserConfig
    from valutatrade_hub.parser_service.storage import RatesStorage
    from valutatrade_hub.parser_service.updater import RatesUpdater

    config = ParserConfig()
    storage = RatesStorage(config)
    clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]
    updater = RatesUpdater(clients, storage, config)

    # Внутреннее обновление не должно шуметь в консоль: ожидаемые сбои
    # источников пишутся в файл, но не мешают выводу CLI.
    with suppress_console():
        result = updater.run_update(source=source, quiet=True)

    if not result.get("rates_count"):
        reason = "; ".join(result.get("errors") or []) or "нет данных"
        raise ApiRequestError(reason)
    return result


def _rate_from_cache(from_code: str, to_code: str) -> dict[str, Any] | None:
    """Возвращает свежий курс из кеша или ``None``."""
    cached = load_cached_rates()
    pair_key = f"{from_code}_{to_code}"
    reverse_key = f"{to_code}_{from_code}"
    ttl = int(_settings().get("RATES_TTL_SECONDS", 300))
    now = datetime.now()

    payload = cached.get(pair_key)
    if payload and not _is_stale(payload.get("updated_at"), ttl, now):
        return {
            "from": from_code,
            "to": to_code,
            "rate": float(payload["rate"]),
            "updated_at": payload.get("updated_at"),
            "source": payload.get("source", "cache"),
        }

    reverse = cached.get(reverse_key)
    if reverse and reverse.get("rate"):
        return {
            "from": from_code,
            "to": to_code,
            "rate": 1.0 / float(reverse["rate"]),
            "updated_at": reverse.get("updated_at"),
            "source": reverse.get("source", "cache"),
        }
    return None


def get_rate(from_code: str, to_code: str) -> dict[str, Any]:
    """Возвращает курс ``from_code`` → ``to_code`` и метаданные кеша.

    Если кеш устарел или отсутствует, предпринимается попытка обновить его
    через Parser Service; при неудаче бросается ``ApiRequestError``.

    Raises:
        CurrencyNotFoundError: Если одна из валют неизвестна.
        ApiRequestError: Если данных нет и обновить кеш не удалось.
    """
    from_code = validate_currency_code(from_code)
    to_code = validate_currency_code(to_code)

    result = _rate_from_cache(from_code, to_code)
    if result is not None:
        return result

    try:
        refresh_rates()
    except ApiRequestError as exc:
        logger.warning("Не удалось обновить кеш курсов: %s", exc)
        raise ApiRequestError(
            f"курс {from_code}→{to_code} недоступен. Повторите попытку позже."
        ) from exc

    result = _rate_from_cache(from_code, to_code)
    if result is not None:
        return result

    raise ApiRequestError(
        f"курс {from_code}→{to_code} недоступен. Повторите попытку позже."
    )


def _is_stale(updated_at: str | None, ttl: int, now: datetime) -> bool:
    """Проверяет, старше ли метка времени порога TTL."""
    if not updated_at:
        return True
    try:
        moment = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if moment.tzinfo is not None:
        now = datetime.now(moment.tzinfo)
    return (now - moment).total_seconds() > ttl


@log_action(verbose=True)
def buy(user_id: int, currency_code: str, amount: float) -> dict[str, Any]:
    """Покупает валюту: создаёт кошелёк при необходимости и пополняет его.

    Raises:
        CurrencyNotFoundError: Если валюта неизвестна.
        ValueError: Если сумма некорректна.
    """
    currency_code = validate_currency_code(currency_code)
    amount = validate_amount(amount)
    get_currency(currency_code)

    portfolio = get_portfolio(user_id)
    wallet = portfolio.get_wallet(currency_code)
    balance_before = wallet.balance if wallet else 0.0

    if wallet is None:
        wallet = portfolio.add_currency(currency_code)

    wallet.deposit(amount)
    _save_portfolio(portfolio)

    rate = _rate_to_base(currency_code)
    return {
        "currency": currency_code,
        "amount": amount,
        "balance_before": balance_before,
        "balance_after": wallet.balance,
        "rate": rate,
        "base": BASE_CURRENCY,
        "value": amount * rate,
    }


@log_action(verbose=True)
def sell(user_id: int, currency_code: str, amount: float) -> dict[str, Any]:
    """Продаёт валюту: списывает средства с кошелька.

    Raises:
        InsufficientFundsError: Если недостаточно средств.
        ValueError: Если кошелька нет или сумма некорректна.
    """
    currency_code = validate_currency_code(currency_code)
    amount = validate_amount(amount)

    portfolio = get_portfolio(user_id)
    wallet = portfolio.get_wallet(currency_code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{currency_code}'. "
            "Он создаётся автоматически при первой покупке."
        )

    balance_before = wallet.balance
    wallet.withdraw(amount)
    _save_portfolio(portfolio)

    rate = _rate_to_base(currency_code)
    return {
        "currency": currency_code,
        "amount": amount,
        "balance_before": balance_before,
        "balance_after": wallet.balance,
        "rate": rate,
        "base": BASE_CURRENCY,
        "value": amount * rate,
    }


def _rate_to_base(currency_code: str) -> float:
    """Курс валюты к базовой (USD), с мягким откатом на резервный."""
    rates = _rates_to_usd()
    return rates.get(currency_code, 0.0)


def portfolio_view(user_id: int, base: str = BASE_CURRENCY) -> dict[str, Any]:
    """Собирает данные портфеля для показа из CLI.

    Стоимость каждого кошелька и итог приводятся к ``base``.
    Резервные ``DEFAULT_RATES`` гарантируют наличие курса для базовой валюты,
    поэтому базовая валюта всегда известна.

    Raises:
        CurrencyNotFoundError: Если базовая валюта неизвестна.
    """
    base = validate_currency_code(base)
    portfolio = get_portfolio(user_id)
    rates = _rates_to_usd()

    base_rate = rates.get(base)
    if not base_rate:
        raise CurrencyNotFoundError(base)

    rows = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        rate = rates.get(code)
        value = wallet.balance * rate / base_rate if rate else None
        if value is not None:
            total += value
        rows.append(
            {
                "currency": code,
                "balance": wallet.balance,
                "rate": rate,
                "value": value,
            }
        )

    return {"base": base, "rows": rows, "total": total}


__all__ = [
    "buy",
    "get_portfolio",
    "get_rate",
    "get_user",
    "load_cached_rates",
    "login",
    "portfolio_view",
    "register",
    "sell",
]
