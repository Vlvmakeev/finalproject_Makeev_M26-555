import logging
from abc import abstractmethod, ABC
from http.client import responses
from typing import Dict, Optional

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger(__name__)

class BaseApiClient(ABC):
    def __init__(self, config: ParserConfig):
        """
        Инициализация клиента.

        Args:
            config: Конфигурация Parser Service
        """
        self.config = config

    @property
    def name(self) -> str:
        """Имя клиента для логирования."""
        return self.__class__.__name__

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы валют.

        Абстрактный метод — наследники обязаны его реализовать.

        Returns:
            Словарь с курсами валют
        """
        pass

    def _make_request(self, url: str, params: Optional[dict] = None) -> requests.Response:
        """
        Выполняет HTTP-запрос с обработкой ошибок.

        Переиспользуемый метод для всех клиентов.

        Args:
            url: URL для запроса
            params: Параметры запроса

        Returns:
            Ответ от сервера

        Raises:
            ApiRequestError: Если запрос не удался
        """
        try:
            response = requests.get(url, params=params, timeout=self.config.REQUEST_TIMEOUT)

            if response.status_code == 401:
                raise ApiRequestError(f"{self.name}: Invalid API key (401)")
            elif response.status_code == 429:
                raise ApiRequestError(f"{self.name}: Rate limit exceeded (429)")
            elif response.status_code != 200:
                raise ApiRequestError(
                    f"{self.name}: HTTP {response.status_code} - {response.reason}"
                )

            return response

        except requests.exceptions.Timeout:
            raise ApiRequestError(f"{self.name}: Request timed out")
        except requests.exceptions.ConnectionError:
            raise ApiRequestError(f"{self.name}: Connection error")
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"{self.name}: Network error - {str(e)}")

class CoinGeckoClient(BaseApiClient):
    """
    Клиент для получения курсов криптовалют с CoinGecko

    Использует публичный API без ключа
    """

    @property
    def name(self) -> str:
        return "CoinGecko"

    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы криптовалют с CoinGecko.

        Returns:
            Словарь с курсами криптовалют

        Raises:
            ApiRequestError: Если запрос не удался
        """

        ids = ",".join([
            self.config.CRYPTO_ID_MAP[code]
            for code in self.config.CRYPTO_CURRENCIES
            if code in self.config.CRYPTO_ID_MAP
        ])

        if not ids:
            logger.warning(f"{self.name}:  No crypto currencies configured")
            return {}

        params = {
            "ids": ids,
            "vs_currencies": self.config.BASE_CURRENCY.lower()
        }

        logger.info(f"Fetching from {self.name}...")

        responses = self._make_request(self.config.COINGECKO_URL, params)

        data = responses.json()

        rates = {}
        base = self.config.BASE_CURRENCY

        for code, crypto_id in self.config.CRYPTO_ID_MAP.items():
            if crypto_id in data and base.lower() in data[crypto_id]:
                pair_key = f"{code}_{base}"
                rates[pair_key] = data[crypto_id][base.lower()]

        logger.info(f"{self.name}: OK ({len(rates)} rates)")
        return rates

class ExchangeRateApiClient(BaseApiClient):
    """
    Клиент для получения курсов фиатных валют с ExchangeRate-API.

    Требует API-ключ.
    """

    @property
    def name(self) -> str:
        return "ExchangeRate-API"

    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы фиатных валют с ExchangeRate-API.

        Returns:
            Словарь с курсами фиатных валют

        Raises:
            ApiRequestError: Если запрос не удался или ключ не настроен
        """
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                f"{self.name}: API key not configured"
                "Set EXCHANGERATE_API_KEY environment variable."
            )

        base = self.config.BASE_CURRENCY
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/"
            f"latest/{base}"
        )

        logger.info(f"Fetching from {self.name}...")

        # Выполняем запрос
        response = self._make_request(url)

        # Парсим ответ
        data = response.json()

        # Проверяем результат
        if data.get("result") != "success":
            error_type = data.get("error-type", "unknown")
            raise ApiRequestError(f"{self.name}: API error - {error_type}")

        # Приводим к стандартизированному формату
        rates = {}
        api_rates = data.get("rates", {})

        for code in self.config.FIAT_CURRENCIES:
            if code in api_rates:
                pair_key = f"{code}_{base}"
                rates[pair_key] = api_rates[code]

        logger.info(f"{self.name}: OK ({len(rates)} rates)")
        return rates
