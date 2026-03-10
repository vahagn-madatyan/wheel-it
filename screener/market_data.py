"""Alpaca daily bar fetching and technical indicator computation.

Fetches split-adjusted daily bars in batches from Alpaca's StockHistoricalDataClient,
then computes RSI(14) and SMA(200) using the ta library. Handles insufficient data
and NaN values gracefully.
"""

import logging as stdlib_logging
from datetime import datetime, timedelta
from typing import Callable

import pandas as pd
from alpaca.data.enums import Adjustment
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

logger = stdlib_logging.getLogger(__name__)


def fetch_daily_bars(
    client: StockHistoricalDataClient,
    symbols: list[str],
    num_bars: int = 250,
    batch_size: int = 20,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch daily bars for symbols in batches, return dict of per-symbol DataFrames.

    Args:
        client: Alpaca StockHistoricalDataClient instance.
        symbols: List of ticker symbols to fetch.
        num_bars: Approximate number of trading days of history to fetch.
        batch_size: Number of symbols per API request.

    Returns:
        Dict mapping symbol -> DataFrame with columns including 'close' and 'volume'.
        Symbols missing from the API response are silently excluded.
    """
    # ~1.5x calendar days covers the desired number of trading days
    start = datetime.now() - timedelta(days=int(num_bars * 1.5))

    all_bars: dict[str, pd.DataFrame] = {}

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        logger.debug("Fetching bars batch %d: %s", batch_num, batch)

        request = StockBarsRequest(
            symbol_or_symbols=batch,
            timeframe=TimeFrame.Day,
            start=start,
            adjustment=Adjustment.SPLIT,
            # DO NOT set limit -- it caps total bars across ALL symbols, not per-symbol
        )
        barset = client.get_stock_bars(request)
        df = barset.df

        for sym in batch:
            try:
                sym_df = df.loc[sym].copy()
                all_bars[sym] = sym_df
            except KeyError:
                logger.debug("Symbol %s not found in bar response, skipping", sym)

        if on_progress:
            on_progress("Fetching daily bars", min(i + batch_size, len(symbols)), len(symbols))

    return all_bars


def compute_indicators(bars_df: pd.DataFrame) -> dict:
    """Compute technical indicators from a single symbol's bar DataFrame.

    Args:
        bars_df: DataFrame with 'close' and 'volume' columns (from Alpaca bars).

    Returns:
        Dict with keys: 'price', 'avg_volume', 'rsi_14', 'sma_200', 'above_sma200'.
        Values that cannot be computed (insufficient data, NaN) are set to None.
    """
    close = bars_df["close"]
    volume = bars_df["volume"]

    result: dict = {
        "price": float(close.iloc[-1]),
        "avg_volume": float(volume.mean()),
    }

    # RSI(14) -- needs at least 30 bars for meaningful values
    if len(close) >= 30:
        rsi_series = RSIIndicator(close=close, window=14).rsi()
        rsi_val = rsi_series.iloc[-1]
        result["rsi_14"] = None if pd.isna(rsi_val) else float(rsi_val)
    else:
        result["rsi_14"] = None

    # SMA(200) -- needs at least 200 bars
    if len(close) >= 200:
        sma_series = SMAIndicator(close=close, window=200).sma_indicator()
        sma_val = sma_series.iloc[-1]
        sma_val = None if pd.isna(sma_val) else float(sma_val)
        result["sma_200"] = sma_val

        if sma_val is not None:
            result["above_sma200"] = result["price"] > sma_val
        else:
            result["above_sma200"] = None
    else:
        result["sma_200"] = None
        result["above_sma200"] = None

    return result
