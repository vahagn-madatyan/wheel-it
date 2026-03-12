"""Run the options wheel trading strategy.

Usage:
    run-strategy                    # normal run
    run-strategy --fresh-start      # liquidate all positions first
    run-strategy --strat-log        # enable JSON strategy logging
    run-strategy --log-level DEBUG --log-to-file
    run-strategy --screen           # run screener before strategy
"""

import logging as stdlib_logging
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from config.credentials import ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER
from config.credentials import require_finnhub_key
from config.params import MAX_RISK
from core.broker_client import BrokerClient
from core.execution import sell_puts, sell_calls
from core.state_manager import update_state, calculate_risk
from logging.logger_setup import setup_logger
from logging.strategy_logger import StrategyLogger
from screener.config_loader import format_validation_errors, load_config
from screener.display import (
    progress_context,
    render_results_table,
    render_stage_summary,
)
from screener.export import export_symbols, get_protected_symbols
from screener.finnhub_client import FinnhubClient
from screener.pipeline import run_pipeline

logger = stdlib_logging.getLogger(__name__)

SYMBOLS_FILE = Path(__file__).parent.parent / "config" / "symbol_list.txt"

app = typer.Typer(help="Run the options wheel trading strategy.")


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@app.command()
def run(
    fresh_start: Annotated[
        bool,
        typer.Option("--fresh-start", help="Liquidate all positions before running"),
    ] = False,
    strat_log: Annotated[
        bool,
        typer.Option("--strat-log", help="Enable strategy JSON logging"),
    ] = False,
    log_level: Annotated[
        LogLevel,
        typer.Option("--log-level", help="Set logging level", case_sensitive=False),
    ] = LogLevel.INFO,
    log_to_file: Annotated[
        bool,
        typer.Option("--log-to-file", help="Write logs to file instead of just printing to stdout"),
    ] = False,
    screen: Annotated[
        bool,
        typer.Option("--screen", help="Run screener before strategy, update symbol list"),
    ] = False,
) -> None:
    """Run the options wheel trading strategy."""
    # Initialize loggers
    strat_logger = StrategyLogger(enabled=strat_log)
    std_logger = setup_logger(level=log_level.value, to_file=log_to_file)

    strat_logger.set_fresh_start(fresh_start)

    # Create BrokerClient early so it can be reused for both --screen and strategy
    client = BrokerClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY, paper=IS_PAPER)

    # --screen: run screener before strategy, auto-update symbol list
    if screen:
        try:
            cfg = load_config()
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
        finnhub_key = require_finnhub_key()
        finnhub = FinnhubClient(api_key=finnhub_key)

        with progress_context() as on_progress:
            results = run_pipeline(
                client.trade_client,
                client.stock_client,
                finnhub,
                cfg,
                on_progress=on_progress,
            )

        render_results_table(results)
        render_stage_summary(results)

        positions = client.get_positions()
        protected = get_protected_symbols(positions, update_state)
        screened = [
            s.symbol
            for s in results
            if s.passed_all_filters and s.score is not None
        ]

        if screened or protected:
            export_symbols(screened, protected, SYMBOLS_FILE)
        else:
            std_logger.warning(
                "Warning: screener found 0 passing stocks. Using existing symbol_list.txt."
            )

    # Read symbol list (may have been updated by --screen)
    with open(SYMBOLS_FILE, "r") as file:
        SYMBOLS = [line.strip() for line in file.readlines()]

    if fresh_start:
        std_logger.info("Running in fresh start mode -- liquidating all positions.")
        client.liquidate_all_positions()
        allowed_symbols = SYMBOLS
        buying_power = MAX_RISK
    else:
        positions = client.get_positions()
        strat_logger.add_current_positions(positions)

        current_risk = calculate_risk(positions)

        states = update_state(positions)
        strat_logger.add_state_dict(states)

        for symbol, state in states.items():
            if state["type"] == "long_shares":
                sell_calls(client, symbol, state["price"], state["qty"], strat_logger)

        allowed_symbols = list(set(SYMBOLS).difference(states.keys()))
        buying_power = MAX_RISK - current_risk

    strat_logger.set_buying_power(buying_power)
    strat_logger.set_allowed_symbols(allowed_symbols)

    std_logger.info(f"Current buying power is ${buying_power}")
    sell_puts(client, allowed_symbols, buying_power, strat_logger)

    strat_logger.save()


def main():
    app()


if __name__ == "__main__":
    main()
