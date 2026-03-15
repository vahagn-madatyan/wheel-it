"""Tests for S10: Covered Call Screening + Strategy Integration.

Covers:
- compute_call_annualized_return() math and edge cases
- screen_calls() filtering: strike >= cost basis, OI, spread, delta
- screen_calls() ranking by annualized return
- screen_calls() error handling (API failures, no contracts)
- CallRecommendation dataclass fields
- render_call_results_table() Rich table output
- run-call-screener CLI entry point
- run-strategy integration: call screener replaces old sell_calls for assigned positions
- Preset thresholds applied to call screening
"""

from datetime import date, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch, call

import pytest

from screener.call_screener import (
    CallRecommendation,
    compute_call_annualized_return,
    render_call_results_table,
    screen_calls,
    _CALL_DTE_MIN,
    _CALL_DTE_MAX,
)
from screener.config_loader import ScreenerConfig, load_preset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_config(**overrides) -> ScreenerConfig:
    """Create a ScreenerConfig with defaults, applying overrides."""
    return ScreenerConfig.model_validate(overrides) if overrides else ScreenerConfig()


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


def _mock_clients(contracts=None, snapshots=None):
    """Create mock trade_client and option_client pair."""
    trade_client = MagicMock()
    option_client = MagicMock()

    response = MagicMock()
    response.option_contracts = contracts or []
    trade_client.get_option_contracts.return_value = response

    option_client.get_option_snapshot.return_value = snapshots or {}

    return trade_client, option_client


# ===========================================================================
# TestComputeCallAnnualizedReturn
# ===========================================================================


class TestComputeCallAnnualizedReturn:
    """compute_call_annualized_return: annualized return math."""

    def test_basic_return(self):
        # premium=2.00, cost_basis=100, DTE=30
        # return = (2.00/100) * (365/30) * 100 = 2% * 12.17 = 24.33%
        result = compute_call_annualized_return(2.00, 100.0, 30)
        assert result is not None
        assert result == pytest.approx(24.33, abs=0.1)

    def test_low_premium(self):
        # premium=0.50, cost_basis=200, DTE=45
        # return = (0.50/200) * (365/45) * 100 = 0.25% * 8.11 = 2.03%
        result = compute_call_annualized_return(0.50, 200.0, 45)
        assert result is not None
        assert result == pytest.approx(2.03, abs=0.1)

    def test_high_premium(self):
        # premium=10.00, cost_basis=50, DTE=14
        # return = (10.00/50) * (365/14) * 100 = 20% * 26.07 = 521.43%
        result = compute_call_annualized_return(10.00, 50.0, 14)
        assert result is not None
        assert result == pytest.approx(521.43, abs=0.1)

    def test_zero_cost_basis_returns_none(self):
        result = compute_call_annualized_return(2.00, 0.0, 30)
        assert result is None

    def test_zero_dte_returns_none(self):
        result = compute_call_annualized_return(2.00, 100.0, 0)
        assert result is None

    def test_negative_premium_returns_none(self):
        result = compute_call_annualized_return(-1.00, 100.0, 30)
        assert result is None

    def test_zero_premium_returns_zero(self):
        result = compute_call_annualized_return(0.0, 100.0, 30)
        assert result is not None
        assert result == 0.0

    def test_negative_cost_basis_returns_none(self):
        result = compute_call_annualized_return(2.00, -100.0, 30)
        assert result is None


# ===========================================================================
# TestCallRecommendation
# ===========================================================================


class TestCallRecommendation:
    """CallRecommendation dataclass structure."""

    def test_all_fields_present(self):
        rec = CallRecommendation(
            symbol="AAPL260401C00180000",
            underlying="AAPL",
            strike=180.0,
            dte=30,
            premium=3.50,
            delta=0.25,
            oi=500,
            spread=0.03,
            annualized_return=23.6,
            cost_basis=175.0,
        )
        assert rec.symbol == "AAPL260401C00180000"
        assert rec.underlying == "AAPL"
        assert rec.strike == 180.0
        assert rec.dte == 30
        assert rec.premium == 3.50
        assert rec.delta == 0.25
        assert rec.oi == 500
        assert rec.spread == 0.03
        assert rec.annualized_return == 23.6
        assert rec.cost_basis == 175.0

    def test_delta_none_allowed(self):
        rec = CallRecommendation(
            symbol="TEST",
            underlying="TEST",
            strike=50.0,
            dte=30,
            premium=1.0,
            delta=None,
            oi=100,
            spread=0.05,
            annualized_return=24.3,
            cost_basis=45.0,
        )
        assert rec.delta is None


