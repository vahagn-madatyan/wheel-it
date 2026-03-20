"""Tests for screener/put_screener.py — put screening module."""

from datetime import date, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from screener.put_screener import (
    PutRecommendation,
    compute_put_annualized_return,
    screen_puts,
)
from screener.config_loader import ScreenerConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_contract(
    symbol: str,
    strike_price: float,
    expiration_date,
    open_interest=200,
    underlying="AAPL",
):
    """Create a mock Alpaca OptionContract."""
    contract = MagicMock()
    contract.symbol = symbol
    contract.strike_price = strike_price
    contract.expiration_date = expiration_date
    contract.open_interest = open_interest
    contract.underlying_symbol = underlying
    return contract


def _make_mock_snapshot(bid_price, ask_price, delta=None):
    """Create a mock OptionSnapshot with quote and optional greeks."""
    snap = MagicMock()
    snap.latest_quote = MagicMock()
    snap.latest_quote.bid_price = bid_price
    snap.latest_quote.ask_price = ask_price
    if delta is not None:
        snap.greeks = MagicMock()
        snap.greeks.delta = delta
    else:
        snap.greeks = None
    return snap


def _make_mock_trade(price: float):
    """Create a mock latest trade response entry."""
    trade = MagicMock()
    trade.price = price
    return trade


def _mock_clients(contracts=None, snapshots=None, page_token=None):
    """Create mock trade_client, option_client, and stock_client."""
    trade_client = MagicMock()
    option_client = MagicMock()
    stock_client = MagicMock()

    response = MagicMock()
    response.option_contracts = contracts or []
    response.next_page_token = page_token
    trade_client.get_option_contracts.return_value = response

    option_client.get_option_snapshot.return_value = snapshots or {}

    return trade_client, option_client, stock_client


# ---------------------------------------------------------------------------
# PutRecommendation dataclass tests
# ---------------------------------------------------------------------------


class TestPutRecommendation:
    """Tests for the PutRecommendation dataclass."""

    def test_basic_construction(self):
        rec = PutRecommendation(
            symbol="AAPL250418P00170000",
            underlying="AAPL",
            strike=170.0,
            dte=30,
            premium=2.50,
            extrinsic=2.50,
            delta=-0.25,
            oi=500,
            spread=0.04,
            annualized_return=17.89,
        )
        assert rec.symbol == "AAPL250418P00170000"
        assert rec.underlying == "AAPL"
        assert rec.strike == 170.0
        assert rec.dte == 30
        assert rec.premium == 2.50
        assert rec.extrinsic == 2.50
        assert rec.delta == -0.25
        assert rec.oi == 500
        assert rec.spread == 0.04
        assert rec.annualized_return == 17.89

    def test_delta_none(self):
        rec = PutRecommendation(
            symbol="AAPL250418P00170000",
            underlying="AAPL",
            strike=170.0,
            dte=30,
            premium=2.50,
            extrinsic=2.50,
            delta=None,
            oi=500,
            spread=0.04,
            annualized_return=17.89,
        )
        assert rec.delta is None

    def test_fields_independent(self):
        """Two recommendations with different values are distinct."""
        rec1 = PutRecommendation(
            symbol="AAPL250418P00170000",
            underlying="AAPL",
            strike=170.0,
            dte=30,
            premium=2.50,
            extrinsic=2.50,
            delta=-0.25,
            oi=500,
            spread=0.04,
            annualized_return=17.89,
        )
        rec2 = PutRecommendation(
            symbol="MSFT250418P00400000",
            underlying="MSFT",
            strike=400.0,
            dte=45,
            premium=5.00,
            extrinsic=5.00,
            delta=-0.20,
            oi=1000,
            spread=0.02,
            annualized_return=10.14,
        )
        assert rec1.underlying != rec2.underlying
        assert rec1.strike != rec2.strike


# ---------------------------------------------------------------------------
# compute_put_annualized_return tests
# ---------------------------------------------------------------------------


