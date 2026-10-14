import hashlib
import secrets
from datetime import datetime


class User:
    """Пользователь приложения.

    Хранит учетные данные, хеш пароля и соль.
    Пароль в открытом виде не хранится нигде.
    """
    _user_id: int
    _username: str
    _hashed_password: str
    _salt: str
    _registration_date: datetime

    def __init__(
            self,
            user_id: int,
            username: str,
            hashed_password: str,
            salt: str,
            registration_date: datetime
        ):
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
    def username(self, value: str):
        if not value or not value.strip():
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
    def _hash(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        if not username or not username.strip():
            raise ValueError("Пароль должен быть не короче 4-х символов")
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4-х символов")

        salt = secrets.token_hex(8)
        hashed = cls._hash(password, salt)
        return cls(user_id=user_id, username=username, hashed_password=hashed, salt=salt, registration_date=datetime.now())

    def get_user_info(self) -> dict:
        """Информация о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не менее 4-х символов")
        self._hashed_password = self._hash(new_password, self.salt)

    def verify_password(self, password: str) -> bool:
        return self._hash(password, self.salt) == self._hashed_password

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
            registration_date=datetime.fromisoformat(data["registration_date"])
        )



class Wallet:
    """Колшелек пользователя для одной конкретной валюты"""
    _currency_code: str
    _balance: float

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self._currency_code = currency_code.upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @balance.setter
    def balance(self, amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Баланс должен быть числом")
        elif amount < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(amount)

    def get_balance_info(self=None):
        print(f"Валюта: {self.currency_code}")
        print(f"Баланс: {self._balance}")

    def deposit(amount: float, self=None) -> float:
        self._check_amount(amount)
        if amount > self._balance:
            raise ValueError("Сумма превышает остаток на балансе")
        self._balance += amount

    def withdraw(amount: float, self=None) -> float:
        self._check_amount(amount)
        if amount > self._balance:
            raise ValueError(
                f"недостаточно средств: доступно {self._balance} "
                f"{self._curr}"
            )
        self._balance -= amount

    @staticmethod
    def _check_amount(self, amount: float):
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Баланс должен быть числом")
        elif amount < 0:
            raise ValueError("Сумма должна быть положительным числом")

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        return cls(
            currency_code=data["currency_code"],
            balance=data.get("balance", 0.0)
        )



class Portfolio:

    EXCHANGE_RATES = {
        "USD": 1.0,
        "EUR": 1.08,
        "BTC": 60000.0,
        "ETH": 3000.0
    }

    _user_id: int
    _wallets: dict[str, Wallet]

    def __init__(self,
                 user_id: int,
                 user=None,
                 wallets: dict[str, Wallet] | None = None
                 ):
        self._user_id = user_id
        self._user = user
        self._wallets: dict[str, Wallet] = wallets or {}

    @property
    def user(self) -> User | None:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)

    @property
    def user_id(self) -> int:
        return self._user_id


    def add_currency(self, currency_code: str):
        """Создается новый кошелек, если такого еще нет."""
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError(f"Кошелек {code} уже существует!")
        wallet = Wallet(currency_code, 0.0)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        return self._wallets.get(currency_code.upper())


    def get_total_value(self, exchange_rates: dict[str, float] | None = None, base_currency='USD') -> float:
        """Суммарная стоимость в base_currency.

        exchange_rates = {code: сколько единиц кода в 1 USD}.
        Если не передали - берем фиктивные {заглушка до Parser Service}.
        """
        rates = exchange_rates or DEFAULT_RATES
        base = base_currency.upper()
        if base not in rates:
            raise ValueError(f"Неизвестная базовая валюта '{base}'")

        base_rate = rates[base]
        total = 0.0
        for code, wallet in self._wallets.items():
            if code not in rates:
                continue
            total += wallet.balance * rates[code] / base_rate
        return total

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "wallets": {
                code: {"balance": w.balance} for code, w in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict, user: User | None = None) -> "Portfolio":
        wallets = {
            code: Wallet(code, w.get("balance", 0.0))
            for code, w in data.get("wallets").items()
        }
        return cls(user_id=data["user_id"], wallets=wallets, user=user)



DEFAULT_RATES: dict[str, float] = {
        "USD": 1.0,
        "EUR": 0.927,
        "GBP": 0.809,
        "RUB": 98.45,
        "BTC": 1 / 59337.21,
        "ETH": 1 / 3720.0,
        "SOL": 1 / 145.12
    }

            