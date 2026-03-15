from .user_agent_mixin import UserAgentMixin 
from alpaca.trading.client import TradingClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import AssetClass


class TradingClientSigned(UserAgentMixin, TradingClient):
    pass

class StockHistoricalDataClientSigned(UserAgentMixin, StockHistoricalDataClient):
    pass

class OptionHistoricalDataClientSigned(UserAgentMixin, OptionHistoricalDataClient):
    pass


class BrokerClient:
    def __init__(self, api_key, secret_key, paper=True):
        self.trade_client = TradingClientSigned(api_key=api_key, secret_key=secret_key, paper=paper)
        self.stock_client = StockHistoricalDataClientSigned(api_key=api_key, secret_key=secret_key)
        self.option_client = OptionHistoricalDataClientSigned(api_key=api_key, secret_key=secret_key)

    def get_positions(self):
        return self.trade_client.get_all_positions()

    def market_sell(self, symbol, qty=1):
        req = MarketOrderRequest(
            symbol=symbol, qty=qty, side='sell', type='market', time_in_force='day'
        )
        self.trade_client.submit_order(req)

    def liquidate_all_positions(self):
        positions = self.get_positions()
        to_liquidate = []
        for p in positions:
            if p.asset_class == AssetClass.US_OPTION:
                self.trade_client.close_position(p.symbol)
            else:
                to_liquidate.append(p)
        for p in to_liquidate:
            self.trade_client.close_position(p.symbol)
