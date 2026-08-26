import functools
import json
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_configured = False

_RESERVED = set(logging.LogRecord("name", logging.INFO, "path", 0, "msg", (), None).__dict__.keys())


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON documents."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure root logging with a single JSON stream handler.

    :param level: the log level as a string (DEBUG, INFO, WARNING, ERROR)
    :return: the root logger
    """
    global _configured
    level_value = getattr(logging, level.upper(), logging.INFO)
    if not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(level_value)
        _configured = True
    return logging.getLogger("cvengine")


def log_event(logger: logging.Logger, msg: str, **fields: Any) -> None:
    """Emit a structured log line with arbitrary extra fields.

    :param logger: the logger to emit on
    :param msg: the human-readable message
    :param fields: extra structured fields attached to the log record
    """
    logger.info(msg, extra=fields)


def timeit(event: str) -> Callable[[F], F]:
    """Decorator that logs the execution time of a callable.

    :param event: the stage/event name used in the structured log
    :return: the wrapped callable
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logging.getLogger("cvengine").info(f"{event} completed", extra={"event": event, "duration_ms": duration_ms})
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
