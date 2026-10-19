"""Singleton-менеджер доступа к JSON-хранилищу.

Реализован через ``__new__``: единый экземпляр даёт общую точку
чтения/записи и позволяет кешировать настройки путей.
"""

import json
import os
from pathlib import Path
from typing import Any

from valutatrade_hub.core.exceptions import StorageError
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Абстракция над JSON-файлами данных (users, portfolios, rates)."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._settings = SettingsLoader()
            cls._instance = instance
        return cls._instance

    @property
    def settings(self) -> SettingsLoader:
        return self._settings

    def _resolve(self, key_or_path: str) -> Path:
        """Принимает ключ конфигурации или путь и возвращает абсолютный путь."""
        known = {
            "USERS_FILE",
            "PORTFOLIOS_FILE",
            "RATES_FILE",
            "EXCHANGE_RATES_FILE",
        }
        if key_or_path in known:
            return self._settings.resolve_path(key_or_path)
        path = Path(key_or_path)
        if not path.is_absolute():
            path = self._settings.project_root / path
        return path

    def load(self, key_or_path: str, default: Any = None) -> Any:
        """Читает JSON из файла; при отсутствии возвращает ``default``."""
        path = self._resolve(key_or_path)
        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                content = file.read().strip()
                if not content:
                    return default
                data = json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"не удалось прочитать {path.name}: {exc}") from exc

        return data if data is not None else default

    def save(self, key_or_path: str, data: Any) -> None:
        """Атомарно записывает данные в JSON-файл (tmp → rename)."""
        path = self._resolve(key_or_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")

        try:
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            os.replace(temp_path, path)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise StorageError(f"не удалось записать {path.name}: {exc}") from exc

    @classmethod
    def _reset(cls) -> None:
        """Сбрасывает синглтон (для тестов)."""
        cls._instance = None


def get_database() -> DatabaseManager:
    """Удобный доступ к единственному экземпляру менеджера хранилища."""
    return DatabaseManager()
