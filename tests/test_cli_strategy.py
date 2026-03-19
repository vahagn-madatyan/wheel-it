"""Tests for run-strategy CLI entry point (scripts/run_strategy.py)."""

from unittest.mock import MagicMock, mock_open, patch

from pydantic import ValidationError
from typer.testing import CliRunner

from screener.config_loader import ScreenerConfig
from scripts.run_strategy import app

runner = CliRunner()


def _raise_validation_error(*a, **kw):
    """Helper that raises a real Pydantic ValidationError."""
    try:
        ScreenerConfig.model_validate({"preset": "invalid"})
    except ValidationError:
        raise


def test_strategy_help():
    """--help exits 0 and shows all flags."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--fresh-start" in result.output
    assert "--strat-log" in result.output
    assert "--log-level" in result.output
    assert "--log-to-file" in result.output
    assert "--screen" in result.output
    assert "--max-risk" in result.output


def test_existing_flags_preserved():
    """Help output shows all original flags from argparse-era CLI."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # All original flag names must be present
    assert "--fresh-start" in result.output
    assert "--strat-log" in result.output
    assert "--log-level" in result.output
    assert "--log-to-file" in result.output
    assert "--screen" in result.output


@patch("scripts.run_strategy.load_config")
@patch("scripts.run_strategy.require_finnhub_key", return_value="fake-key")
@patch("scripts.run_strategy.FinnhubClient")
@patch("scripts.run_strategy.progress_context")
@patch("scripts.run_strategy.run_pipeline", return_value=[])
@patch("scripts.run_strategy.render_results_table")
@patch("scripts.run_strategy.render_stage_summary")
@patch("scripts.run_strategy.get_protected_symbols", return_value={})
@patch("scripts.run_strategy.export_symbols")
@patch("scripts.run_strategy.screen_puts", return_value=[])
@patch("scripts.run_strategy.calculate_risk", return_value=0)
@patch("scripts.run_strategy.update_state", return_value={})
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.BrokerClient")
@patch("builtins.open", mock_open(read_data="AAPL\nMSFT\n"))
def test_screen_flag_runs_screener_first(
    mock_broker_cls,
    mock_setup_logger,
    mock_strat_logger_cls,
    mock_update_state,
    mock_calc_risk,
    mock_screen_puts,
    mock_export,
    mock_get_protected,
    mock_stage_summary,
    mock_results_table,
    mock_pipeline,
    mock_progress_ctx,
    mock_finnhub_cls,
    mock_finnhub_key,
    mock_load_config,
):
    """--screen flag runs screener pipeline before strategy execution."""
    mock_load_config.return_value = ScreenerConfig()

    mock_broker = MagicMock()
    mock_broker.get_positions.return_value = []
    mock_broker_cls.return_value = mock_broker

    mock_strat_logger = MagicMock()
    mock_strat_logger_cls.return_value = mock_strat_logger

    mock_std_logger = MagicMock()
    mock_setup_logger.return_value = mock_std_logger

    mock_progress_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_progress_ctx.return_value.__exit__ = MagicMock(return_value=False)

    result = runner.invoke(app, ["--screen"])
    assert result.exit_code == 0

    # Screener pipeline was called
    mock_pipeline.assert_called_once()
    # Results were displayed
    mock_results_table.assert_called_once()
    mock_stage_summary.assert_called_once()
    # Put screener called (replaces old sell_puts)
    mock_screen_puts.assert_called_once()


@patch("scripts.run_strategy.BrokerClient")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.load_config", side_effect=_raise_validation_error)
def test_config_error_shows_panel_with_screen(
    mock_load_config,
    mock_strat_logger_cls,
    mock_setup_logger,
    mock_broker_cls,
):
    """ValidationError with --screen produces Rich Panel, not raw traceback."""
    mock_strat_logger_cls.return_value = MagicMock()
    mock_setup_logger.return_value = MagicMock()
    mock_broker_cls.return_value = MagicMock()

    result = runner.invoke(app, ["--screen"])
    assert result.exit_code != 0
    assert "Configuration Error" in result.output
    assert "Traceback" not in result.output
    assert "config/presets/" in result.output


# ---------------------------------------------------------------------------
# Strategy integration tests for screen_puts()
# ---------------------------------------------------------------------------


@patch("scripts.run_strategy.load_config")
@patch("scripts.run_strategy.screen_puts", return_value=[])
@patch("scripts.run_strategy.calculate_risk", return_value=0)
@patch("scripts.run_strategy.update_state", return_value={})
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.BrokerClient")
@patch("builtins.open", mock_open(read_data="AAPL\nMSFT\n"))
def test_strategy_calls_screen_puts_not_sell_puts(
    mock_broker_cls,
    mock_setup_logger,
    mock_strat_logger_cls,
    mock_update_state,
    mock_calc_risk,
    mock_screen_puts,
    mock_load_config,
):
    """Strategy calls screen_puts() instead of the old sell_puts()."""
    mock_load_config.return_value = ScreenerConfig()
    mock_broker = MagicMock()
    mock_broker.get_positions.return_value = []
    mock_broker_cls.return_value = mock_broker
    mock_strat_logger_cls.return_value = MagicMock()
    mock_setup_logger.return_value = MagicMock()

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    mock_screen_puts.assert_called_once()


