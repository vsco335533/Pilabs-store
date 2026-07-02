import logging
import logging.config
import sys
from pathlib import Path

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Logging configuration dictionary
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] [Request-ID: %(request_id)s] - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": sys.stdout
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8"
        },
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "logs/audit.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf8"
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True
        },
        "audit": {
            "handlers": ["console", "audit_file"],
            "level": "INFO",
            "propagate": False
        }
    }
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)


# Add placeholder adapter for Request ID if needed
class RequestIDAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        request_id = kwargs.pop("request_id", "N/A")
        return f"[Request-ID: {request_id}] {msg}", kwargs
