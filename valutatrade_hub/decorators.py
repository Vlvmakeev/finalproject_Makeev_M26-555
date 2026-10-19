"""Декоратор ``@log_action`` для трассировки доменных операций."""

import functools
import inspect
import logging
from datetime import datetime
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_LOGGER_NAME = "valutatrade_hub.actions"

#: Поля, которые попадают в лог, если присутствуют среди аргументов вызова.
_TRACKED_FIELDS = ("username", "user_id", "currency_code", "amount", "code")


def _extract_context(func: Callable[..., Any], args, kwargs) -> dict[str, Any]:
    """Собирает контекст вызова из именованных и позиционных аргументов."""
    context: dict[str, Any] = {}
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        for field in _TRACKED_FIELDS:
            if field in bound.arguments:
                context[field] = bound.arguments[field]
    except (TypeError, ValueError):
        context.update({k: v for k, v in kwargs.items() if k in _TRACKED_FIELDS})
    return context


def _format_log(action: str, context: dict[str, Any], extra: dict[str, Any]) -> str:
    parts = [f"action={action}", f"timestamp={datetime.now().isoformat()}"]
    parts.extend(f"{key}={value}" for key, value in context.items())
    parts.extend(f"{key}={value}" for key, value in extra.items())
    return " ".join(parts)


def log_action(verbose: bool = False) -> Callable[[F], F]:
    """Логирует вызов доменной функции на уровне INFO."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(_LOGGER_NAME)
            action = func.__name__.upper()
            context = _extract_context(func, args, kwargs)
            extra: dict[str, Any] = {}

            try:
                result = func(*args, **kwargs)
                extra["result"] = "OK"
                if verbose and isinstance(result, dict):
                    for key in ("rate", "base", "value", "amount"):
                        if key in result:
                            extra[key] = result[key]
                logger.info(_format_log(action, context, extra))
                return result
            except Exception as exc:
                extra["result"] = "ERROR"
                extra["error_type"] = type(exc).__name__
                extra["error_message"] = str(exc)
                logger.error(_format_log(action, context, extra))
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
