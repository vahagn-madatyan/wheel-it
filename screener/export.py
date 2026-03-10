"""Position-safe symbol list export with diff display.

Ensures active wheel positions (short puts, assigned shares, short calls)
are never removed from config/symbol_list.txt when updating with screener results.
"""

import logging as stdlib_logging
from pathlib import Path
from typing import Callable

from rich.console import Console

logger = stdlib_logging.getLogger(__name__)


def get_protected_symbols(
    positions: list,
    update_state_fn: Callable,
) -> dict[str, str]:
    """Map symbol to wheel state type for active positions.

    Args:
        positions: List of Alpaca Position objects.
        update_state_fn: The update_state function from core.state_manager.

    Returns:
        Dict mapping symbol -> state type string (e.g., "short_put", "long_shares", "short_call").
    """
    states = update_state_fn(positions)
    return {sym: state["type"] for sym, state in states.items()}


def export_symbols(
    screened: list[str],
    protected: dict[str, str],
    path: Path,
    console: Console | None = None,
) -> bool:
    """Write symbol list with position protection and colored diff display.

    Args:
        screened: List of symbols that passed screening.
        protected: Dict mapping symbol -> state type for active positions.
        path: Path to symbol_list.txt.
        console: Optional Rich Console for output (defaults to new Console).

    Returns:
        True if file was written, False if skipped (zero results with no protection).
    """
    console = console or Console()

    if not screened and not protected:
        console.print(
            "[yellow]Warning: screener found 0 passing stocks. "
            "Using existing symbol_list.txt.[/yellow]"
        )
        return False

    # Read current symbols from file
    current: set[str] = set()
    if path.exists():
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                current.add(stripped)

    # Build final set: screened + protected
    final = set(screened) | set(protected.keys())

    # Compute diff
    added = final - current
    removed = current - final
    kept_protected = set(protected.keys()) & current

    # Display diff
    for sym in sorted(added):
        console.print(f"  [green]+{sym}[/green]")
    for sym in sorted(removed):
        console.print(f"  [red]-{sym} (screened out)[/red]")
    for sym in sorted(kept_protected):
        state_type = protected[sym].replace("_", " ")
        console.print(f"  [yellow]~{sym}: kept (active {state_type})[/yellow]")

    # Write sorted symbols, one per line, trailing newline
    path.write_text("\n".join(sorted(final)) + "\n")

    logger.info(
        "Symbol list updated: %d symbols (%d added, %d removed, %d protected)",
        len(final),
        len(added),
        len(removed),
        len(kept_protected),
    )

    return True
