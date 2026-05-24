"""Unified logging config with request-id injection."""
import logging
import logging.config
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "app.logging_config.RequestIDFilter"}},
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-5s [%(request_id)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "sqlalchemy.engine": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING)
