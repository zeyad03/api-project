"""Structured logging configuration for the F1 Facts API."""

import logging
import sys

from src.config.settings import settings


def setup_logging() -> logging.Logger:
    """Configure application-wide structured logging.

    Returns the root ``f1api`` logger so callers can do::

        from src.core.logging import logger
        logger.info("something happened", extra={"user_id": uid})
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger("f1api")
    root_logger.setLevel(log_level)
    # Avoid duplicate handlers on reload
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    return root_logger


logger = setup_logging()
