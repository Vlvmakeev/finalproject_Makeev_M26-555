class InsufficientFundsError(Exception):
    """
    Исключение: недостаточно средств для операции

    Наследуется от Exception
    """

    def __init__(self, available: float, required: float, code: str):
        """
        Args:
        :param available: Доступная сумма
        :param required: Требуемая сумма
        :param code: Код валюты
        """
        self.message = f"Недостаточно средств: доступно {available:.4f} {code}, требуется {required:.4f} {code}"

        super().__init__(self.message)

class CurrencyNitFoundError(Exception):
    """Исключение: валюта не найдена."""

    def __init__(self, code: str):
        self.message = f"Неизвестная валюта '{code}'"
        super().__init__(self.message)

class ApiRequestError(Exception):
    """Исключение: ошибка при обращении к внешнему API"""

    def __init__(self, reason: str):
        self.message = f"Ошибка при обращении к внешнему API: {reason}"
        super().__init__(self.message)


class UserNotFoundError(Exception):
    """Исключение: пользователь на найден"""

    def __init__(self, username: str):
        self.message = f"Пользователь '{username}' не найден"
        super().__init__(self.message)

class InvalidPasswordError(Exception):
    """Исключение: неверный пароль"""

    def __int__(self):
        self.message = "Неверный пароль"
        super().__init__(self.message)

class UsernameAlreadyExistsError(Exception):
    """Исключение: имя пользователя уже занято"""

    def __init__(self, username: str):
        self.message = f"Имя пользователя '{username}' уже занято"
        super().__init__(self.message)