class TestComputePutAnnualizedReturn:
    """Tests for the annualized return computation function."""

    def test_known_value(self):
        """(1.50 / 150.0) * (365 / 30) * 100 = 12.17"""
        result = compute_put_annualized_return(1.50, 150.0, 30)
        assert result == 12.17

    def test_known_value_45_dte(self):
        """(3.00 / 200.0) * (365 / 45) * 100 = 12.17"""
        result = compute_put_annualized_return(3.00, 200.0, 45)
        assert result == 12.17

    def test_known_value_14_dte(self):
        """(0.50 / 100.0) * (365 / 14) * 100 = 13.04"""
        result = compute_put_annualized_return(0.50, 100.0, 14)
        assert result == 13.04

    def test_high_premium(self):
        """(5.00 / 50.0) * (365 / 30) * 100 = 121.67"""
        result = compute_put_annualized_return(5.00, 50.0, 30)
        assert result == 121.67

    def test_zero_premium_is_valid(self):
        """Zero premium is valid — returns 0.0, not None."""
        result = compute_put_annualized_return(0, 150.0, 30)
        assert result == 0.0

    def test_zero_strike_returns_none(self):
        result = compute_put_annualized_return(1.50, 0, 30)
        assert result is None

    def test_negative_strike_returns_none(self):
        result = compute_put_annualized_return(1.50, -100.0, 30)
        assert result is None

    def test_zero_dte_returns_none(self):
        result = compute_put_annualized_return(1.50, 150.0, 0)
        assert result is None

    def test_negative_dte_returns_none(self):
        result = compute_put_annualized_return(1.50, 150.0, -5)
        assert result is None

    def test_negative_premium_returns_none(self):
        result = compute_put_annualized_return(-1.0, 150.0, 30)
        assert result is None

    def test_rounding(self):
        """Verify result is rounded to 2 decimal places."""
        # (1.0 / 300.0) * (365 / 17) * 100 = 7.156862...
        result = compute_put_annualized_return(1.0, 300.0, 17)
        assert result == 7.16

    def test_large_values(self):
        """Large strike/premium values compute correctly."""
        result = compute_put_annualized_return(10.0, 5000.0, 60)
        # (10 / 5000) * (365 / 60) * 100 = 1.22
        assert result == 1.22


# ---------------------------------------------------------------------------
# DTE constants tests
# ---------------------------------------------------------------------------


class TestDTEConstants:
    """Verify DTE range defaults on OptionsConfig."""

    def test_put_dte_min_default(self):
        config = ScreenerConfig()
        assert config.options.dte_min == 14

    def test_put_dte_max_default(self):
        config = ScreenerConfig()
        assert config.options.dte_max == 60


# ---------------------------------------------------------------------------
# screen_puts() tests
# ---------------------------------------------------------------------------


