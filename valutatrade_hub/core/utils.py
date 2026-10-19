import json
import os.path


def load_json(file_path):
    """
    Загружает данные из JSON-фалы
    Args:
        file_path: Путь к файлу
    Returns:
        Данные из файла или пустой список
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if data is not None else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(file_path, data):
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
    except(FileNotFoundError, json.JSONDecodeError):
        print("Ошибка: файл не найден!")
