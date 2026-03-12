"""Standalone covered call screener CLI entry point.

Usage:
    run-call-screener AAPL --cost-basis 175
    run-call-screener MSFT --cost-basis 420 --preset conservative
    run-call-screener TSLA --cost-basis 250 --config path/to.yaml
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

from core.cli_common import create_broker_client
from screener.call_screener import render_call_results_table, screen_calls
from screener.config_loader import (
    ScreenerConfig,
    deep_merge,
    format_validation_errors,
    load_config,
    load_preset,
)

logger = stdlib_logging.getLogger(__name__)

app = typer.Typer(help="Screen covered call opportunities for a stock position.")


class PresetName(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


@app.command()
def run(
    symbol: Annotated[
        str,
        typer.Argument(help="Stock symbol (e.g. AAPL)"),
    ],
    cost_basis: Annotated[
        float,
        typer.Option("--cost-basis", help="Average entry price per share"),
    ],
    preset: Annotated[
        PresetName | None,
        typer.Option(help="Override config preset [conservative|moderate|aggressive]"),
    ] = None,
    config: Annotated[
        str,
        typer.Option("--config", help="Path to screener config YAML"),
    ] = "config/screener.yaml",
) -> None:
    """Screen covered call opportunities for a given symbol and cost basis."""
    console = Console()

    # Load screener config (reuses put screener config infrastructure)
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
        err_console = Console(stderr=True)
        error_text = format_validation_errors(e)
        panel = Panel(
            error_text,
            title="Configuration Error",
            border_style="red",
            expand=False,
        )
        err_console.print(panel)
        raise typer.Exit(code=1)

    # Create Alpaca clients
    broker = create_broker_client()

    symbol = symbol.upper()

    console.print(
        f"\n[bold]Screening covered calls for {symbol} "
        f"(cost basis: ${cost_basis:.2f}, preset: {cfg.preset})[/bold]\n"
    )

    # Run call screener
    recommendations = screen_calls(
        broker.trade_client,
        broker.option_client,
        symbol,
        cost_basis,
        config=cfg,
    )

    # Display results
    render_call_results_table(recommendations, symbol, cost_basis, console=console)


def main():
    app()


if __name__ == "__main__":
    main()
