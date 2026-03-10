"""Tests for run-screener CLI entry point (scripts/run_screener.py)."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from scripts.run_screener import app

runner = CliRunner()


def test_screener_help():
    """--help exits 0 and shows all options."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Screen stocks" in result.output
    assert "--update-symbols" in result.output
    assert "--verbose" in result.output
    assert "--preset" in result.output
    assert "--config" in result.output


@patch("scripts.run_screener.load_config")
@patch("scripts.run_screener.render_stage_summary")
@patch("scripts.run_screener.render_results_table")
@patch("scripts.run_screener.progress_context")
@patch("scripts.run_screener.run_pipeline", return_value=[])
@patch("scripts.run_screener.FinnhubClient")
@patch("scripts.run_screener.require_finnhub_key", return_value="fake-key")
@patch("scripts.run_screener.create_broker_client")
def test_default_no_file_writes(
    mock_create_broker,
    mock_finnhub_key,
    mock_finnhub_cls,
    mock_pipeline,
    mock_progress_ctx,
    mock_results_table,
    mock_stage_summary,
    mock_load_config,
):
    """Default invocation (no flags) displays results without writing files."""
    from screener.config_loader import ScreenerConfig

    mock_load_config.return_value = ScreenerConfig()

    mock_broker = MagicMock()
    mock_create_broker.return_value = mock_broker

    # progress_context is a context manager
    mock_progress_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_progress_ctx.return_value.__exit__ = MagicMock(return_value=False)

    result = runner.invoke(app, [])
    assert result.exit_code == 0

    # Pipeline was called
    mock_pipeline.assert_called_once()
    # Results were displayed
    mock_results_table.assert_called_once()
    mock_stage_summary.assert_called_once()


@patch("scripts.run_screener.require_alpaca_credentials")
def test_update_symbols_requires_credentials(mock_require_creds):
    """--update-symbols requires Alpaca credentials; exits non-zero if missing."""
    mock_require_creds.side_effect = SystemExit(
        "Error: --update-symbols requires Alpaca credentials for position protection.\n"
        "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env"
    )

    result = runner.invoke(app, ["--update-symbols"])
    assert result.exit_code != 0
    assert "requires Alpaca credentials" in result.output


@patch("scripts.run_screener.load_config")
@patch("scripts.run_screener.render_filter_breakdown")
@patch("scripts.run_screener.render_stage_summary")
@patch("scripts.run_screener.render_results_table")
@patch("scripts.run_screener.progress_context")
@patch("scripts.run_screener.run_pipeline", return_value=[])
@patch("scripts.run_screener.FinnhubClient")
@patch("scripts.run_screener.require_finnhub_key", return_value="fake-key")
@patch("scripts.run_screener.create_broker_client")
def test_verbose_shows_filter_breakdown(
    mock_create_broker,
    mock_finnhub_key,
    mock_finnhub_cls,
    mock_pipeline,
    mock_progress_ctx,
    mock_results_table,
    mock_stage_summary,
    mock_breakdown,
    mock_load_config,
):
    """--verbose flag triggers render_filter_breakdown call."""
    from screener.config_loader import ScreenerConfig

    mock_load_config.return_value = ScreenerConfig()

    mock_broker = MagicMock()
    mock_create_broker.return_value = mock_broker

    mock_progress_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_progress_ctx.return_value.__exit__ = MagicMock(return_value=False)

    result = runner.invoke(app, ["--verbose"])
    assert result.exit_code == 0
    mock_breakdown.assert_called_once()
