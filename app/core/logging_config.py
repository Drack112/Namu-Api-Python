import json
import logging
import sys
from datetime import UTC, datetime


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        skip = {
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "name",
            "message",
            "asctime",
        }
        for key, value in record.__dict__.items():
            if key not in skip:
                base[key] = value

        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False, default=str)


def configure_logging(level: str = "DEBUG", environment: str = "development") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()

    if environment == "production":
        effective = max(logging.getLevelName(level.upper()), logging.WARNING)
        root.setLevel(effective)
    else:
        root.setLevel(level.upper())

    root.handlers = [handler]

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
