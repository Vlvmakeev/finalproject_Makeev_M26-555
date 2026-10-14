import json
import os
import tomllib
from typing import Any
from pathlib import Path


class SettingsLoader:
    """Singleton-загрузчик конфигурации проекта.

    Источник конфигурации (в порядке приоритета):
    1. Секция [tool.valutatrade] в pyproject.toml
    2. Значения по умолчанию (DEFAULTS)
    """

    try:
        import tomllib
    except ModuleNotFoundError:
        print("Модуль не найден")

    _instance: "SettingsLoader | None" = None

    DEFAULTS: dict[str, Any] = {
        # Пути к данным
        "USERS_FILE_PATH": "data/users.json",
        "PORTFOLIO_FILE_PATH": "data/portfolio.json",
        "RATES_FILE_PATH": "data/rates.json",
        "EXCHANGE_RATES_FILE_PATH": "data/exchange_rates.json",
        # Логи
        "LOG_FILE_PATH": "logs/actions.log",
        "LOG_LEVEL": "INFO",
        "LOG_MAX_BYTES": 1_048_576,   # 1 MiB
        "LOG_BACKUP_COUNT": 3,
        # Бизнес-параметры
        "RATES_TTL_SECONDS": 300,     # 5 минут
        "DEFAULT_BASE_CURRENCY": "USD",
        # Парсер
        "REQUEST_TIMEOUT": 10,
    }

    def __new__(cls, config_path: str | Path = "pyproject.toml") -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str | Path = "pyproject.toml") -> None:
        if self._initialized:
            return
        self._config_path = Path(config_path)
        self._settings: dict[str, Any] = dict(self.DEFAULTS)
        self._load()
        self._apply_env_overrides()
        self._initialized = True

    def _load(self) -> None:
        if not self._config_path.exists():
            return
        with self._config_path.open("rb") as file:
            data = tomllib.load(file)
        section = data.get("tool", {}).get("valutatrade", {})
        if isinstance(section, dict):
            self._settings.update(section)

    def _apply_env_overrides(self) -> None:
        """Переменные окружения вида VALUTATRADE_<KEY> переопределяют конфиг."""
        prefix = "VALUTATRADE_"
        for key in self._settings:
            env_key = prefix + key
            if env_key in os.environ:
                raw = os.environ[env_key]
                self._settings[key] = self._coerce(raw, self._settings[key])

    @staticmethod
    def _coerce(raw: str, example: Any) -> Any:
        """Приводит строку из env к типу значения по умолчанию."""
        if isinstance(example, bool):
            return raw.lower() in ("1", "true", "yes", "on")
        if isinstance(example, int):
            return int(raw)
        if isinstance(example, float):
            return float(raw)
        return raw

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def reload(self) -> None:
        """Перечитать конфигурацию."""
        self._settings = dict(self.DEFAULTS)
        self._load()
        self._apply_env_overrides()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._settings)



