"""Singleton-загрузчик конфигурации проекта."""

import os
import tomllib
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "DATA_DIR": "data",
    "USERS_FILE": "data/users.json",
    "PORTFOLIOS_FILE": "data/portfolios.json",
    "RATES_FILE": "data/rates.json",
    "EXCHANGE_RATES_FILE": "data/exchange_rates.json",
    "LOG_DIR": "logs",
    "LOG_FILE": "logs/actions.log",
    "LOG_LEVEL": "INFO",
    "RATES_TTL_SECONDS": 300,
    "DEFAULT_BASE_CURRENCY": "USD",
    "REQUEST_TIMEOUT": 10,
}

#: Карта ключей из [tool.valutatrade] в имена, используемые в коде.
_CONFIG_ALIASES: dict[str, str] = {
    "USERS_FILE_PATH": "USERS_FILE",
    "PORTFOLIOS_FILE_PATH": "PORTFOLIOS_FILE",
    "RATES_FILE_PATH": "RATES_FILE",
    "EXCHANGE_RATES_FILE_PATH": "EXCHANGE_RATES_FILE",
    "LOG_FILE_PATH": "LOG_FILE",
}


class SettingsLoader:
    """Единственный экземпляр конфигурации приложения.

    Реализован через ``__new__`` — для синглтона без наследования это самый
    простой и читаемый способ: не нужен отдельный метакласс, а ленивая
    инициализация выполняется один раз при первом обращении.
    """

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._config: dict[str, Any] = dict(DEFAULT_CONFIG)
        self._project_root = self._find_project_root()
        self._load_from_pyproject()
        self._initialized = True

    @staticmethod
    def _find_project_root() -> Path:
        """Ищет корень проекта (каталог с pyproject.toml) вверх по дереву."""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "pyproject.toml").exists():
                return parent
        return Path.cwd()

    def _load_from_pyproject(self) -> None:
        """Читает секцию ``[tool.valutatrade]`` и переносит её в конфиг."""
        pyproject = self._project_root / "pyproject.toml"
        if not pyproject.exists():
            return

        try:
            with pyproject.open("rb") as file:
                data = tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError):
            return

        section = data.get("tool", {}).get("valutatrade", {})
        for key, value in section.items():
            self._config[_CONFIG_ALIASES.get(key, key)] = value

    @property
    def project_root(self) -> Path:
        return self._project_root

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение конфигурации по ключу."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Устанавливает значение конфигурации."""
        self._config[key] = value

    def reload(self) -> None:
        """Перезагружает конфигурацию из pyproject заново."""
        self._config = dict(DEFAULT_CONFIG)
        self._load_from_pyproject()

    def resolve_path(self, key: str) -> Path:
        """Возвращает абсолютный путь к файлу данных из конфигурации."""
        raw = self.get(key)
        if raw is None:
            raise KeyError(f"Путь '{key}' не задан в конфигурации")
        path = Path(raw)
        if not path.is_absolute():
            path = self._project_root / path
        return path

    def ensure_directories(self) -> None:
        """Создаёт каталоги для данных и логов."""
        self.resolve_path("USERS_FILE").parent.mkdir(parents=True, exist_ok=True)
        self.resolve_path("LOG_FILE").parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _reset(cls) -> None:
        """Сбрасывает синглтон (для тестов)."""
        cls._instance = None


def get_settings() -> "SettingsLoader":
    """Удобный доступ к единственному экземпляру настроек."""
    return SettingsLoader()


def _configure_api_key_from_env() -> None:
    """Загружает ключи из окружения, если они заданы в ``.env``."""
    env_path = SettingsLoader().project_root / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


_configure_api_key_from_env()
