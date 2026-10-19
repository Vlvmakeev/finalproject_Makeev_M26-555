from typing import Any


class SettingsLoader:
    """Singleton-загрузчик конфигурации проекта и ее кэширования"""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __int__(self):
        if self._initialized:
            return

        self._config = {
            "DATA_DIR": "data",
            "USERS_FILE": "data/users.json",
            "PORTFOLIOS_FILE": "data/portfolios.json",
            "RATES_FILE": "data/rates.json",
            "LOG_DIR": "logs",
            "LOG_FILE": "logs/actions.log",
            "LOG_LEVEL": "INFO",
            "RATES_TTL_SECONDS": 60,
            "DEFAULT_BASE_CURRENCY": "USD"
        }

        self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """Получение конфигурации по ключу"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Устанавливает значение конфигурации"""
        self._config[key] = value
