import json
import os
import tempfile
from pathlib import Path
from typing import Any

class DatabaseManager:
    "Singleton-обертка над JSON-хранилищем с атомарной записью."

    _instance = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def read_json(self, path: str | Path) -> Any:
        path = Path(path)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as file:
            content = file.read().strip()
            return json.loads(content) if content else []

    def write_json(self, path: str | Path, data: Any) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_directory, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(file_directory, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise