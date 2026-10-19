"""Планировщик периодического обновления курсов."""

import logging
import threading
import time
from typing import Optional

from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger("valutatrade_hub.parser_service.scheduler")

DEFAULT_INTERVAL_SECONDS = 300


class UpdateScheduler:
    """Периодически запускает обновление курсов в фоновом потоке или разово."""

    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: RatesStorage,
        config: ParserConfig,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    ):
        """
        Args:
            clients: Список API-клиентов.
            storage: Хранилище курсов.
            config: Конфигурация Parser Service.
            interval_seconds: Интервал между обновлениями в секундах.
        """
        self.updater = RatesUpdater(clients, storage, config)
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_once(self, source: Optional[str] = None) -> dict:
        """Выполняет одно обновление."""
        return self.updater.run_update(source=source)

    def _loop(self, source: Optional[str]) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once(source=source)
            except Exception as exc:  # noqa: BLE001 - планировщик не должен падать
                logger.error("Scheduled update failed: %s", exc)
            self._stop_event.wait(self.interval_seconds)

    def start(self, source: Optional[str] = None) -> None:
        """Запускает фоновое периодическое обновление."""
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            args=(source,),
            daemon=True,
        )
        self._thread.start()
        logger.info("Scheduler started (interval=%ss)", self.interval_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        """Останавливает фоновое обновление."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("Scheduler stopped")


def run_scheduler(
    clients: list[BaseApiClient],
    storage: RatesStorage,
    config: ParserConfig,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    source: Optional[str] = None,
) -> None:
    """Блокирующая функция запуска планировщика (для ручного запуска)."""
    scheduler = UpdateScheduler(clients, storage, config, interval_seconds)
    scheduler.start(source=source)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
