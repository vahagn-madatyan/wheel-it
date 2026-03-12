"""Standalone screener CLI entry point.

Usage:
    run-screener                        # display results only (default)
    run-screener --update-symbols       # write screened symbols to config/symbol_list.txt
    run-screener --verbose              # show per-filter breakdown waterfall
    run-screener --preset aggressive    # override config preset
    run-screener --config path/to.yaml  # custom config file
"""

import logging as stdlib_logging
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from config.credentials import require_finnhub_key
from core.cli_common import create_broker_client, require_alpaca_credentials
from core.state_manager import update_state
from screener.config_loader import (
    ScreenerConfig,
    deep_merge,
    format_validation_errors,
    load_config,
    load_preset,
)
from screener.display import (
    progress_context,
    render_filter_breakdown,
    render_results_table,
    render_stage_summary,
)
from screener.export import export_symbols, get_protected_symbols
from screener.finnhub_client import FinnhubClient
from screener.pipeline import run_pipeline

logger = stdlib_logging.getLogger(__name__)

SYMBOL_LIST_PATH = Path(__file__).parent.parent / "config" / "symbol_list.txt"

app = typer.Typer(help="Screen stocks for wheel strategy suitability.")


class PresetName(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


@app.command()
def run(
    update_symbols: Annotated[
        bool,
        typer.Option("--update-symbols", help="Write screened symbols to config/symbol_list.txt"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show per-filter breakdown waterfall"),
    ] = False,
    preset: Annotated[
        PresetName | None,
        typer.Option(help="Override config preset [conservative|moderate|aggressive]"),
    ] = None,
    config: Annotated[
        str,
        typer.Option("--config", help="Path to screener config YAML"),
    ] = "config/screener.yaml",
) -> None:
    """Screen stocks for wheel strategy suitability."""
    # If --update-symbols, validate Alpaca credentials early (hard error)
    if update_symbols:
        require_alpaca_credentials()

    # Load screener config with optional preset override
    try:
        if preset is not None:
            preset_data = load_preset(preset.value)
            config_path = Path(config)
            if config_path.exists():
                with open(config_path) as f:
                    user_config = yaml.safe_load(f) or {}
            else:
                user_config = {}
            user_config["preset"] = preset.value
            merged = deep_merge(preset_data, user_config)
            cfg = ScreenerConfig.model_validate(merged)
        else:
            cfg = load_config(config)
    except ValidationError as e:
        console = Console(stderr=True)
        error_text = format_validation_errors(e)
        panel = Panel(
            error_text,
            title="Configuration Error",
            border_style="red",
            expand=False,
        )
        console.print(panel)
        console.print(
            "[dim]See config/presets/ for valid examples "
            "or run-screener --preset conservative[/dim]"
        )
        raise typer.Exit(code=1)

    # Create Finnhub client
    finnhub_key = require_finnhub_key()
    finnhub = FinnhubClient(api_key=finnhub_key)

    # Create Alpaca clients
    broker = create_broker_client()

    # Run pipeline with progress display
    with progress_context() as on_progress:
        results = run_pipeline(
            broker.trade_client,
            broker.stock_client,
            finnhub,
            cfg,
            on_progress=on_progress,
        )

    # Display results
    render_results_table(results)
    render_stage_summary(results)

    if verbose:
        render_filter_breakdown(results)

    # Optionally update symbol list
    if update_symbols:
        positions = broker.get_positions()
        protected = get_protected_symbols(positions, update_state)
        screened = [
            s.symbol
            for s in results
            if s.passed_all_filters and s.score is not None
        ]
        export_symbols(screened, protected, SYMBOL_LIST_PATH)


def main():
    app()


if __name__ == "__main__":
    main()