# ===========================================================================
# TestScreenCalls
# ===========================================================================


class TestScreenCalls:
    """screen_calls: core screening logic."""

    def _standard_exp_date(self):
        return date.today() + timedelta(days=30)

    def test_basic_screening_returns_recommendation(self):
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("AAPL260401C00180000", 180.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"AAPL260401C00180000": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 1
        assert results[0].symbol == "AAPL260401C00180000"
        assert results[0].strike == 180.0
        assert results[0].premium == 3.50
        assert results[0].delta == 0.25
        assert results[0].annualized_return > 0
        assert results[0].cost_basis == 175.0

    def test_strike_below_cost_basis_excluded(self):
        """Contracts with strike < cost basis must be excluded."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("LOW", 170.0, exp, 500),   # below cost basis
            _make_mock_contract("HIGH", 180.0, exp, 500),  # above cost basis
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={
                "LOW": snap,
                "HIGH": snap,
            },
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 1
        assert results[0].symbol == "HIGH"
        assert results[0].strike == 180.0

    def test_strike_equal_to_cost_basis_included(self):
        """Contract with strike == cost basis should pass."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("EXACT", 175.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=2.00, ask_price=2.10, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"EXACT": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 1
        assert results[0].strike == 175.0

    def test_low_oi_excluded(self):
        """Contracts with OI below threshold are excluded."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("LOW_OI", 180.0, exp, open_interest=10),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"LOW_OI": snap},
        )
        config = _default_config()  # options_oi_min=100

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0, config=config,
        )

        assert len(results) == 0

    def test_wide_spread_excluded(self):
        """Contracts with spread above threshold are excluded."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("WIDE", 180.0, exp, 500),
        ]
        # bid=1.00, ask=2.00 → midpoint=1.50 → spread=66.7%
        snap = _make_mock_snapshot(bid_price=1.00, ask_price=2.00, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"WIDE": snap},
        )
        config = _default_config()  # options_spread_max=0.10

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0, config=config,
        )

        assert len(results) == 0

    def test_delta_below_min_excluded(self):
        """Contracts with delta below DELTA_MIN are excluded."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("LOW_DELTA", 180.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.05)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"LOW_DELTA": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 0

    def test_delta_above_max_excluded(self):
        """Contracts with delta above DELTA_MAX are excluded."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("HIGH_DELTA", 180.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.50)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"HIGH_DELTA": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 0

    def test_no_greeks_contract_passes_delta_filter(self):
        """Contract with no greeks data should pass delta filter."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("NO_GREEKS", 180.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=None)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"NO_GREEKS": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 1
        assert results[0].delta is None

    def test_sorted_by_annualized_return_descending(self):
        """Results should be sorted by annualized return, best first."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("C1", 180.0, exp, 500),
            _make_mock_contract("C2", 185.0, exp, 500),
            _make_mock_contract("C3", 190.0, exp, 500),
        ]
        # Higher bid → higher return
        snaps = {
            "C1": _make_mock_snapshot(bid_price=5.00, ask_price=5.10, delta=0.25),
            "C2": _make_mock_snapshot(bid_price=3.00, ask_price=3.10, delta=0.20),
            "C3": _make_mock_snapshot(bid_price=1.50, ask_price=1.55, delta=0.15),
        }
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots=snaps,
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert len(results) == 3
        assert results[0].annualized_return >= results[1].annualized_return
        assert results[1].annualized_return >= results[2].annualized_return
        assert results[0].symbol == "C1"

    def test_no_contracts_returns_empty(self):
        trade_client, option_client = _mock_clients(contracts=[], snapshots={})

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert results == []

    def test_all_below_cost_basis_returns_empty(self):
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("C1", 150.0, exp, 500),
            _make_mock_contract("C2", 160.0, exp, 500),
        ]
        trade_client, option_client = _mock_clients(contracts=contracts)

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert results == []

    def test_api_exception_returns_empty(self):
        trade_client = MagicMock()
        option_client = MagicMock()
        trade_client.get_option_contracts.side_effect = Exception("API error")

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert results == []

    def test_snapshot_fetch_exception_returns_empty(self):
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("C1", 180.0, exp, 500),
        ]
        trade_client, option_client = _mock_clients(contracts=contracts)
        option_client.get_option_snapshot.side_effect = Exception("Snapshot error")

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert results == []

    def test_missing_snapshot_for_contract_skipped(self):
        """Contract whose symbol isn't in snapshot dict should be skipped."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("MISSING", 180.0, exp, 500),
        ]
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={},  # no snapshot for MISSING
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert results == []

    def test_zero_bid_excluded(self):
        """Contracts with bid <= 0 should be excluded."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("ZERO_BID", 180.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=0.0, ask_price=0.10, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"ZERO_BID": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        assert results == []

    def test_uses_default_config_when_none(self):
        """screen_calls with config=None should use default ScreenerConfig."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("C1", 180.0, exp, 500),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"C1": snap},
        )

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0, config=None,
        )

        assert len(results) == 1

    def test_preset_thresholds_applied(self):
        """Conservative preset with high OI min should reject low-OI contracts."""
        exp = self._standard_exp_date()
        contracts = [
            _make_mock_contract("C1", 180.0, exp, open_interest=200),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"C1": snap},
        )

        # Conservative requires OI >= 500
        config = ScreenerConfig.model_validate({
            "preset": "conservative",
            "options": {"options_oi_min": 500, "options_spread_max": 0.05},
        })

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0, config=config,
        )

        assert len(results) == 0


# ===========================================================================
# TestDTERange
# ===========================================================================


class TestDTERange:
    """DTE range constants match put screener convention."""

    def test_dte_range_values(self):
        assert _CALL_DTE_MIN == 14
        assert _CALL_DTE_MAX == 60


# ===========================================================================
# TestRenderCallResultsTable
# ===========================================================================


class TestRenderCallResultsTable:
    """render_call_results_table: Rich table output."""

    def test_table_renders_with_data(self):
        from rich.console import Console

        recs = [
            CallRecommendation(
                symbol="AAPL260401C00180000",
                underlying="AAPL",
                strike=180.0,
                dte=30,
                premium=3.50,
                delta=0.250,
                oi=500,
                spread=0.028,
                annualized_return=24.3,
                cost_basis=175.0,
            ),
        ]

        buf = StringIO()
        console = Console(file=buf, width=200)
        render_call_results_table(recs, "AAPL", 175.0, console=console)
        output = buf.getvalue()

        assert "AAPL" in output
        assert "175.00" in output
        assert "$180.00" in output
        assert "30" in output
        assert "$3.50" in output
        assert "0.250" in output
        assert "500" in output
        assert "24.3%" in output

    def test_table_empty_shows_message(self):
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, width=200)
        render_call_results_table([], "AAPL", 175.0, console=console)
        output = buf.getvalue()

        assert "No covered call recommendations" in output
        assert "AAPL" in output
        assert "175.00" in output

    def test_table_delta_none_shows_na(self):
        from rich.console import Console

        recs = [
            CallRecommendation(
                symbol="TEST",
                underlying="TEST",
                strike=50.0,
                dte=30,
                premium=1.00,
                delta=None,
                oi=200,
                spread=0.05,
                annualized_return=24.3,
                cost_basis=45.0,
            ),
        ]

        buf = StringIO()
        console = Console(file=buf, width=200)
        render_call_results_table(recs, "TEST", 45.0, console=console)
        output = buf.getvalue()

        assert "N/A" in output

    def test_table_multiple_rows(self):
        from rich.console import Console

        recs = [
            CallRecommendation(
                symbol=f"C{i}",
                underlying="AAPL",
                strike=180.0 + i * 5,
                dte=30,
                premium=5.0 - i,
                delta=0.25 - i * 0.05,
                oi=500,
                spread=0.03,
                annualized_return=30.0 - i * 5,
                cost_basis=175.0,
            )
            for i in range(3)
        ]

        buf = StringIO()
        console = Console(file=buf, width=200)
        render_call_results_table(recs, "AAPL", 175.0, console=console)
        output = buf.getvalue()

        assert "C0" in output
        assert "C1" in output
        assert "C2" in output


# ===========================================================================
# TestRunCallScreenerCLI
# ===========================================================================


class TestRunCallScreenerCLI:
    """run-call-screener CLI entry point."""

    @patch("scripts.run_call_screener.create_broker_client")
    @patch("scripts.run_call_screener.screen_calls")
    @patch("scripts.run_call_screener.render_call_results_table")
    @patch("scripts.run_call_screener.load_config")
    def test_cli_invokes_screen_calls(
        self, mock_config, mock_render, mock_screen, mock_broker
    ):
        from typer.testing import CliRunner
        from scripts.run_call_screener import app

        mock_config.return_value = ScreenerConfig()
        mock_broker.return_value = MagicMock()
        mock_screen.return_value = []

        runner = CliRunner()
        result = runner.invoke(app, ["AAPL", "--cost-basis", "175.0"])

        assert result.exit_code == 0
        mock_screen.assert_called_once()
        args = mock_screen.call_args
        assert args[0][2] == "AAPL"
        assert args[0][3] == 175.0

    @patch("scripts.run_call_screener.create_broker_client")
    @patch("scripts.run_call_screener.screen_calls")
    @patch("scripts.run_call_screener.render_call_results_table")
    @patch("scripts.run_call_screener.load_config")
    def test_cli_symbol_uppercased(
        self, mock_config, mock_render, mock_screen, mock_broker
    ):
        from typer.testing import CliRunner
        from scripts.run_call_screener import app

        mock_config.return_value = ScreenerConfig()
        mock_broker.return_value = MagicMock()
        mock_screen.return_value = []

        runner = CliRunner()
        result = runner.invoke(app, ["aapl", "--cost-basis", "175.0"])

        assert result.exit_code == 0
        args = mock_screen.call_args
        assert args[0][2] == "AAPL"

    @patch("scripts.run_call_screener.create_broker_client")
    @patch("scripts.run_call_screener.screen_calls")
    @patch("scripts.run_call_screener.render_call_results_table")
    @patch("scripts.run_call_screener.load_preset")
    def test_cli_preset_override(
        self, mock_preset, mock_render, mock_screen, mock_broker
    ):
        from typer.testing import CliRunner
        from scripts.run_call_screener import app

        mock_preset.return_value = load_preset("conservative")
        mock_broker.return_value = MagicMock()
        mock_screen.return_value = []

        runner = CliRunner()
        result = runner.invoke(
            app, ["AAPL", "--cost-basis", "175.0", "--preset", "conservative"]
        )

        assert result.exit_code == 0
        mock_preset.assert_called_with("conservative")


# ===========================================================================
# TestStrategyIntegration
# ===========================================================================


class TestStrategyIntegration:
    """run-strategy integrates call screener for assigned positions."""

    def _make_position(self, symbol, qty, avg_entry_price, asset_class):
        """Create a mock Alpaca position."""
        pos = MagicMock()
        pos.symbol = symbol
        pos.qty = str(qty)
        pos.avg_entry_price = str(avg_entry_price)
        pos.asset_class = asset_class
        return pos

    @patch("scripts.run_strategy.screen_calls")
    @patch("scripts.run_strategy.load_config")
    @patch("scripts.run_strategy.screen_puts", return_value=[])
    @patch("scripts.run_strategy.update_state")
    @patch("scripts.run_strategy.calculate_risk")
    def test_long_shares_triggers_call_screener(
        self, mock_risk, mock_state, mock_puts, mock_cfg, mock_screen
    ):
        """When state is long_shares, screen_calls should be invoked."""
        from alpaca.trading.enums import AssetClass

        mock_risk.return_value = 10000
        mock_state.return_value = {
            "AAPL": {"type": "long_shares", "price": 175.0, "qty": 100},
        }
        mock_cfg.return_value = ScreenerConfig()

        best_call = CallRecommendation(
            symbol="AAPL260401C00180000",
            underlying="AAPL",
            strike=180.0,
            dte=30,
            premium=3.50,
            delta=0.25,
            oi=500,
            spread=0.03,
            annualized_return=24.3,
            cost_basis=175.0,
        )
        mock_screen.return_value = [best_call]

        # Mock BrokerClient
        mock_client = MagicMock()
        mock_client.get_positions.return_value = [
            self._make_position("AAPL", 100, 175.0, AssetClass.US_EQUITY),
        ]

        # Import and invoke
        with patch("scripts.run_strategy.BrokerClient", return_value=mock_client):
            with patch("scripts.run_strategy.StrategyLogger") as mock_logger_cls:
                mock_logger = MagicMock()
                mock_logger_cls.return_value = mock_logger

                with patch("scripts.run_strategy.setup_logger"):
                    with patch("builtins.open", MagicMock(
                        return_value=MagicMock(
                            __enter__=MagicMock(return_value=MagicMock(
                                readlines=MagicMock(return_value=["AAPL\n"])
                            )),
                            __exit__=MagicMock(return_value=False),
                        )
                    )):
                        from scripts.run_strategy import app
                        from typer.testing import CliRunner

                        runner = CliRunner()
                        result = runner.invoke(app)

        # Verify screen_calls was called with AAPL and cost basis
        mock_screen.assert_called_once()
        sc_args = mock_screen.call_args
        assert sc_args[0][2] == "AAPL"
        assert sc_args[0][3] == 175.0

        # Verify market_sell was called with the best recommendation
        mock_client.market_sell.assert_called_with("AAPL260401C00180000")

    @patch("scripts.run_strategy.screen_calls")
    @patch("scripts.run_strategy.load_config")
    @patch("scripts.run_strategy.screen_puts", return_value=[])
    @patch("scripts.run_strategy.update_state")
    @patch("scripts.run_strategy.calculate_risk")
    def test_no_recommendations_does_not_sell(
        self, mock_risk, mock_state, mock_puts, mock_cfg, mock_screen
    ):
        """When screen_calls returns empty, no order should be placed."""
        mock_risk.return_value = 10000
        mock_state.return_value = {
            "AAPL": {"type": "long_shares", "price": 175.0, "qty": 100},
        }
        mock_cfg.return_value = ScreenerConfig()
        mock_screen.return_value = []

        mock_client = MagicMock()
        mock_client.get_positions.return_value = []

        with patch("scripts.run_strategy.BrokerClient", return_value=mock_client):
            with patch("scripts.run_strategy.StrategyLogger") as mock_logger_cls:
                mock_logger = MagicMock()
                mock_logger_cls.return_value = mock_logger

                with patch("scripts.run_strategy.setup_logger"):
                    with patch("builtins.open", MagicMock(
                        return_value=MagicMock(
                            __enter__=MagicMock(return_value=MagicMock(
                                readlines=MagicMock(return_value=["AAPL\n"])
                            )),
                            __exit__=MagicMock(return_value=False),
                        )
                    )):
                        from scripts.run_strategy import app
                        from typer.testing import CliRunner

                        runner = CliRunner()
                        result = runner.invoke(app)

        # No sell order placed
        mock_client.market_sell.assert_not_called()

    @patch("scripts.run_strategy.screen_calls")
    @patch("scripts.run_strategy.load_config")
    @patch("scripts.run_strategy.screen_puts", return_value=[])
    @patch("scripts.run_strategy.update_state")
    @patch("scripts.run_strategy.calculate_risk")
    def test_insufficient_shares_skips_call_screening(
        self, mock_risk, mock_state, mock_puts, mock_cfg, mock_screen
    ):
        """When fewer than 100 shares, call screening should be skipped."""
        mock_risk.return_value = 10000
        mock_state.return_value = {
            "AAPL": {"type": "long_shares", "price": 175.0, "qty": 50},
        }
        mock_cfg.return_value = ScreenerConfig()

        mock_client = MagicMock()
        mock_client.get_positions.return_value = []

        with patch("scripts.run_strategy.BrokerClient", return_value=mock_client):
            with patch("scripts.run_strategy.StrategyLogger") as mock_logger_cls:
                mock_logger = MagicMock()
                mock_logger_cls.return_value = mock_logger

                with patch("scripts.run_strategy.setup_logger"):
                    with patch("builtins.open", MagicMock(
                        return_value=MagicMock(
                            __enter__=MagicMock(return_value=MagicMock(
                                readlines=MagicMock(return_value=["AAPL\n"])
                            )),
                            __exit__=MagicMock(return_value=False),
                        )
                    )):
                        from scripts.run_strategy import app
                        from typer.testing import CliRunner

                        runner = CliRunner()
                        result = runner.invoke(app)

        # screen_calls should NOT be called for insufficient shares
        mock_screen.assert_not_called()


# ===========================================================================
# TestPresetThresholdsForCalls
# ===========================================================================


class TestPresetThresholdsForCalls:
    """Presets apply correctly to call screening via shared ScreenerConfig."""

    def test_conservative_strict_thresholds(self):
        config = ScreenerConfig.model_validate(load_preset("conservative"))
        assert config.options.options_oi_min == 500
        assert config.options.options_spread_max == 0.05

    def test_moderate_thresholds(self):
        config = ScreenerConfig.model_validate(load_preset("moderate"))
        assert config.options.options_oi_min == 100
        assert config.options.options_spread_max == 0.10

    def test_aggressive_loose_thresholds(self):
        config = ScreenerConfig.model_validate(load_preset("aggressive"))
        assert config.options.options_oi_min == 50
        assert config.options.options_spread_max == 0.20

    def test_conservative_rejects_moderate_oi(self):
        """Conservative OI threshold should reject contracts that moderate accepts."""
        exp = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("C1", 180.0, exp, open_interest=200),
        ]
        snap = _make_mock_snapshot(bid_price=3.50, ask_price=3.55, delta=0.25)
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"C1": snap},
        )

        # Moderate accepts (OI 200 >= 100)
        moderate = ScreenerConfig.model_validate(load_preset("moderate"))
        mod_results = screen_calls(
            trade_client, option_client, "AAPL", 175.0, config=moderate,
        )

        # Reset mocks
        trade_client, option_client = _mock_clients(
            contracts=contracts,
            snapshots={"C1": snap},
        )

        # Conservative rejects (OI 200 < 500)
        conservative = ScreenerConfig.model_validate(load_preset("conservative"))
        con_results = screen_calls(
            trade_client, option_client, "AAPL", 175.0, config=conservative,
        )

        assert len(mod_results) == 1
        assert len(con_results) == 0


# ===========================================================================
# TestSnapshotBatching
# ===========================================================================


class TestSnapshotBatching:
    """Snapshot fetching handles large contract lists via batching."""

    def test_batching_over_100_contracts(self):
        """Contracts > 100 should be fetched in batches of 100."""
        exp = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract(f"C{i}", 180.0 + i, exp, 500)
            for i in range(150)
        ]

        trade_client = MagicMock()
        option_client = MagicMock()

        response = MagicMock()
        response.option_contracts = contracts
        trade_client.get_option_contracts.return_value = response

        # Return a snapshot for each contract
        def make_snaps(req):
            symbols = req.symbol_or_symbols
            return {
                s: _make_mock_snapshot(bid_price=3.50, ask_price=3.60, delta=0.25)
                for s in (symbols if isinstance(symbols, list) else [symbols])
            }

        option_client.get_option_snapshot.side_effect = make_snaps

        results = screen_calls(
            trade_client, option_client, "AAPL", 175.0,
        )

        # Should have called get_option_snapshot twice (100 + 50)
        assert option_client.get_option_snapshot.call_count == 2
        assert len(results) > 0
