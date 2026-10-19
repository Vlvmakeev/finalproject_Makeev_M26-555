"""API-клиенты Parser Service для получения курсов валют."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger("valutatrade_hub.parser_service.api_clients")


class BaseApiClient(ABC):
    """Базовый клиент для внешнего API курсов."""

    def __init__(self, config: ParserConfig):
        """
        Args:
            config: Конфигурация Parser Service.
        """
        self.config = config

    @property
    def name(self) -> str:
        """Имя клиента для логирования."""
        return self.__class__.__name__

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы вида ``{"BTC_USD": 59337.21}``."""
        raise NotImplementedError

    def _make_request(
        self, url: str, params: Optional[dict] = None
    ) -> requests.Response:
        """Выполняет HTTP GET с обработкой ошибок.

        Raises:
            ApiRequestError: При ошибке сети, лимите, неверном ключе и т.п.
        """
        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.Timeout as exc:
            raise ApiRequestError(f"{self.name}: request timed out") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ApiRequestError(f"{self.name}: connection error") from exc
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"{self.name}: network error - {exc}") from exc

        if response.status_code == 401:
            raise ApiRequestError(f"{self.name}: invalid API key (401)")
        if response.status_code == 429:
            raise ApiRequestError(f"{self.name}: rate limit exceeded (429)")
        if response.status_code != 200:
            raise ApiRequestError(
                f"{self.name}: HTTP {response.status_code} - {response.reason}"
            )

        return response


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для курсов криптовалют (публичный API)."""

    @property
    def name(self) -> str:
        return "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы криптовалют к базовой валюте."""
        ids = ",".join(
            self.config.CRYPTO_ID_MAP[code]
            for code in self.config.CRYPTO_CURRENCIES
            if code in self.config.CRYPTO_ID_MAP
        )
        if not ids:
            logger.warning("%s: no crypto currencies configured", self.name)
            return {}

        base = self.config.BASE_CURRENCY
        params = {"ids": ids, "vs_currencies": base.lower()}

        logger.info("Fetching from %s...", self.name)
        response = self._make_request(self.config.COINGECKO_URL, params)
        data = response.json()

        rates: dict[str, float] = {}
        for code, crypto_id in self.config.CRYPTO_ID_MAP.items():
            entry = data.get(crypto_id)
            if isinstance(entry, dict) and base.lower() in entry:
                rates[f"{code}_{base}"] = float(entry[base.lower()])

        logger.info("%s: OK (%d rates)", self.name, len(rates))
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для курсов фиатных валют."""

    @property
    def name(self) -> str:
        return "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы фиатных валют к базовой валюте."""
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                f"{self.name}: API key not configured. "
                "Set EXCHANGERATE_API_KEY environment variable."
            )

        base = self.config.BASE_CURRENCY
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/{base}"
        )

        logger.info("Fetching from %s...", self.name)
        response = self._make_request(url)
        data = response.json()

        if data.get("result") != "success":
            error_type = data.get("error-type", "unknown")
            raise ApiRequestError(f"{self.name}: API error - {error_type}")

        rates: dict[str, float] = {}
        api_rates = data.get("rates", {})
        for code in self.config.FIAT_CURRENCIES:
            if code in api_rates:
                rates[f"{code}_{base}"] = float(api_rates[code])

        logger.info("%s: OK (%d rates)", self.name, len(rates))
        return rates
