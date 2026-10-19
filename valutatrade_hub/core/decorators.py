import functools
import logging
from datetime import datetime

def log_action(verbose: bool = False):
    """
    Декоратор для логирования

    Args:
        verbose: Если True, добавляет дополнительнй контекст
    Returns:
        decorator: Функция-декоратор
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(__name__)

            action = func.__name__.upper()

            username = kwargs.get("username", "unknown")
            currency_code = kwargs.get("currency_code", "")
            amount = kwargs.get("amount", "")

            log_data = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "username": username,
            }

            if currency_code:
                log_data["currency_code"] = currency_code
            if amount:
                log_data["amount"] = str(amount)

            try:
                result = func(*args, **kwargs)

                log_data["result"] = "OK"
                log_message = " ".join([f"{k}='{v}'" for k, v in log_data.items()])
                logger.info(log_message)

                return result

            except Exception as e:
                log_data["result"] = "ERROR"
                log_data["error_type"] = type(e).__name__
                log_data["error_msg"] = str(e)

                log_message = " ".join([f"{k}='{v}'" for k, v in log_data.items()])
                logger.error(log_message)

                raise

        return wrapper

    return decorator
