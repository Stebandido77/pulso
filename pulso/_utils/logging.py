"""Logging setup for pulso.

Use `get_logger(__name__)` in modules. Users can configure level via:

    import logging
    logging.getLogger("pulso").setLevel(logging.DEBUG)
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "pulso"


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the pulso root logger.

    Args:
        name: Module name, typically `__name__`.

    Returns:
        A configured logger instance.
    """
    if not name.startswith(_LOGGER_NAME):
        name = f"{_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


# Configure root logger with a NullHandler so library doesn't emit
# unconfigured warnings. Users opt in to logging output.
logging.getLogger(_LOGGER_NAME).addHandler(logging.NullHandler())
