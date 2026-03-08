from typing import Optional
from dataclasses import dataclass, field


@dataclass
class FilterResult:
    """Pass/fail for a single filter with reason."""

    filter_name: str
    passed: bool
    actual_value: Optional[float] = None
    threshold: Optional[float] = None
    reason: str = ""


@dataclass
class ScreenedStock:
    """Stock data accumulated progressively through the screening pipeline."""

    symbol: str

    # Alpaca market data (Phase 2)
    price: Optional[float] = None
    avg_volume: Optional[float] = None

    # Finnhub fundamental data (Phase 2)
    market_cap: Optional[float] = None
    debt_equity: Optional[float] = None
    net_margin: Optional[float] = None
    sales_growth: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    # Technical indicators (Phase 3)
    rsi_14: Optional[float] = None
    sma_200: Optional[float] = None
    above_sma200: Optional[bool] = None

    # Options data (Phase 3)
    is_optionable: Optional[bool] = None

    # Scoring (Phase 3)
    score: Optional[float] = None

    # Filter tracking (Phase 4 output)
    filter_results: list[FilterResult] = field(default_factory=list)

    # Raw API responses for debugging
    raw_finnhub_profile: Optional[dict] = None
    raw_finnhub_metrics: Optional[dict] = None
    raw_alpaca_bars: Optional[dict] = None

    @classmethod
    def from_symbol(cls, symbol: str) -> "ScreenedStock":
        """Create a ScreenedStock with just a symbol, all other fields default to None."""
        return cls(symbol=symbol.upper())

    @property
    def passed_all_filters(self) -> bool:
        """Returns True only if there are filter results and all passed."""
        if not self.filter_results:
            return False
        return all(r.passed for r in self.filter_results)

    @property
    def failed_filters(self) -> list[FilterResult]:
        """Returns only the FilterResult entries where passed=False."""
        return [r for r in self.filter_results if not r.passed]
