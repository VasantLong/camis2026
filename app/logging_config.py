"""Unified logging config with request-id injection."""
import logging
import logging.config
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "camis.log"


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
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_FILE),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "default",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "sqlalchemy.engine": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.config.dictConfig(LOGGING)
