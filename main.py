"""Точка входа приложения ValutaTrade Hub.

Запускает командный интерфейс ``valutatrade_hub.cli.interface``.
"""

import sys

from valutatrade_hub.cli.interface import main

if __name__ == "__main__":
    sys.exit(main())
