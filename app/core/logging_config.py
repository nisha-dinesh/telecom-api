# app/core/logging_config.py
# Job of this file: structured logging. Each log line is ONE JSON object,
# easy for tools to search, e.g. {"time": "...", "level": "INFO", "status": 200, ...}.

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))  # extra data such as status, path
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)  # server log only
        return json.dumps(entry)


def setup_logging() -> None:
    """All our loggers are children of 'app' (app.request, app.error)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("app")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False