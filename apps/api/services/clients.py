"""Per-request Alpaca client construction.

Builds SDK clients directly from provided API keys — no env vars,
no BrokerClient wrapper, no UserAgentMixin.
"""

from alpaca.trading.client import TradingClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient


def create_alpaca_clients(
    api_key: str,
    secret_key: str,
    is_paper: bool = True,
) -> tuple[TradingClient, OptionHistoricalDataClient, StockHistoricalDataClient]:
    """Construct the three Alpaca SDK clients from provided credentials.

    Args:
        api_key: Alpaca API key.
        secret_key: Alpaca secret key.
        is_paper: Whether to use the paper trading environment.

    Returns:
        Tuple of (TradingClient, OptionHistoricalDataClient, StockHistoricalDataClient).
    """
    trade_client = TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=is_paper,
    )
    option_client = OptionHistoricalDataClient(
        api_key=api_key,
        secret_key=secret_key,
    )
    stock_client = StockHistoricalDataClient(
        api_key=api_key,
        secret_key=secret_key,
    )
    return trade_client, option_client, stock_client
