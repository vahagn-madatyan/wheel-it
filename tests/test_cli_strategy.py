"""Tests for run-strategy CLI entry point (scripts/run_strategy.py)."""

from unittest.mock import MagicMock, mock_open, patch

from typer.testing import CliRunner

from scripts.run_strategy import app

runner = CliRunner()


def test_strategy_help():
    """--help exits 0 and shows all flags."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--fresh-start" in result.output
    assert "--strat-log" in result.output
    assert "--log-level" in result.output
    assert "--log-to-file" in result.output
    assert "--screen" in result.output


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
@patch("scripts.run_strategy.sell_puts")
@patch("scripts.run_strategy.sell_calls")
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
    mock_sell_calls,
    mock_sell_puts,
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
    from screener.config_loader import ScreenerConfig

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
    # Strategy execution proceeded (sell_puts called)
    mock_sell_puts.assert_called_once()