class TestScreenPuts:
    """Tests for the core screen_puts() function."""

    def _exp_date(self, days_from_now=30):
        return date.today() + timedelta(days=days_from_now)

    # --- Empty / edge cases ---

    def test_empty_symbols_returns_empty(self):
        tc, oc, sc = _mock_clients()
        result = screen_puts(tc, oc, [], 50000.0, stock_client=sc)
        assert result == []

    def test_zero_buying_power_returns_empty(self):
        tc, oc, sc = _mock_clients()
        result = screen_puts(tc, oc, ["AAPL"], 0, stock_client=sc)
        assert result == []

    def test_negative_buying_power_returns_empty(self):
        tc, oc, sc = _mock_clients()
        result = screen_puts(tc, oc, ["AAPL"], -1000, stock_client=sc)
        assert result == []

    def test_no_contracts_returns_empty(self):
        tc, oc, sc = _mock_clients(contracts=[])
        sc.get_stock_latest_trade.return_value = {
            "AAPL": _make_mock_trade(150.0)
        }
        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_config_none_uses_defaults(self):
        """screen_puts works with config=None (uses ScreenerConfig defaults)."""
        tc, oc, sc = _mock_clients(contracts=[])
        sc.get_stock_latest_trade.return_value = {
            "AAPL": _make_mock_trade(150.0)
        }
        result = screen_puts(tc, oc, ["AAPL"], 50000.0, config=None, stock_client=sc)
        assert result == []
        # Main check: didn't crash

    # --- Buying power pre-filter ---

    def test_buying_power_excludes_expensive_symbols(self):
        """Symbols where 100 * price > buying_power are excluded."""
        exp = self._exp_date()
        contract = _make_mock_contract("CHEAP250P", 40.0, exp, underlying="CHEAP")
        snap = _make_mock_snapshot(1.0, 1.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"CHEAP250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {
            "CHEAP": _make_mock_trade(45.0),   # 100*45 = 4500 <= 5000 ✓; strike 40 < 45 OTM ✓
            "EXPENSIVE": _make_mock_trade(100.0),  # 100*100 = 10000 > 5000 ✗
        }

        result = screen_puts(tc, oc, ["CHEAP", "EXPENSIVE"], 5000.0, stock_client=sc)
        # EXPENSIVE should be excluded from the contract fetch
        req = tc.get_option_contracts.call_args[0][0]
        assert "EXPENSIVE" not in req.underlying_symbols

    def test_all_symbols_too_expensive_returns_empty(self):
        tc, oc, sc = _mock_clients()
        sc.get_stock_latest_trade.return_value = {
            "AAPL": _make_mock_trade(200.0),  # 100*200 = 20000 > 5000
        }
        result = screen_puts(tc, oc, ["AAPL"], 5000.0, stock_client=sc)
        assert result == []

    def test_stock_client_none_skips_buying_power_filter(self):
        """When stock_client is None, all symbols proceed."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, underlying="AAPL")
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc, oc, _ = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=None)
        assert len(result) == 1

    def test_stock_api_failure_proceeds_with_all_symbols(self):
        """API failure in get_stock_latest_trade doesn't crash — all symbols proceed."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, underlying="AAPL")
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.side_effect = Exception("API error")

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1

    # --- OI filter ---

    def test_low_oi_excluded(self):
        """Contracts with OI below threshold are excluded."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=5)
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        # Default ScreenerConfig OI minimum is > 5
        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_oi_none_treated_as_zero(self):
        """Contract with None OI is treated as 0 (excluded by default)."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=None)

        tc, oc, sc = _mock_clients(contracts=[contract])
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    # --- Spread filter ---

    def test_wide_spread_excluded(self):
        """Contracts with spread > threshold are excluded."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        # bid=1.0, ask=2.0 → spread = 1.0/1.5 = 0.667 → way above default max
        snap = _make_mock_snapshot(1.0, 2.0, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_tight_spread_passes(self):
        """Contracts with narrow spread pass the filter."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        # bid=2.0, ask=2.10 → spread = 0.10/2.05 ≈ 0.049 → tight
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1

    # --- Delta filter ---

    def test_delta_below_min_excluded(self):
        """Contracts with abs(delta) < DELTA_MIN are excluded."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.05)  # too low

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_delta_above_max_excluded(self):
        """Contracts with abs(delta) > DELTA_MAX are excluded."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.50)  # too high

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_delta_none_passes(self):
        """Contracts with None delta pass the filter (D039)."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        snap = _make_mock_snapshot(2.0, 2.10, delta=None)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1
        assert result[0].delta is None

    def test_delta_in_range_passes(self):
        """Contracts with delta in [DELTA_MIN, DELTA_MAX] pass."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)  # abs=0.20, in [0.15, 0.30]

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1
        assert result[0].delta == -0.20

    # --- One-per-underlying ---

    def test_one_per_underlying_keeps_best(self):
        """When multiple contracts exist for same underlying, keep highest return."""
        exp = self._exp_date()
        c1 = _make_mock_contract("AAPL250P170", 170.0, exp, open_interest=500, underlying="AAPL")
        c2 = _make_mock_contract("AAPL250P165", 165.0, exp, open_interest=500, underlying="AAPL")

        # c2 has higher bid → higher annualized return for lower strike
        snap1 = _make_mock_snapshot(1.50, 1.60, delta=-0.20)  # (1.50/170)*365/30*100 ≈ 10.74
        snap2 = _make_mock_snapshot(3.00, 3.10, delta=-0.20)  # (3.00/165)*365/30*100 ≈ 22.12

        tc, oc, sc = _mock_clients(
            contracts=[c1, c2],
            snapshots={"AAPL250P170": snap1, "AAPL250P165": snap2},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1
        assert result[0].symbol == "AAPL250P165"  # higher return

    def test_multiple_underlyings(self):
        """Returns one recommendation per underlying when multiple symbols screened."""
        exp = self._exp_date()
        c1 = _make_mock_contract("AAPL250P170", 170.0, exp, open_interest=500, underlying="AAPL")
        c2 = _make_mock_contract("MSFT250P400", 400.0, exp, open_interest=500, underlying="MSFT")

        snap1 = _make_mock_snapshot(2.0, 2.10, delta=-0.20)
        snap2 = _make_mock_snapshot(5.0, 5.20, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[c1, c2],
            snapshots={"AAPL250P170": snap1, "MSFT250P400": snap2},
        )
        sc.get_stock_latest_trade.return_value = {
            "AAPL": _make_mock_trade(175.0),
            "MSFT": _make_mock_trade(420.0),
        }

        result = screen_puts(tc, oc, ["AAPL", "MSFT"], 50000.0, stock_client=sc)
        assert len(result) == 2
        underlyings = {r.underlying for r in result}
        assert underlyings == {"AAPL", "MSFT"}

    # --- Sorting ---

    def test_sorted_by_annualized_return_descending(self):
        """Recommendations are sorted by annualized return, best first."""
        exp = self._exp_date()
        c1 = _make_mock_contract("AAPL250P170", 170.0, exp, open_interest=500, underlying="AAPL")
        c2 = _make_mock_contract("MSFT250P400", 400.0, exp, open_interest=500, underlying="MSFT")

        # AAPL: (2.0/170)*365/30*100 ≈ 14.31
        # MSFT: (3.0/400)*365/30*100 ≈ 9.13
        snap1 = _make_mock_snapshot(2.0, 2.10, delta=-0.20)
        snap2 = _make_mock_snapshot(3.0, 3.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[c1, c2],
            snapshots={"AAPL250P170": snap1, "MSFT250P400": snap2},
        )
        sc.get_stock_latest_trade.return_value = {
            "AAPL": _make_mock_trade(175.0),
            "MSFT": _make_mock_trade(420.0),
        }

        result = screen_puts(tc, oc, ["AAPL", "MSFT"], 50000.0, stock_client=sc)
        assert len(result) == 2
        assert result[0].annualized_return > result[1].annualized_return
        assert result[0].underlying == "AAPL"

    # --- Pagination ---

    def test_pagination_fetches_multiple_pages(self):
        """Pagination: follows next_page_token to get all contracts."""
        exp = self._exp_date()
        c1 = _make_mock_contract("AAPL250P170", 170.0, exp, open_interest=500, underlying="AAPL")
        c2 = _make_mock_contract("AAPL250P165", 165.0, exp, open_interest=500, underlying="AAPL")

        snap1 = _make_mock_snapshot(2.0, 2.10, delta=-0.20)
        snap2 = _make_mock_snapshot(3.0, 3.10, delta=-0.20)

        tc = MagicMock()
        oc = MagicMock()
        sc = MagicMock()

        # Page 1: returns c1 with next_page_token
        page1 = MagicMock()
        page1.option_contracts = [c1]
        page1.next_page_token = "page2token"

        # Page 2: returns c2 with no next_page_token
        page2 = MagicMock()
        page2.option_contracts = [c2]
        page2.next_page_token = None

        tc.get_option_contracts.side_effect = [page1, page2]
        oc.get_option_snapshot.return_value = {
            "AAPL250P170": snap1,
            "AAPL250P165": snap2,
        }
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        # Should have fetched 2 pages
        assert tc.get_option_contracts.call_count == 2
        # Best of the two AAPL contracts (one-per-underlying)
        assert len(result) == 1

    # --- API failure handling ---

    def test_contract_fetch_failure_returns_empty(self):
        """API failure in get_option_contracts returns empty, not crash."""
        tc, oc, sc = _mock_clients()
        tc.get_option_contracts.side_effect = Exception("API error")
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_snapshot_fetch_failure_returns_empty(self):
        """API failure in get_option_snapshot returns empty, not crash."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)

        tc, oc, sc = _mock_clients(contracts=[contract])
        oc.get_option_snapshot.side_effect = Exception("API error")
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    # --- Snapshot edge cases ---

    def test_no_snapshot_for_contract_skipped(self):
        """Contract without a matching snapshot is skipped."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={},  # empty — no snapshot for AAPL250P
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_zero_bid_skipped(self):
        """Contract with zero bid price is skipped."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500)
        snap = _make_mock_snapshot(0.0, 1.0, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    # --- OTM filter ---

    def test_itm_put_filtered_out(self):
        """ITM put (strike > stock price) is rejected."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 180.0, exp, open_interest=500, underlying="AAPL")
        snap = _make_mock_snapshot(12.0, 12.20, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}  # strike 180 > price 170

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_atm_put_filtered_out(self):
        """ATM put (strike == stock price) is rejected."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500, underlying="AAPL")
        snap = _make_mock_snapshot(3.0, 3.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(170.0)}  # strike == price

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert result == []

    def test_otm_put_passes(self):
        """OTM put (strike < stock price) passes the filter."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 165.0, exp, open_interest=500, underlying="AAPL")
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}  # strike 165 < price 175

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1
        assert result[0].strike == 165.0

    def test_no_stock_price_skips_otm_filter(self):
        """Without stock_client, OTM filter is skipped (backward compat)."""
        exp = self._exp_date()
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=500, underlying="AAPL")
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc, oc, _ = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250P": snap},
        )

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=None)
        assert len(result) == 1

    def test_extrinsic_used_for_ranking(self):
        """OTM puts rank by extrinsic premium, not total premium."""
        exp = self._exp_date()
        # Both OTM: stock at 180
        # Contract A: strike 175, bid 3.0 → extrinsic = 3.0 (all extrinsic)
        # Contract B: strike 170, bid 2.5 → extrinsic = 2.5 (all extrinsic)
        c1 = _make_mock_contract("AAPL250P175", 175.0, exp, open_interest=500, underlying="AAPL")
        c2 = _make_mock_contract("MSFT250P170", 170.0, exp, open_interest=500, underlying="MSFT")

        snap1 = _make_mock_snapshot(3.0, 3.10, delta=-0.20)
        snap2 = _make_mock_snapshot(2.5, 2.60, delta=-0.20)

        tc, oc, sc = _mock_clients(
            contracts=[c1, c2],
            snapshots={"AAPL250P175": snap1, "MSFT250P170": snap2},
        )
        sc.get_stock_latest_trade.return_value = {
            "AAPL": _make_mock_trade(180.0),
            "MSFT": _make_mock_trade(180.0),
        }

        result = screen_puts(tc, oc, ["AAPL", "MSFT"], 50000.0, stock_client=sc)
        assert len(result) == 2
        # AAPL has higher extrinsic/strike ratio → ranked first
        assert result[0].underlying == "AAPL"
        assert result[0].extrinsic == 3.0
        assert result[1].extrinsic == 2.5

    # --- Full pipeline ---

    def test_full_pipeline_happy_path(self):
        """Full pipeline: affordable symbol, valid contract, passes all filters."""
        exp = self._exp_date(30)
        contract = _make_mock_contract(
            "AAPL250418P00170000", 170.0, exp, open_interest=500, underlying="AAPL"
        )
        snap = _make_mock_snapshot(2.50, 2.60, delta=-0.22)

        tc, oc, sc = _mock_clients(
            contracts=[contract],
            snapshots={"AAPL250418P00170000": snap},
        )
        sc.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}

        result = screen_puts(tc, oc, ["AAPL"], 50000.0, stock_client=sc)
        assert len(result) == 1
        rec = result[0]
        assert rec.symbol == "AAPL250418P00170000"
        assert rec.underlying == "AAPL"
        assert rec.strike == 170.0
        assert rec.dte == 30
        assert rec.premium == 2.50
        assert rec.extrinsic == 2.50  # OTM: all premium is extrinsic
        assert rec.delta == -0.22
        assert rec.oi == 500
        assert rec.annualized_return == compute_put_annualized_return(2.50, 170.0, 30)


