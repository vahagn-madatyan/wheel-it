"""The logging helpers must not shadow Python's standard library."""

from __future__ import annotations

import logging


def test_import_logging_is_stdlib() -> None:
    """A pip install used to fail here: our package was also named `logging`."""
    assert hasattr(logging, "LogRecord")
    assert hasattr(logging, "getLogger")
    assert logging.__file__ is not None
    assert "strategy_logging" not in logging.__file__


def test_strategy_logging_imports_without_shadowing_stdlib() -> None:
    from strategy_logging.logger_setup import setup_logger
    from strategy_logging.strategy_logger import StrategyLogger

    assert callable(setup_logger)
    assert StrategyLogger is not logging
