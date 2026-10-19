"""Иерархия валют: базовый ABC ``Currency`` и наследники ``FiatCurrency`` /
``CryptoCurrency``, а также реестр для получения валюты по коду.
"""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError

MIN_CODE_LENGTH = 2
MAX_CODE_LENGTH = 5


class Currency(ABC):
    """Абстрактная валюта с человекочитаемым именем и кодом.

    Инварианты:
        * ``code`` — верхний регистр, 2–5 символов, без пробелов;
        * ``name`` — непустая строка.
    """

    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")

        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")

        normalized = code.strip()
        if not normalized or " " in normalized:
            raise ValueError("Код валюты не может быть пустым или содержать пробелы")

        normalized = normalized.upper()
        if not (MIN_CODE_LENGTH <= len(normalized) <= MAX_CODE_LENGTH):
            raise ValueError(
                f"Код валюты должен быть {MIN_CODE_LENGTH}-{MAX_CODE_LENGTH} "
                f"символов, получено: {normalized}"
            )

        self.name = name
        self.code = normalized

    @property
    def is_fiat(self) -> bool:
        """Является ли валюта фиатной."""
        return isinstance(self, FiatCurrency)

    @property
    def is_crypto(self) -> bool:
        """Является ли валюта криптовалютой."""
        return isinstance(self, CryptoCurrency)

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI и логов."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code='{self.code}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Currency):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)


class FiatCurrency(Currency):
    """Фиатная валюта с указанием страны/зоны эмиссии."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        """Формат: ``[FIAT] USD — US Dollar (Issuing: United States)``."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом и рыночной капитализацией."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if not isinstance(market_cap, (int, float)) or market_cap < 0:
            raise ValueError("Капитализация должна быть неотрицательным числом")
        self.algorithm = algorithm
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Формат: ``[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)``."""
        mcap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap})"
        )


#: Реестр известных валют проекта.
_CURRENCIES: dict[str, Currency] = {}


def register_currency(currency: Currency) -> None:
    """Добавляет валюту в реестр (перезаписывая одноимённый код)."""
    _CURRENCIES[currency.code] = currency


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду из реестра.

    Args:
        code: Код валюты (регистр не важен).

    Returns:
        Объект ``Currency``.

    Raises:
        CurrencyNotFoundError: Если код неизвестен.
    """
    if not isinstance(code, str) or not code.strip():
        raise CurrencyNotFoundError(str(code))

    normalized = code.strip().upper()
    currency = _CURRENCIES.get(normalized)
    if currency is None:
        raise CurrencyNotFoundError(normalized)
    return currency


def list_currencies() -> list[Currency]:
    """Возвращает список всех зарегистрированных валют."""
    return list(_CURRENCIES.values())


def _register_defaults() -> None:
    """Заполняет реестр базовым набором валют."""
    register_currency(FiatCurrency("US Dollar", "USD", "United States"))
    register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
    register_currency(FiatCurrency("British Pound", "GBP", "United Kingdom"))
    register_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))
    register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
    register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11))
    register_currency(CryptoCurrency("Solana", "SOL", "Proof of History", 6.8e10))


_register_defaults()
