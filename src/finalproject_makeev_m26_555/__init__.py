"""Пакет-обёртка, предоставляющий консольную точку входа приложения."""

from valutatrade_hub.cli.interface import main


def run() -> None:
    """Запускает CLI ValutaTrade Hub, завершая процесс его кодом возврата."""
    import sys

    sys.exit(main())


__all__ = ["main", "run"]
