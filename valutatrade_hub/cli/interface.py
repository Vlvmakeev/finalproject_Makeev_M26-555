import argparse
import sys
from typing import Optional

from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import UsernameAlreadyExistsError, UserNotFoundError, InvalidPasswordError, \
    InsufficientFundsError

_current_user_id: Optional[int] = None

def register_command(args):
    """Команда регистрации нового пользователя."""
    try:
        user = usecases.register(
            username=args.username,
            password=args.password,
        )
        print(f"Пользователь '{args.username}' зарегистрирован (id={user.user_id})")
        print(f"Войдите: login --username {args.username} --password ****")
    except UsernameAlreadyExistsError as e:
        print(e.message)
    except ValueError as e:
        print(str(e))
    except Exception as e:
        print(f"Ошибка регистрации: {str(e)}")

def login_command(args):
    """Команда входа в систему."""
    global _current_user_id

    try:
        user = usecases.login(
            username=args.username,
            password=args.password
        )
        _current_user_id = user.user_id
        print(f"Вы вошли в систему под ником '{args.username}'")
    except UserNotFoundError as e:
        print(e.message)
    except InvalidPasswordError as e:
        print(e.message)
    except Exception as e:
        print(f"Ошибка входа: {str(e)}")

def buy_command(args):
    """Команда покупки валюты."""
    global _current_user_id

    if _current_user_id is None:
        print("Сначала авторизируйтесь в системе")
        return

    try:
        result = usecases.buy(
            user_id=_current_user_id,
            currency_code=args.currency_code,
            amount=args.amount
        )

        currency = result["currency"]
        amount = result["amount"]

        print(f"Покупка выполнена: {amount:.4f} {currency}")

    except InsufficientFundsError as e:
        print(e.message)
    except ValueError as e:
        print(str(e))
    except Exception as e:
        print(f"Ошибка покупки: {str(e)}")

def sell_command(args):
    """Команда продажи валюты."""
    global _current_user_id

    if _current_user_id is None:
        print("Сначала авторизируйтесь в системе")
        return

    try:
        result = usecases.sell(
            user_id=_current_user_id,
            currency_code=args.currency_code,
            amount=args.amount
        )

        currency = result["currency"]
        amount = result["amount"]

        print(f"Продажа выполнена: {amount:.4f} {currency}")

    except InsufficientFundsError as e:
        print(e.message)
    except ValueError as e:
        print(str(e))
    except Exception as e:
        print(f"Ошибка продажи: {str(e)}")


def update_rates_command(args):
    """Команда обновления курсов валют."""
    params = parse_named_args(args)
    source = params.get("source")

    try:
        from valutatrade_hub.parser_service.config import ParserConfig
        from valutatrade_hub.parser_service.api_clients import (
            CoinGeckoClient,
            ExchangeRateApiClient,
        )
        from valutatrade_hub.parser_service.updater import RatesUpdater
        from valutatrade_hub.parser_service.storage import RatesStorage

        # Создаем конфигурацию
        config = ParserConfig()

        # Проверяем конфигурацию
        if not config.is_valid():
            warning = config.get_warning_message()
            print(f"WARNING: {warning}")
            print("Some sources may not be available.\n")

        # Создаем хранилище
        storage = RatesStorage(config)

        # Создаем клиенты
        clients = [
            CoinGeckoClient(config),
            ExchangeRateApiClient(config),
        ]

        # Создаем апдейтер и запускаем обновление
        updater = RatesUpdater(clients, storage, config)
        result = updater.run_update(source=source)

    except ImportError as e:
        print(f"ERROR: Missing dependencies - {str(e)}")
        print("Please run: uv add requests")
    except Exception as e:
        print(f"ERROR: {str(e)}")

def create_parser():
    """Создает парсер аргументов командной строки."""