from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from src import logging_setup


@pytest.fixture(autouse=True)
def _isolate_root_logger() -> Iterator[None]:
    """Isolate each test from global ``logging`` state.

    Saves and restores the root logger's handlers, level, and the
    module-level ``_CONFIGURED`` flag, so tests can freely mutate these
    without leaking state between tests.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    saved_configured = logging_setup._CONFIGURED

    try:
        yield
    finally:
        root.handlers.clear()
        root.handlers.extend(saved_handlers)
        root.setLevel(saved_level)
        logging_setup._CONFIGURED = saved_configured


def _reset_logging_state() -> None:
    """Drop any handlers pytest's logging plugin attached around the call
    phase and clear the module-level ``_CONFIGURED`` flag, so
    ``logging.basicConfig`` can actually take effect within the test body.
    """
    logging.getLogger().handlers.clear()
    logging_setup._CONFIGURED = False


def test_configure_logging_is_idempotent() -> None:
    _reset_logging_state()
    root = logging.getLogger()
    initial_count = len(root.handlers)

    logging_setup.configure_logging()
    logging_setup.configure_logging()

    assert len(root.handlers) - initial_count == 1


def test_configure_logging_respects_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_logging_state()
    monkeypatch.setenv("ACC_VIZ_LOG_LEVEL", "DEBUG")

    logging_setup.configure_logging()

    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_respects_explicit_arg() -> None:
    _reset_logging_state()

    logging_setup.configure_logging(level=logging.WARNING)

    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_invalid_env_defaults_to_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_logging_state()
    monkeypatch.setenv("ACC_VIZ_LOG_LEVEL", "GARBAGE")

    logging_setup.configure_logging()

    assert logging.getLogger().level == logging.INFO


def test_get_logger_triggers_configuration() -> None:
    _reset_logging_state()

    logger = logging_setup.get_logger("x")

    assert logging_setup._CONFIGURED is True
    assert isinstance(logger, logging.Logger)
    assert logger.name == "x"
