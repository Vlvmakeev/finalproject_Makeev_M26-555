from datetime import datetime
import secrets
import datetime
from typing import Dict

from valutatrade_hub.core.exceptions import UsernameAlreadyExistsError, UserNotFoundError, InvalidPasswordError, \
    InsufficientFundsError
from valutatrade_hub.core.models import User, Wallet, Portfolio
from valutatrade_hub.core.utils import load_json, get_next_id, save_json, validate_currency_code, validate_amount
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.core.decorators import log_action



@log_action(verbose=True)
def register(username: str, password: str) -> User:
    """
    Создание нового пользователя и пустого портфеля
    Args
        username: никнейм создаваемого пользователя
        password: пароль создаваемого пользователя
    Returns:
        объект User
    Raises:
        UsernameAlreadyExistsError: Если имя пользователя уже занято
        ValueError: Если пароль слишком короткий
    """

    settings = SettingsLoader()
    users_path = settings.get("USERS_FILE")
    portfolio_path = settings.get("PORTFOLIOS_FILE")

    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4-х символов")

    users = load_json(users_path)

    for user_data in users:
        if user_data["username"] == username:
            raise UsernameAlreadyExistsError(username)

    user_id = get_next_id(users)
    salt = secrets.token_hex(8)
    hashed_password = User._hash_password(password, salt)

    user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
        registration_date=datetime.now(),
    )

    users.append(user.to_dict())
    save_json(users_path, users)

    portfolios = load_json(portfolio_path)
    portfolio = Portfolio(user_id)
    portfolios.append(portfolio.to_dict())
    save_json(portfolio_path, portfolios)

    return user

@log_action(verbose=True)
def login(username: str, password: str) -> User:
    """Аутентификация пльзователя в системе
     Args
        username: никнейм создаваемого пользователя
        password: пароль создаваемого пользователя

    Returns:
        Объект User, если вход успешен

    Raises:
        UserNotFoundError: Если пользователь не найден
        InvalidPasswordError: Если пароль неверный
     """

    settings = SettingsLoader()
    users_path = settings.get("USERS_FILE")

    users = load_json(users_path)

    user_data = None
    for user in users:
        if user.get("username") == username:
            user_data = user
            break

    if user_data is None:
        raise UserNotFoundError(username)

    user = User.from_dict(user_data)

    if not user.verify_password(password):
        raise InvalidPasswordError(password)

    return user

def get_portfolio(user_id: int) -> Portfolio:
    """Получает портфель пользователя
     Args
        username: никнейм создаваемого пользователя
        password: пароль создаваемого пользователя

    Args:
        user_id: Идентификатор пользователя

    Returns:
        Объект Portfolio
    """
    settings = SettingsLoader()
    portfolio_path = settings.get("PORTFOLIOS_FILE")

    portfolios = load_json(portfolio_path)

    for portfolio in portfolios:
        if portfolio.get("user_id") == user_id:
            return Portfolio.from_dict(portfolio)

    portfolio = Portfolio(user_id)
    portfolios.append(portfolio.to_dict())
    save_json(portfolio_path, portfolios)
    return portfolio

def buy(user_id: int, currency_code: str, amount: float) -> Dict:
    """Покупка валюты
     Args:
        user_id: Идентификатор пользователя
        currency_code: Код покупаемой валюты
        amount: Количество покупаемой валюты

    Returns:
        Словарь с информацией о покупке
    """

    settings = SettingsLoader()
    portfolio_path = settings.get("PORTFOLIOS_FILE")

    currency_code = validate_currency_code(currency_code)
    amount = validate_amount(amount)

    portfolio = get_portfolio(user_id)

    wallet = portfolio.add_currency(currency_code)

    wallet.deposit(amount)

    portfolios = load_json(portfolio_path)
    for i, p in enumerate(portfolios):
        if p.get("user_id") == user_id:
            portfolios[i] = portfolio.to_dict()
            break

    save_json(portfolio_path, portfolios)

    return {
        "currency": currency_code,
        "amount": amount
    }

@log_action(verbose=True)
def sell(user_id: int, currency_code: str, amount: float) -> Dict:
    """
        Продает валюту.

        Args:
            user_id: Идентификатор пользователя
            currency_code: Код продаваемой валюты
            amount: Количество продаваемой валюты

        Returns:
            Словарь с информацией о продаже

        Raises:
            InsufficientFundsError: Если недостаточно средств
    """
    settings = SettingsLoader()
    portfolio_path = settings.get("PORTFOLIOS_FILE")

    currency_code = validate_currency_code(currency_code)
    amount = validate_amount(amount)

    portfolio = get_portfolio(user_id)

    wallet = portfolio.get_wallet(currency_code)

    if wallet is None:
        raise ValueError(f"У вас нет кошелька '{currency_code}'")

    wallet.withdraw(amount)

    portfolios = load_json(portfolio_path)
    for i, p in enumerate(portfolios):
        if p.get("user_id") == user_id:
            portfolios[i] = portfolio.to_dict()
            break

    save_json(portfolio_path, portfolios)

    return {
        "currency": currency_code,
        "amount": amount
    }