# ---------------------------------------------------------------------------
# render_put_results_table() tests
# ---------------------------------------------------------------------------


class TestRenderPutResultsTable:
    """Tests for the Rich table display function."""

    def _capture(self, recommendations, buying_power=50000.0):
        from rich.console import Console
        from screener.put_screener import render_put_results_table

        buf = StringIO()
        console = Console(file=buf, width=200, force_terminal=True)
        render_put_results_table(recommendations, buying_power, console=console)
        return buf.getvalue()

    def test_empty_shows_message(self):
        output = self._capture([])
        assert "No put recommendations found" in output

    def test_table_renders_with_data(self):
        recs = [
            PutRecommendation(
                symbol="AAPL250418P00170000",
                underlying="AAPL",
                strike=170.0,
                dte=30,
                premium=2.50,
                extrinsic=2.50,
                delta=-0.22,
                oi=500,
                spread=0.04,
                annualized_return=17.89,
            ),
        ]
        output = self._capture(recs)
        assert "Symbol" in output
        assert "Underlying" in output
        assert "Strike" in output
        assert "DTE" in output
        assert "Premium" in output
        assert "Extrinsic" in output
        assert "Delta" in output
        assert "OI" in output
        assert "Spread" in output
        assert "Ann. Return" in output
        assert "AAPL250418P00170000" in output
        assert "AAPL" in output

    def test_multiple_rows_render(self):
        recs = [
            PutRecommendation(
                symbol="AAPL250418P00170000",
                underlying="AAPL",
                strike=170.0,
                dte=30,
                premium=2.50,
                extrinsic=2.50,
                delta=-0.22,
                oi=500,
                spread=0.04,
                annualized_return=17.89,
            ),
            PutRecommendation(
                symbol="MSFT250418P00400000",
                underlying="MSFT",
                strike=400.0,
                dte=45,
                premium=5.00,
                extrinsic=5.00,
                delta=-0.20,
                oi=1000,
                spread=0.02,
                annualized_return=10.14,
            ),
        ]
        output = self._capture(recs)
        assert "AAPL" in output
        assert "MSFT" in output

    def test_delta_none_shows_na(self):
        recs = [
            PutRecommendation(
                symbol="AAPL250418P00170000",
                underlying="AAPL",
                strike=170.0,
                dte=30,
                premium=2.50,
                extrinsic=2.50,
                delta=None,
                oi=500,
                spread=0.04,
                annualized_return=17.89,
            ),
        ]
        output = self._capture(recs)
        assert "N/A" in output

    def test_buying_power_in_title(self):
        output = self._capture([], buying_power=25000.0)
        assert "25" in output
        assert "000" in output
        assert "buying power" in output


