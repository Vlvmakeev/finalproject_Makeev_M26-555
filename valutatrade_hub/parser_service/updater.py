import logging
from datetime import datetime
from typing import Dict, List, Optional

from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger(__name__)


class RatesUpdater:
    """
    Координатор процесса обновления курсов.

    Отвечает за:
    - Опрос всех API-клиентов
    - Объединение результатов
    - Сохранение в кеш и историю
    """

    def __init__(self, clients: List[BaseApiClient], storage: RatesStorage, config: ParserConfig):
        """
        Инициализация апдейтера.

        Args:
            clients: Список API клиентов
            storage: Хранилище данных
            config: Конфигурация
        """
        self.clients = clients
        self.storage = storage
        self.config = config

    def run_update(self, source: Optional[str] = None) -> Dict:
        """
        Запускает процесс обновления курсов.

        Опрашивает всех клиентов, объединяет результаты и сохраняет.
        Если один клиент падает, продолжаем с остальными.

        Args:
            source: Опциональный фильтр по источнику
                   ("coingecko" или "exchangerate")

        Returns:
            Словарь с результатами обновления
        """
        logger.info("Starting rates update...")
        print("INFO: Starting rates update...")

        all_rates = {}
        errors = []
        success_count = 0

        for client in self.clients:
            try:
                # Проверяем фильтр по источнику
                client_name = type(client).__name__
                if source:
                    source_lower = source.lower()
                    if source_lower == "coingecko" and "CoinGecko" not in client_name:
                        continue
                    if source_lower == "exchangerate" and "ExchangeRate" not in client_name:
                        continue

                # Получаем курсы
                rates = client.fetch_rates()

                if rates:
                    all_rates.update(rates)
                    success_count += len(rates)
                    print(f"INFO: Fetching from {client.name}... OK ({len(rates)} rates)")

            except Exception as e:
                error_msg = f"Failed to fetch from {client.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                print(f"ERROR: {error_msg}")

        # Сохраняем результаты, если что-то получили
        last_refresh = datetime.now().isoformat()

        if all_rates:
            # Сохраняем кеш
            self.storage.save_rates_cache(all_rates, last_refresh)
            print(f"INFO: Writing {len(all_rates)} rates to {self.config.RATES_FILE_PATH}...")

            # Сохраняем в историю
            history_records = []
            for pair_key, rate in all_rates.items():
                parts = pair_key.split("_")
                record = {
                    "id": f"{pair_key}_{last_refresh}",
                    "from_currency": parts[0],
                    "to_currency": parts[1],
                    "rate": rate,
                    "timestamp": last_refresh,
                    "source": self._get_source_for_pair(pair_key)
                }
                history_records.append(record)

            self.storage.save_exchange_history(history_records)
        else:
            logger.warning("No rates fetched from any source")

        # Формируем результат
        result = {
            "success": len(errors) == 0,
            "rates_count": len(all_rates),
            "errors": errors,
            "last_refresh": last_refresh
        }

        # Выводим итоговое сообщение
        if errors:
            print(f"Update completed with errors. Check logs for details.")
        else:
            print(f"Update successful. Total rates updated: {success_count}. Last refresh: {last_refresh}")

        logger.info(f"Update completed. Rates: {len(all_rates)}, Errors: {len(errors)}")

        return result

    def _get_source_for_pair(self, pair_key: str) -> str:
        """
        Определяет источник для пары валют.

        Криптовалюты → CoinGecko
        Фиатные → ExchangeRate-API

        Args:
            pair_key: Ключ пары (например, "BTC_USD")

        Returns:
            str: Название источника
        """
        from_code = pair_key.split("_")[0]

        if from_code in self.config.CRYPTO_CURRENCIES:
            return "CoinGecko"
        else:
            return "ExchangeRate-API"