"""Координатор обновления курсов из всех источников."""

import logging
from typing import Any, Optional

from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger("valutatrade_hub.parser_service.updater")

#: Соответствие имени источника и фрагмента имени класса клиента.
_SOURCE_MATCHERS = {
    "coingecko": "CoinGecko",
    "exchangerate": "ExchangeRate",
}


class RatesUpdater:
    """Опрашивает API-клиентов, объединяет и сохраняет курсы."""

    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: RatesStorage,
        config: ParserConfig,
    ):
        """
        Args:
            clients: Список API-клиентов.
            storage: Хранилище курсов.
            config: Конфигурация Parser Service.
        """
        self.clients = clients
        self.storage = storage
        self.config = config

    def run_update(
        self, source: Optional[str] = None, quiet: bool = False
    ) -> dict[str, Any]:
        """Запускает обновление курсов.

        Падение одного клиента не прерывает обновление остальных.

        Args:
            source: Опциональный фильтр ("coingecko"/"exchangerate").
            quiet: Не выводить прогресс в stdout (для внутренних вызовов).

        Returns:
            Сводка: ``success``, ``rates_count``, ``errors``, ``last_refresh``.
        """

        def _echo(message: str) -> None:
            if not quiet:
                print(message)

        _echo("INFO: Starting rates update...")
        logger.info("Starting rates update...")

        all_rates: dict[str, float] = {}
        errors: list[str] = []

        for client in self.clients:
            if not self._matches_source(client, source):
                continue
            try:
                rates = client.fetch_rates()
            except Exception as exc:  # noqa: BLE001 - изоляция источников
                message = f"Failed to fetch from {client.name}: {exc}"
                logger.error(message)
                errors.append(message)
                _echo(f"ERROR: {message}")
                continue

            if rates:
                all_rates.update(rates)
                _echo(f"INFO: Fetching from {client.name}... OK ({len(rates)} rates)")

        last_refresh = self.storage.utc_timestamp()

        if all_rates:
            self.storage.save_rates_cache(all_rates, last_refresh)
            _echo(
                f"INFO: Writing {len(all_rates)} rates to "
                f"{self.config.RATES_FILE_PATH}..."
            )
            records = [
                self.storage.build_history_record(pair_key, rate, last_refresh)
                for pair_key, rate in all_rates.items()
            ]
            self.storage.save_exchange_history(records)
        else:
            logger.warning("No rates fetched from any source")
            _echo("WARNING: No rates fetched from any source")

        result = {
            "success": not errors,
            "rates_count": len(all_rates),
            "errors": errors,
            "last_refresh": last_refresh,
        }

        if errors:
            _echo("Update completed with errors. Check logs/actions.log for details.")
        else:
            _echo(
                f"Update successful. Total rates updated: {len(all_rates)}. "
                f"Last refresh: {last_refresh}"
            )

        logger.info(
            "Update completed. Rates: %d, Errors: %d",
            len(all_rates),
            len(errors),
        )
        return result

    @staticmethod
    def _matches_source(client: BaseApiClient, source: Optional[str]) -> bool:
        """Проверяет, соответствует ли клиент фильтру по источнику."""
        if not source:
            return True
        matcher = _SOURCE_MATCHERS.get(source.lower())
        if matcher is None:
            return True
        return matcher in type(client).__name__
