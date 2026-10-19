"""Вспомогательные функции: работа с JSON, валидации и конвертации."""

from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.infra.database import get_database

MIN_CODE_LENGTH = 2
MAX_CODE_LENGTH = 5


def load_json(file_path: str, default: Any = None) -> Any:
    """Загружает данные из JSON-файла.

    Args:
        file_path: Путь к файлу или ключ конфигурации.
        default: Значение по умолчанию при отсутствии/пустом файле.

    Returns:
        Данные из файла или ``default`` (по умолчанию пустой список).
    """
    if default is None:
        default = []
    return get_database().load(file_path, default=default)


def save_json(file_path: str, data: Any) -> None:
    """Сохраняет данные в JSON-файл."""
    if data is None:
        return
    get_database().save(file_path, data)


def normalize_currency_code(code: str) -> str:
    """Нормализует код валюты к верхнему регистру.

    Raises:
        ValueError: Если код пуст или неверной длины.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не может быть пустым")

    normalized = code.strip().upper()
    if not (MIN_CODE_LENGTH <= len(normalized) <= MAX_CODE_LENGTH):
        raise ValueError(
            f"Код валюты должен быть {MIN_CODE_LENGTH}-{MAX_CODE_LENGTH} "
            f"символов, получено: {normalized}"
        )
    return normalized


def validate_currency_code(code: str) -> str:
    """Проверяет код валюты по реестру и возвращает его в верхнем регистре.

    Raises:
        CurrencyNotFoundError: Если валюта неизвестна.
    """
    normalized = normalize_currency_code(code)
    get_currency(normalized)
    return normalized


def validate_amount(amount: Any) -> float:
    """Проверяет, что сумма — положительное число.

    Raises:
        ValueError: Если сумма не число или не положительна.
    """
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("Сумма должна быть числом")
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
    return float(amount)


def get_next_id(items: list[dict], id_field: str = "user_id") -> int:
    """Возвращает следующий свободный идентификатор.

    Args:
        items: Список элементов.
        id_field: Имя поля с идентификатором.
    """
    if not items:
        return 1
    return max(item.get(id_field, 0) for item in items) + 1


def find_by(items: list[dict], **criteria: Any) -> dict | None:
    """Ищет первый элемент списка, совпадающий по всем критериям."""
    for item in items:
        if all(item.get(key) == value for key, value in criteria.items()):
            return item
    return None


def convert_amount(
    amount: float,
    from_code: str,
    to_code: str,
    rates_to_usd: dict[str, float],
) -> float:
    """Конвертирует сумму между валютами через их курс к USD.

    Args:
        amount: Сумма в исходной валюте.
        from_code: Код исходной валюты.
        to_code: Код целевой валюты.
        rates_to_usd: Курсы вида ``{code: сколько USD стоит 1 единица}``.

    Raises:
        CurrencyNotFoundError: Если для одной из валют нет курса.
    """
    from_rate = rates_to_usd.get(from_code.upper())
    to_rate = rates_to_usd.get(to_code.upper())
    if from_rate is None or to_rate is None:
        missing = from_code if from_rate is None else to_code
        from valutatrade_hub.core.exceptions import CurrencyNotFoundError

        raise CurrencyNotFoundError(missing)
    return amount * from_rate / to_rate
