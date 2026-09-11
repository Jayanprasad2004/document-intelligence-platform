"""
Central logging setup. Import `logger` from here wherever logging is needed,
rather than calling logging.getLogger() ad hoc in each module.
"""
import logging
import sys

from app.core.config import settings


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("document_intelligence")
    logger.setLevel(settings.log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = configure_logging()
