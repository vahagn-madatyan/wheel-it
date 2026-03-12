"""Tests for core.cli_common and screener.export modules."""

import importlib
from io import StringIO

import pytest
from rich.console import Console


# ── cli_common tests ──────────────────────────────────────────────────────────


def test_cli_common_returns_credentials_when_set(monkeypatch):
    """require_alpaca_credentials returns (key, secret, is_paper) when env vars are set."""
    monkeypatch.setenv("ALPACA_API_KEY", "test-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setenv("IS_PAPER", "true")

    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(creds_mod, "IS_PAPER", True)

    from core.cli_common import require_alpaca_credentials

    # Re-import to pick up patched values
    import core.cli_common as cli_mod

    importlib.reload(cli_mod)
    key, secret, is_paper = cli_mod.require_alpaca_credentials()
    assert key == "test-key"
    assert secret == "test-secret"
    assert is_paper is True


def test_cli_common_exits_when_api_key_missing(monkeypatch):
    """require_alpaca_credentials raises SystemExit when ALPACA_API_KEY is missing."""
    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", None)
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", "test-secret")

    import core.cli_common as cli_mod

    importlib.reload(cli_mod)
    with pytest.raises(SystemExit, match="ALPACA_API_KEY"):
        cli_mod.require_alpaca_credentials()


def test_cli_common_exits_when_secret_key_missing(monkeypatch):
    """require_alpaca_credentials raises SystemExit when ALPACA_SECRET_KEY is missing."""
    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", None)

    import core.cli_common as cli_mod

    importlib.reload(cli_mod)
    with pytest.raises(SystemExit, match="ALPACA_SECRET_KEY"):
        cli_mod.require_alpaca_credentials()


def test_cli_common_create_broker_client(monkeypatch):
    """create_broker_client returns a BrokerClient when credentials are valid."""
    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(creds_mod, "IS_PAPER", True)

    # Mock BrokerClient to avoid real API calls
    class MockBrokerClient:
        def __init__(self, api_key, secret_key, paper):
            self.api_key = api_key
            self.secret_key = secret_key
            self.paper = paper

    import core.cli_common as cli_mod
    import core.broker_client as bc_mod

    monkeypatch.setattr(bc_mod, "BrokerClient", MockBrokerClient)
    importlib.reload(cli_mod)

    client = cli_mod.create_broker_client()
    assert client.api_key == "test-key"
    assert client.secret_key == "test-secret"
    assert client.paper is True


# ── export tests ──────────────────────────────────────────────────────────────

from screener.export import get_protected_symbols, export_symbols


def test_get_protected_symbols():
    """get_protected_symbols returns dict mapping symbol to state type string."""
    fake_positions = ["pos1", "pos2"]

    def mock_update_state(positions):
        return {
            "AAPL": {"type": "short_put", "price": None},
            "MSFT": {"type": "long_shares", "price": 350.0, "qty": 100},
        }

    result = get_protected_symbols(fake_positions, mock_update_state)
    assert result == {"AAPL": "short_put", "MSFT": "long_shares"}


def test_export_writes_file(tmp_path):
    """export_symbols writes sorted symbols to file with trailing newline."""
    path = tmp_path / "symbol_list.txt"
    buf = StringIO()
    console = Console(file=buf, highlight=False)

    result = export_symbols(
        screened=["NVDA", "AMD", "AAPL"],
        protected={},
        path=path,
        console=console,
    )

    assert result is True
    content = path.read_text()
    assert content == "AAPL\nAMD\nNVDA\n"


def test_protected_symbols_kept(tmp_path):
    """Protected symbols remain in file even when not in screened list."""
    path = tmp_path / "symbol_list.txt"
    path.write_text("AAPL\nMSFT\nNVDA\n")

    buf = StringIO()
    console = Console(file=buf, highlight=False)

    # MSFT has active position but is NOT in screened list
    result = export_symbols(
        screened=["AAPL", "AMD"],
        protected={"MSFT": "short_put"},
        path=path,
        console=console,
    )

    assert result is True
    content = path.read_text()
    symbols = content.strip().split("\n")
    assert "MSFT" in symbols
    assert "AAPL" in symbols
    assert "AMD" in symbols
    # NVDA was in current file but not screened or protected -- removed
    assert "NVDA" not in symbols


def test_zero_results_skips_write(tmp_path):
    """Empty screened + empty protected returns False, file not modified."""
    path = tmp_path / "symbol_list.txt"
    path.write_text("AAPL\nMSFT\n")

    buf = StringIO()
    console = Console(file=buf, highlight=False)

    result = export_symbols(
        screened=[],
        protected={},
        path=path,
        console=console,
    )

    assert result is False
    # File should remain unchanged
    assert path.read_text() == "AAPL\nMSFT\n"

    output = buf.getvalue()
    assert "0 passing stocks" in output


def test_diff_display(tmp_path):
    """Diff output shows green/red/yellow markup for added/removed/protected symbols."""
    path = tmp_path / "symbol_list.txt"
    path.write_text("AAPL\nINTC\nMSFT\n")

    buf = StringIO()
    console = Console(file=buf, highlight=False, force_terminal=True)

    export_symbols(
        screened=["AAPL", "NVDA"],
        protected={"MSFT": "short_put"},
        path=path,
        console=console,
    )

    output = buf.getvalue()
    # Added symbol
    assert "+NVDA" in output
    # Removed symbol
    assert "-INTC" in output
    assert "screened out" in output
    # Protected symbol
    assert "~MSFT" in output
    assert "kept" in output
    assert "active short put" in output


def test_existing_file_merged(tmp_path):
    """Existing file symbols are merged with screened + protected correctly."""
    path = tmp_path / "symbol_list.txt"
    path.write_text("AAPL\nGOOG\nINTC\n")

    buf = StringIO()
    console = Console(file=buf, highlight=False)

    result = export_symbols(
        screened=["AAPL", "AMD", "NVDA"],
        protected={"GOOG": "short_call"},
        path=path,
        console=console,
    )

    assert result is True
    content = path.read_text()
    symbols = content.strip().split("\n")
    # AAPL: in both screened and current -> kept
    assert "AAPL" in symbols
    # AMD: new from screened -> added
    assert "AMD" in symbols
    # NVDA: new from screened -> added
    assert "NVDA" in symbols
    # GOOG: protected (active short_call) -> kept
    assert "GOOG" in symbols
    # INTC: in current but not screened or protected -> removed
    assert "INTC" not in symbols
    # File should be sorted
    assert symbols == sorted(symbols)


def test_empty_screened_but_protected_writes(tmp_path):
    """Empty screened list but protected symbols still writes protected symbols."""
    path = tmp_path / "symbol_list.txt"

    buf = StringIO()
    console = Console(file=buf, highlight=False)

    result = export_symbols(
        screened=[],
        protected={"AAPL": "long_shares", "MSFT": "short_call"},
        path=path,
        console=console,
    )

    assert result is True
    content = path.read_text()
    assert content == "AAPL\nMSFT\n"
