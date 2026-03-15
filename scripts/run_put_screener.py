"""Standalone cash-secured put screener CLI entry point.

Usage:
    run-put-screener AAPL MSFT GOOG --buying-power 50000
    run-put-screener AAPL --buying-power 20000 --preset conservative
    run-put-screener TSLA AMZN --buying-power 80000 --config path/to.yaml
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
from screener.put_screener import render_put_results_table, screen_puts
from screener.config_loader import (
    ScreenerConfig,
    deep_merge,
    format_validation_errors,
    load_config,
    load_preset,
)

logger = stdlib_logging.getLogger(__name__)

app = typer.Typer(help="Screen cash-secured put opportunities across multiple symbols.")


class PresetName(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


@app.command()
def run(
    symbols: Annotated[
        list[str],
        typer.Argument(help="Stock symbols to screen (e.g. AAPL MSFT GOOG)"),
    ],
    buying_power: Annotated[
        float,
        typer.Option("--buying-power", help="Available cash for securing puts"),
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
    """Screen cash-secured put opportunities for the given symbols."""
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

    symbols = [s.upper() for s in symbols]

    console.print(
        f"\n[bold]Screening cash-secured puts for {', '.join(symbols)} "
        f"(buying power: ${buying_power:,.2f}, preset: {cfg.preset})[/bold]\n"
    )

    # Run put screener
    recommendations = screen_puts(
        broker.trade_client,
        broker.option_client,
        symbols,
        buying_power,
        config=cfg,
        stock_client=broker.stock_client,
    )

    # Display results
    render_put_results_table(recommendations, buying_power, console=console)


def main():
    app()


if __name__ == "__main__":
    main()
