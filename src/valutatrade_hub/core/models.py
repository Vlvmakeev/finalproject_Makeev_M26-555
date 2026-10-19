"""Доменные модели: ``User``, ``Wallet`` и ``Portfolio``."""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError

MIN_PASSWORD_LENGTH = 4

#: Резервные курсы (сколько USD стоит 1 единица валюты) до Parser Service.
DEFAULT_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.24,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.0,
    "SOL": 145.12,
}


class User:
    """Пользователь системы.

    Атрибуты:
        _user_id (int): Уникальный идентификатор пользователя.
        _username (str): Имя пользователя.
        _hashed_password (str): Хешированный пароль.
        _salt (str): Соль для хеширования.
        _registration_date (datetime): Дата регистрации.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Односторонний псевдо-хеш ``sha256(password + salt)``."""
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """Создаёт пользователя с новой солью и хешем пароля."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
            )

        salt = secrets.token_hex(8)
        hashed = cls._hash_password(password, salt)
        return cls(
            user_id=user_id,
            username=username,
            hashed_password=hashed,
            salt=salt,
            registration_date=datetime.now(),
        )

    def get_user_info(self) -> dict:
        """Информация о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя с хешированием."""
        if not isinstance(new_password, str) or len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
            )
        self._hashed_password = self._hash_password(new_password, self.salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет пароль на совпадение."""
        return self._hash_password(password, self.salt) == self._hashed_password

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты.

    Атрибуты:
        _currency_code (str): Код валюты (например, "USD", "BTC").
        _balance (float): Баланс в данной валюте.
    """

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self._currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if amount < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(amount)

    @staticmethod
    def _check_amount(amount: float) -> None:
        """Проверяет, что сумма — положительное число."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом")

    def deposit(self, amount: float) -> float:
        """Пополняет баланс и возвращает новый баланс."""
        self._check_amount(amount)
        self._balance += float(amount)
        return self._balance

    def withdraw(self, amount: float) -> float:
        """Снимает средства, если баланс позволяет.

        Raises:
            InsufficientFundsError: Если на балансе недостаточно средств.
        """
        self._check_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self._currency_code,
            )
        self._balance -= float(amount)
        return self._balance

    def get_balance_info(self) -> str:
        """Возвращает строку с информацией о балансе."""
        return f"Валюта: {self._currency_code}\nБаланс: {self._balance}"

    def to_dict(self) -> dict:
        return {"currency_code": self._currency_code, "balance": self._balance}

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        return cls(
            currency_code=data["currency_code"],
            balance=data.get("balance", 0.0),
        )


class Portfolio:
    """Портфель пользователя: набор кошельков по кодам валют."""

    def __init__(self, user_id: int, wallets: dict[str, Wallet] | None = None):
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = wallets if wallets is not None else {}
        self._user: User | None = None

    @property
    def user(self) -> User | None:
        """Привязанный пользователь (только чтение)."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря кошельков."""
        return dict(self._wallets)

    @property
    def user_id(self) -> int:
        return self._user_id

    def add_currency(self, currency_code: str) -> Wallet:
        """Создаёт новый кошелёк, если такого ещё нет.

        Raises:
            ValueError: Если кошелёк с таким кодом уже существует.
        """
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        code = currency_code.strip().upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует!")
        wallet = Wallet(code, 0.0)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелёк по коду валюты или ``None``."""
        if not isinstance(currency_code, str):
            return None
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, float] | None = None,
    ) -> float:
        """Суммарная стоимость кошельков в ``base_currency``.

        Args:
            base_currency: Базовая валюта (по умолчанию USD).
            exchange_rates: Курсы вида ``{code: сколько USD стоит 1 единица}``.
                Если не передан — берутся резервные ``DEFAULT_RATES``.

        Raises:
            ValueError: Если базовая валюта неизвестна.
        """
        rates = exchange_rates or DEFAULT_RATES
        base = base_currency.strip().upper()
        if base not in rates:
            raise ValueError(f"Неизвестная базовая валюта '{base}'")

        base_rate = rates[base]
        total = 0.0
        for code, wallet in self._wallets.items():
            rate = rates.get(code)
            if rate is None:
                continue
            total += wallet.balance * rate / base_rate
        return total

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": w.balance} for code, w in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict, user: User | None = None) -> "Portfolio":
        wallets = {
            code: Wallet(code, w.get("balance", 0.0))
            for code, w in (data.get("wallets") or {}).items()
        }
        portfolio = cls(user_id=data["user_id"], wallets=wallets)
        portfolio._user = user
        return portfolio
