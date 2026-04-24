from __future__ import annotations

import logging
import os
from typing import Final

_DEFAULT_FORMAT: Final[str] = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# ``logging.getLevelNamesMapping`` was added in Python 3.11. The project pins
# ``requires-python = ">=3.10"``, so we provide a fallback mapping for 3.10.
_LEVEL_MAP: Final[dict[str, int]] = getattr(
    logging,
    "getLevelNamesMapping",
    lambda: {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    },
)()

_CONFIGURED: bool = False


def configure_logging(level: int | str | None = None) -> None:
    """Configure the root logger exactly once.

    Idempotent: subsequent calls are no-ops. The level is resolved from:
      1) the ``level`` argument,
      2) the ``ACC_VIZ_LOG_LEVEL`` environment variable (case-insensitive),
      3) ``logging.INFO``.

    Args:
        level: Optional logging level. May be an ``int`` (e.g. ``logging.DEBUG``)
            or a case-insensitive string (e.g. ``"debug"``). When ``None`` the
            value is read from the ``ACC_VIZ_LOG_LEVEL`` environment variable,
            falling back to ``logging.INFO`` if unset or unrecognized.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved: int | str | None = level
    if resolved is None:
        resolved = os.environ.get("ACC_VIZ_LOG_LEVEL", "INFO")
    if isinstance(resolved, str):
        resolved = _LEVEL_MAP.get(resolved.upper(), logging.INFO)

    logging.basicConfig(level=resolved, format=_DEFAULT_FORMAT)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger after ensuring configuration has run.

    Args:
        name: Logger name, typically ``__name__`` from the calling module.

    Returns:
        A ``logging.Logger`` instance bound to ``name``.
    """
    configure_logging()
    return logging.getLogger(name)
