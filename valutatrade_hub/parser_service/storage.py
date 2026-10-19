import json
import logging
import os
from typing import Dict, List

from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger(__name__)

class RatesStorage:
    """
        Хранилище для курсов валют.

        Управляет двумя файлами:
        - rates.json — текущий кеш курсов (для Core Service)
        - exchange_rates.json — история всех обновлений
        """

    def __init__(self, config: ParserConfig):
        """
        Инициализация хранилища.

        Args:
            config: Конфигурация Parser Service
        """
        self.config = config

    def save_rates_cache(self, rates: Dict, last_refresh: str):
        """
        Сохраняет кеш курсов в rates.json.

        Использует атомарную запись через временный файл,
        чтобы избежать повреждения данных при сбое.

        Args:
            rates: Словарь с курсами
            last_refresh: Время последнего обновления
        """
        data = {
            "pairs": rates,
            "last_refresh": last_refresh,
            "source": "ParserService"
        }

        # Создаем директорию, если её нет
        dir_path = os.path.dirname(self.config.RATES_FILE_PATH)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Атомарная запись: пишем во временный файл, потом переименовываем
        temp_path = self.config.RATES_FILE_PATH + ".tmp"

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # os.replace — атомарная операция переименования
            os.replace(temp_path, self.config.RATES_FILE_PATH)

            logger.info(f"Saved {len(rates)} rates to {self.config.RATES_FILE_PATH}")

        except Exception as e:
            # Удаляем временный файл в случае ошибки
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Failed to save rates: {e}")
            raise

    def load_rates_cache(self) -> Dict:
        """
        Загружает кеш курсов из rates.json.

        Returns:
            Словарь с курсами или пустая структура
        """
        if not os.path.exists(self.config.RATES_FILE_PATH):
            return {"pairs": {}, "last_refresh": ""}

        try:
            with open(self.config.RATES_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {"pairs": {}, "last_refresh": ""}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load rates: {e}")
            return {"pairs": {}, "last_refresh": ""}

    def save_exchange_history(self, records: List[Dict]):
        """
        Сохраняет записи в историю курсов (exchange_rates.json).

        Каждая запись представляет собой одно обновление курсов.

        Args:
            records: Список записей с курсами и метаданными
        """
        # Загружаем существующую историю
        history = self.load_exchange_history()

        # Добавляем новые записи
        history.extend(records)

        # Создаем директорию, если её нет
        dir_path = os.path.dirname(self.config.HISTORY_FILE_PATH)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Атомарная запись
        temp_path = self.config.HISTORY_FILE_PATH + ".tmp"

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            os.replace(temp_path, self.config.HISTORY_FILE_PATH)

        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Failed to save exchange history: {e}")
            raise

    def load_exchange_history(self) -> List[Dict]:
        """
        Загружает историю курсов из exchange_rates.json.

        Returns:
            Список записей с курсами
        """
        if not os.path.exists(self.config.HISTORY_FILE_PATH):
            return []

        try:
            with open(self.config.HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load exchange history: {e}")
            return []

    def get_rate_history(self, pair_key: str, limit: int = 10) -> List[Dict]:
        """
        Возвращает историю курсов для конкретной пары.

        Args:
            pair_key: Ключ пары (например, "BTC_USD")
            limit: Максимальное количество записей

        Returns:
            Список записей с курсами
        """
        history = self.load_exchange_history()

        # Фильтруем записи по паре
        pair_history = [
            record for record in history
            if record.get("from_currency") == pair_key.split("_")[0]
               and record.get("to_currency") == pair_key.split("_")[1]
        ]

        # Возвращаем последние N записей
        return pair_history[-limit:]