@patch("scripts.run_strategy.load_config")
@patch("scripts.run_strategy.screen_puts")
@patch("scripts.run_strategy.calculate_risk", return_value=0)
@patch("scripts.run_strategy.update_state", return_value={})
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.BrokerClient")
@patch("builtins.open", mock_open(read_data="AAPL\nMSFT\n"))
def test_strategy_sells_put_recommendations(
    mock_broker_cls,
    mock_setup_logger,
    mock_strat_logger_cls,
    mock_update_state,
    mock_calc_risk,
    mock_screen_puts,
    mock_load_config,
):
    """Strategy iterates put recommendations and calls market_sell for each."""
    from screener.put_screener import PutRecommendation

    mock_load_config.return_value = ScreenerConfig()

    rec = PutRecommendation(
        symbol="AAPL250418P00170000",
        underlying="AAPL",
        strike=170.0,
        dte=30,
        premium=2.50,
        delta=-0.22,
        oi=500,
        spread=0.04,
        annualized_return=17.89,
    )
    mock_screen_puts.return_value = [rec]

    mock_broker = MagicMock()
    mock_broker.get_positions.return_value = []
    mock_broker_cls.return_value = mock_broker
    mock_strat_logger_cls.return_value = MagicMock()
    mock_setup_logger.return_value = MagicMock()

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    mock_broker.market_sell.assert_called_once_with("AAPL250418P00170000")


@patch("scripts.run_strategy.load_config")
@patch("scripts.run_strategy.screen_puts", return_value=[])
@patch("scripts.run_strategy.calculate_risk", return_value=0)
@patch("scripts.run_strategy.update_state", return_value={})
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.BrokerClient")
@patch("builtins.open", mock_open(read_data="AAPL\nMSFT\n"))
def test_empty_recommendations_no_crash(
    mock_broker_cls,
    mock_setup_logger,
    mock_strat_logger_cls,
    mock_update_state,
    mock_calc_risk,
    mock_screen_puts,
    mock_load_config,
):
    """Empty recommendations → no orders placed, no crash."""
    mock_load_config.return_value = ScreenerConfig()
    mock_broker = MagicMock()
    mock_broker.get_positions.return_value = []
    mock_broker_cls.return_value = mock_broker
    mock_strat_logger_cls.return_value = MagicMock()
    mock_setup_logger.return_value = MagicMock()

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    mock_broker.market_sell.assert_not_called()


@patch("scripts.run_strategy.load_config")
@patch("scripts.run_strategy.screen_puts", return_value=[])
@patch("scripts.run_strategy.calculate_risk", return_value=10_000)
@patch("scripts.run_strategy.update_state", return_value={})
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.BrokerClient")
@patch("builtins.open", mock_open(read_data="AAPL\nMSFT\n"))
def test_max_risk_cli_flag(
    mock_broker_cls,
    mock_setup_logger,
    mock_strat_logger_cls,
    mock_update_state,
    mock_calc_risk,
    mock_screen_puts,
    mock_load_config,
):
    """--max-risk CLI flag sets buying power to (max_risk - current_risk)."""
    mock_load_config.return_value = ScreenerConfig()
    mock_broker = MagicMock()
    mock_broker.get_positions.return_value = []
    mock_broker_cls.return_value = mock_broker
    mock_strat_logger_cls.return_value = MagicMock()
    mock_setup_logger.return_value = MagicMock()

    result = runner.invoke(app, ["--max-risk", "50000"])
    assert result.exit_code == 0
    # buying_power = 50000 - 10000 = 40000 (third positional arg to screen_puts)
    call_args = mock_screen_puts.call_args
    assert call_args[0][3] == 40_000


@patch("scripts.run_strategy.load_config")
@patch("scripts.run_strategy.screen_puts", return_value=[])
@patch("scripts.run_strategy.StrategyLogger")
@patch("scripts.run_strategy.setup_logger")
@patch("scripts.run_strategy.BrokerClient")
@patch("builtins.open", mock_open(read_data="AAPL\nMSFT\n"))
def test_max_risk_cli_flag_with_fresh_start(
    mock_broker_cls,
    mock_setup_logger,
    mock_strat_logger_cls,
    mock_screen_puts,
    mock_load_config,
):
    """--max-risk with --fresh-start uses full max_risk as buying power."""
    mock_load_config.return_value = ScreenerConfig()
    mock_broker = MagicMock()
    mock_broker_cls.return_value = mock_broker
    mock_strat_logger_cls.return_value = MagicMock()
    mock_setup_logger.return_value = MagicMock()

    result = runner.invoke(app, ["--fresh-start", "--max-risk", "60000"])
    assert result.exit_code == 0
    call_args = mock_screen_puts.call_args
    assert call_args[0][3] == 60_000


def test_no_core_execution_imports():
    """scripts/run_strategy.py must not import from core.execution."""
    import ast
    from pathlib import Path

    source = Path("scripts/run_strategy.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "core.execution", (
                "run_strategy.py still imports from core.execution"
            )