# ---------------------------------------------------------------------------
# Preset threshold tests
# ---------------------------------------------------------------------------


class TestPresetThresholds:
    """Verify preset thresholds affect screening results."""

    def _exp_date(self, days=30):
        return date.today() + timedelta(days=days)

    def test_conservative_rejects_what_moderate_accepts(self):
        """Conservative OI/spread thresholds are stricter than moderate."""
        from screener.config_loader import load_preset

        conservative = ScreenerConfig.model_validate(load_preset("conservative"))
        moderate = ScreenerConfig.model_validate(load_preset("moderate"))

        # Verify conservative is stricter
        assert conservative.options.options_oi_min > moderate.options.options_oi_min
        assert conservative.options.options_spread_max < moderate.options.options_spread_max

    def test_conservative_oi_rejects_moderate_oi_contract(self):
        """A contract with OI that passes moderate but fails conservative."""
        from screener.config_loader import load_preset

        conservative = ScreenerConfig.model_validate(load_preset("conservative"))
        moderate = ScreenerConfig.model_validate(load_preset("moderate"))

        exp = self._exp_date()
        # OI=150 — passes moderate (oi_min=100) but fails conservative (oi_min=500)
        contract = _make_mock_contract("AAPL250P", 170.0, exp, open_interest=150, underlying="AAPL")
        snap = _make_mock_snapshot(2.0, 2.10, delta=-0.20)

        tc_m, oc_m, sc_m = _mock_clients(contracts=[contract], snapshots={"AAPL250P": snap})
        sc_m.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}
        result_moderate = screen_puts(tc_m, oc_m, ["AAPL"], 50000.0, config=moderate, stock_client=sc_m)

        tc_c, oc_c, sc_c = _mock_clients(contracts=[contract], snapshots={"AAPL250P": snap})
        sc_c.get_stock_latest_trade.return_value = {"AAPL": _make_mock_trade(175.0)}
        result_conservative = screen_puts(tc_c, oc_c, ["AAPL"], 50000.0, config=conservative, stock_client=sc_c)

        assert len(result_moderate) == 1
        assert len(result_conservative) == 0


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestPutScreenerCLI:
    """Tests for the run-put-screener CLI entry point."""

    def test_cli_help(self):
        from typer.testing import CliRunner
        from scripts.run_put_screener import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--buying-power" in result.output
        assert "--preset" in result.output
        assert "--config" in result.output
        assert "SYMBOLS" in result.output

    @patch("scripts.run_put_screener.create_broker_client")
    @patch("scripts.run_put_screener.screen_puts", return_value=[])
    @patch("scripts.run_put_screener.render_put_results_table")
    @patch("scripts.run_put_screener.load_config")
    def test_cli_symbol_uppercased(self, mock_config, mock_render, mock_screen, mock_broker):
        from typer.testing import CliRunner
        from scripts.run_put_screener import app

        mock_config.return_value = ScreenerConfig()
        mock_broker.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(app, ["aapl", "msft", "--buying-power", "50000"])
        assert result.exit_code == 0
        # Check symbols were uppercased
        call_args = mock_screen.call_args
        symbols_arg = call_args[0][2]  # 3rd positional arg
        assert symbols_arg == ["AAPL", "MSFT"]

    @patch("scripts.run_put_screener.create_broker_client")
    @patch("scripts.run_put_screener.screen_puts", return_value=[])
    @patch("scripts.run_put_screener.render_put_results_table")
    @patch("scripts.run_put_screener.load_preset")
    def test_cli_preset_override(self, mock_load_preset, mock_render, mock_screen, mock_broker):
        from typer.testing import CliRunner
        from scripts.run_put_screener import app

        mock_load_preset.return_value = {"preset": "conservative"}
        mock_broker.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(app, ["AAPL", "--buying-power", "50000", "--preset", "conservative"])
        assert result.exit_code == 0
        mock_load_preset.assert_called_once_with("conservative")
