"""Пользовательские исключения доменной модели.

Все исключения несут готовое пользовательское сообщение в ``str(exc)``,
поэтому CLI может печатать их как есть.
"""


class ValutaTradeError(Exception):
    """Базовое исключение проекта."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств для операции."""

    def __init__(self, available: float, required: float, code: str):
        """
        Args:
            available: Доступная сумма.
            required: Требуемая сумма.
            code: Код валюты.
        """
        self.available = available
        self.required = required
        self.code = code
        message = (
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Сбой при обращении к внешнему API."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class UserNotFoundError(ValutaTradeError):
    """Пользователь не найден."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Пользователь '{username}' не найден")


class InvalidPasswordError(ValutaTradeError):
    """Неверный пароль."""

    def __init__(self, username: str | None = None):
        self.username = username
        super().__init__("Неверный пароль")


class UsernameAlreadyExistsError(ValutaTradeError):
    """Имя пользователя уже занято."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Имя пользователя '{username}' уже занято")


class StorageError(ValutaTradeError):
    """Ошибка чтения/записи хранилища."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка хранилища: {reason}")
