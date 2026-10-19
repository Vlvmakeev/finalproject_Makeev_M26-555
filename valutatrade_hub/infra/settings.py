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
            "data_dir": "data",
            "users_file": "data/users.json",
            "portfolios_file": "data/portfolios.json",
            "rates_file": "data/rates.json",
            "log_dir": "logs",
            "log_file": "logs/actions.log",
            "log_level": "INFO",
            "rates_ttl_seconds": 60,
            "default_base_currency": "USD"
        }

        self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """Получение конфигурации по ключу"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Устанавливает значение конфигурации"""
        self._config[key] = value
