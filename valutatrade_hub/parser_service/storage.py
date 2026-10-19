"""Операции чтения/записи файлов курсов Parser Service."""

import json
import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger("valutatrade_hub.parser_service.storage")


class RatesStorage:
    """Хранилище курсов.

    Управляет двумя файлами:

    * ``rates.json`` — текущий кеш курсов для Core Service;
    * ``exchange_rates.json`` — история измерений.
    """

    def __init__(self, config: Any):
        """
        Args:
            config: Конфигурация Parser Service (``ParserConfig``).
        """
        self.config = config

    def _describe_pair(self, pair_key: str) -> str:
        """Возвращает название источника для пары по её коду."""
        from_code = pair_key.split("_")[0]
        if from_code in self.config.CRYPTO_CURRENCIES:
            return "CoinGecko"
        return "ExchangeRate-API"

    def save_rates_cache(self, rates: dict[str, float], last_refresh: str) -> None:
        """Сохраняет кеш курсов в ``rates.json`` атомарно (tmp → rename).

        Args:
            rates: Словарь ``{"BTC_USD": 59337.21}``.
            last_refresh: Время последнего обновления (ISO-UTC).
        """
        pairs = {
            pair_key: {
                "rate": rate,
                "updated_at": last_refresh,
                "source": self._describe_pair(pair_key),
            }
            for pair_key, rate in rates.items()
        }
        data = {
            "pairs": pairs,
            "source": "ParserService",
            "last_refresh": last_refresh,
        }
        self._atomic_write(self.config.RATES_FILE_PATH, data)
        logger.info("Saved %d rates to %s", len(pairs), self.config.RATES_FILE_PATH)

    def load_rates_cache(self) -> dict[str, Any]:
        """Загружает кеш курсов; при ошибке возвращает пустую структуру."""
        data = self._read(self.config.RATES_FILE_PATH)
        if isinstance(data, dict):
            return data
        return {"pairs": {}, "last_refresh": ""}

    def save_exchange_history(self, records: list[dict]) -> None:
        """Добавляет записи в историю ``exchange_rates.json``."""
        history = self.load_exchange_history()
        history.extend(records)
        self._atomic_write(self.config.HISTORY_FILE_PATH, history)

    def load_exchange_history(self) -> list[dict]:
        """Загружает историю измерений."""
        data = self._read(self.config.HISTORY_FILE_PATH)
        return data if isinstance(data, list) else []

    def build_history_record(
        self,
        pair_key: str,
        rate: float,
        timestamp: str,
        meta: dict | None = None,
    ) -> dict:
        """Собирает одну запись истории с уникальным id.

        ``id = <FROM><TO><ISO-UTC timestamp>``.
        """
        from_code, _, to_code = pair_key.partition("_")
        record: dict[str, Any] = {
            "id": f"{from_code}_{to_code}_{timestamp}",
            "from_currency": from_code,
            "to_currency": to_code,
            "rate": rate,
            "timestamp": timestamp,
            "source": self._describe_pair(pair_key),
        }
        if meta:
            record["meta"] = meta
        return record

    def get_rate_history(self, pair_key: str, limit: int = 10) -> list[dict]:
        """Возвращает последние ``limit`` записей истории для пары."""
        from_code, _, to_code = pair_key.partition("_")
        history = [
            record
            for record in self.load_exchange_history()
            if record.get("from_currency") == from_code
            and record.get("to_currency") == to_code
        ]
        return history[-limit:]

    def _read(self, path: str) -> Any:
        """Читает JSON или возвращает ``None`` при отсутствии/ошибке."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as file:
                content = file.read().strip()
                return json.loads(content) if content else None
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", path, exc)
            return None

    def _atomic_write(self, path: str, data: Any) -> None:
        """Атомарно пишет JSON через временный файл."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temp_path = f"{path}.{uuid4().hex}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
        except OSError as exc:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error("Failed to write %s: %s", path, exc)
            raise

    @staticmethod
    def utc_timestamp() -> str:
        """Возвращает текущее время в ISO-UTC с суффиксом ``Z``."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
