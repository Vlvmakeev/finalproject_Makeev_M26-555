import os
from dataclasses import dataclass, field

@dataclass
class ParserConfig:
    """
       Конфигурация для Parser Service.

       Все параметры, которые могут меняться, вынесены сюда,
       чтобы не хардкодить их в коде.
    """
    EXCHANGERATE_API_KEY: str = ""

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"

    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")

    CRYPTO_ID_MAP: dict = field(default_factory=dict)

    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    REQUEST_TIMEOUT: int = 10

    def __post_init__(self):
        """
        Инициализация после создания объекта.

        Вызывается автоматически после __init__.
        Загружаем ключ из окружения и заполняем словарь, если он пуст.
        """
        if not self.EXCHANGERATE_API_KEY:
            self.EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY", "")

        if not self.CRYPTO_ID_MAP:
            self.CRYPTO_ID_MAP = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana"
            }

    def is_valid(self) -> bool:
        """
        Проверяет, что конфигурация корректна.

        Returns:
            bool: True если конфигурация валидна
        """
        return bool(self.EXCHANGERATE_API_KEY)

    def get_warning_message(self) -> str:
        """
        Возвращает предупреждение о проблемах конфигурации.

        Returns:
            str: Сообщение с предупреждением
        """
        warnings = []

        if not self.EXCHANGERATE_API_KEY:
            warnings.append(
                "ExchangeRate-API key not configured. "
                "Set EXCHANGERATE_API_KEY environment variable."
            )

        return "; ".join(warnings) if warnings else ""