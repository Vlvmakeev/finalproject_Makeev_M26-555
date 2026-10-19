import json
import os.path
from typing import Any, Dict, List


def load_json(file_path):
    """
    Загружает данные из JSON-фалы
    Args:
        file_path: Путь к файлу
    Returns:
        Данные из файла или пустой список при несуществующем файле
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if data is not None else []
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return []

def save_json(file_path: str, data: Any):
    """
    Сохраняет данные в JSON-файл
    Args:
        file_path: Путь к файлу
        data: Данные для сохранения
    """
    if data is None:
        print("Отсутствют данные для сохранения")
        return

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except(FileNotFoundError, json.JSONDecodeError, IOError):
        print("Ошибка: файл не найден!")

def validate_currency_code(code: str) -> str:
    """Валидирует и нормализует код валюты
     Args:
        code: Код валюты

    Returns:
        Код валюты в верхнем регистре

    Raises:
        ValueError: Если код некорректен
    """
    if not code or not isinstance(code, str):
        raise ValueError("Код валюты не может быть пустым")

    code = code.upper().strip()

    if not (2 <= len(code) <= 5):
        raise ValueError(f"Код валюты должен быть 2-5 символов, получено: {code}")

    return code

def validate_amount(amount: float) -> float:
    """Валидация суммы
    Args:
        amount: Сумма для проверки

    Returns:
        Сумма как float

    Raises:
        ValueError: если сумма некорректна
    """
    if not isinstance(amount, (int, float)):
        raise ValueError("Сумма должна быть числом")

    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")

    return float(amount)

def get_next_id(items: List[Dict], id_field: str = "user_id") -> int:
    """Получить следующий достпный идентификатор для пользователя
       Args:
           items: Список элементов
           id_field: Название поля с ID

       Returns:
           Следующий доступный id
       """
    if not items:
        return 1

    max_id = max(item.get(id_field) for item in items)
    return max_id + 1