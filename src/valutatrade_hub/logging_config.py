"""Настройка логирования проекта (формат, уровень, ротация)."""

import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5

_configured = False


def setup_logging(level: str | None = None) -> logging.Logger:
    """Настраивает корневой логгер с файловой ротацией и консолью.

    Args:
        level: Уровень логирования (по умолчанию из конфигурации).

    Returns:
        Корневой логгер проекта.
    """
    global _configured

    settings = SettingsLoader()
    log_path = settings.resolve_path("LOG_FILE")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_level = (level or settings.get("LOG_LEVEL", "INFO")).upper()

    logger = logging.getLogger("valutatrade_hub")
    logger.setLevel(getattr(logging, resolved_level, logging.INFO))

    if _configured:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console_handler)

    logger.propagate = False
    _configured = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Возвращает дочерний логгер проекта с настроенными обработчиками."""
    setup_logging()
    return logging.getLogger(f"valutatrade_hub.{name}")


class suppress_console:
    """Контекстный менеджер: временно глушит консольный вывод логов.

    Файловые обработчики продолжают работать, поэтому диагностика
    сохраняется в ``logs/actions.log``. Используется для внутренних
    операций, которые не должны засорять вывод CLI (например, попытка
    обновить курс внутри ``get-rate``).
    """

    def __init__(self, level: int = logging.CRITICAL):
        self._level = level
        self._handlers: list[tuple[logging.Handler, int]] = []

    def __enter__(self) -> "suppress_console":
        logger = logging.getLogger("valutatrade_hub")
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                self._handlers.append((handler, handler.level))
                handler.setLevel(self._level)
        return self

    def __exit__(self, *exc_info: object) -> None:
        for handler, level in self._handlers:
            handler.setLevel(level)
        self._handlers.clear()
