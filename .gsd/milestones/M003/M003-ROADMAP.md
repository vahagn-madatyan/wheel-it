# M003: Modern Put Screener + Legacy Cleanup

**Vision:** Replace the legacy `sell_puts()` path in `run-strategy` with a modern `screen_puts()` function that mirrors `call_screener.py` — using preset-configurable thresholds, DTE 14–60 days, annualized return ranking, OI/spread/delta filters, and buying power pre-filtering — then wire it into the strategy bot and clean up the dead legacy code (`core/strategy.py`, `core/execution.py:sell_puts`, `models/contract.py`, and obsolete `config/params.py` constants).

## Success Criteria

- Running `run-strategy` on a fresh account uses `screen_puts()` to select put contracts with preset-configurable OI/spread/delta thresholds and DTE 14–60 days
- Running `run-strategy` with no affordable symbols (buying power below any symbol's price × 100) logs clearly and returns an empty list instead of crashing
- A new `run-put-screener` CLI lets the user explore put opportunities for a list of symbols with Rich table output showing strike, DTE, premium, delta, OI, spread, and annualized return
- The legacy `core/strategy.py`, `core/execution.py:sell_puts`, and `models/contract.py` are removed with no test failures
- Obsolete constants in `config/params.py` (`YIELD_MIN`, `YIELD_MAX`, `SCORE_MIN`, `OPEN_INTEREST_MIN`, `EXPIRATION_MIN`, `EXPIRATION_MAX`) are removed
- All 368+ existing tests continue to pass, plus new tests covering put screening logic, CLI, and strategy integration
- One-per-underlying diversification rule is enforced: at most one put contract per underlying symbol is recommended

## Key Risks / Unknowns

- Multi-symbol contract pagination — fetching contracts for 20+ symbols may exceed Alpaca's 1000 per-page limit, requiring pagination logic that the call screener (single-symbol) does not need
- Buying power pre-filter requires a separate `get_stock_latest_trade()` API call — failure handling must not crash the strategy run

## Proof Strategy

- Multi-symbol pagination → retire in S01 by building `screen_puts()` with pagination and testing it with mock data exceeding 1000 contracts
- Legacy removal safety → retire in S03 by removing all legacy modules and confirming 368+ existing tests still pass

## Verification Classes

- Contract verification: pytest tests for put screening math, filter pipeline, one-per-underlying selection, buying power pre-filter, pagination, CLI flag parsing, display columns, strategy integration, backward compatibility
- Integration verification: `run-strategy` and `run-put-screener` against live Alpaca APIs producing real put recommendations
- Operational verification: none (batch CLI tool)
- UAT / human verification: user runs `run-put-screener AAPL MSFT GOOG --buying-power 50000` and sees ranked recommendations; user runs `run-strategy` and confirms put selection uses new screener

## Milestone Definition of Done

This milestone is complete only when all are true:

- `screen_puts()` produces ranked `PutRecommendation` objects using preset-configurable thresholds
- `run-strategy` uses `screen_puts()` instead of `sell_puts()` for the put-selling leg
- `run-put-screener` CLI displays put recommendations in a Rich table
- `core/strategy.py`, `core/execution.py:sell_puts`, `core/execution.py:sell_calls`, and `models/contract.py` are deleted
- Obsolete `config/params.py` constants are removed
- `CLAUDE.md` is updated to reflect the new architecture
- All tests pass (368+ existing + new put screener tests)
- Success criteria are re-checked against the test suite, not just artifact existence

## Requirement Coverage

- Covers: none (no Active requirements — all 31 validated requirements are from M001/M002)
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — `REQUIREMENTS.md` has 0 Active requirements. This milestone is an internally-motivated modernization completing the wheel strategy's put leg to match the call leg's quality.

**Note:** `REQUIREMENTS.md` has no Active requirements. This milestone operates in legacy compatibility mode — requirements will be defined as part of this planning if the user adds them. The scope is driven by the S01 research findings and the natural next step of replacing the last legacy code path.

## Slices

- [x] **S01: Put Screener Module** `risk:medium` `depends:[]`
  > After this: `screen_puts(trade_client, option_client, ["AAPL", "MSFT"], 50000.0, config)` returns a sorted list of `PutRecommendation` objects — one per underlying, ranked by annualized return — with buying power pre-filtering, OI/spread/delta filters, and multi-symbol pagination all working. Verified by 40+ unit tests covering math, filtering, pagination, one-per-underlying selection, and edge cases.

- [x] **S02: Put Screener CLI + Strategy Integration** `risk:medium` `depends:[S01]`
  > After this: User runs `run-put-screener AAPL MSFT GOOG --buying-power 50000` and sees a Rich table of put recommendations. Running `run-strategy` uses `screen_puts()` for the put-selling leg instead of the legacy `sell_puts()` path. Verified by CLI tests and strategy integration tests.

- [ ] **S03: Legacy Code Removal + Docs Update** `risk:low` `depends:[S02]`
  > After this: `core/strategy.py`, the `sell_puts()` and `sell_calls()` functions in `core/execution.py`, `models/contract.py`, and obsolete constants in `config/params.py` are deleted. `core/execution.py` is either empty (deleted) or contains only non-dead code. `CLAUDE.md` and `README.md` reflect the new architecture. All 368+ existing tests still pass.

- [ ] **S04: End-to-End Strategy Verification** `risk:low` `depends:[S03]`
  > After this: `run-strategy` exercises the complete wheel cycle — detecting positions via `update_state()`, selling covered calls via `screen_calls()` for `long_shares`, and selling cash-secured puts via `screen_puts()` for allowed symbols — with all legacy code removed. Verified by running `run-strategy --help` to confirm CLI works, examining strategy integration tests, and confirming all tests pass with zero imports from deleted modules.

## Boundary Map

### S01 → S02

Produces:
- `screener/put_screener.py` → `screen_puts(trade_client, option_client, symbols, buying_power, config?)` returning `list[PutRecommendation]`
- `screener/put_screener.py` → `PutRecommendation` dataclass with fields: `symbol`, `underlying`, `strike`, `dte`, `premium`, `delta`, `oi`, `spread`, `annualized_return`
- `screener/put_screener.py` → `compute_put_annualized_return(premium, strike, dte)` returning `Optional[float]`
- `screener/put_screener.py` → `render_put_results_table(recommendations, buying_power, console?)` rendering Rich table
- `tests/test_put_screener.py` → 40+ tests covering math, filtering, pagination, one-per-underlying, edge cases

Consumes:
- nothing (first slice — uses existing `ScreenerConfig`, `DELTA_MIN`/`DELTA_MAX` from `config/params.py`, Alpaca SDK types)

### S01 → S03

Produces:
- `screen_puts()` as complete replacement for `sell_puts()` + `core/strategy.py` functions

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `scripts/run_put_screener.py` → Typer CLI entry point registered as `run-put-screener` in `pyproject.toml`
- `scripts/run_strategy.py` → `sell_puts()` call replaced with `screen_puts()` + `client.market_sell()` loop
- All remaining imports from `core/execution.sell_puts` removed from `scripts/run_strategy.py`

Consumes from S01:
- `screen_puts()` function signature and return type
- `PutRecommendation` dataclass
- `render_put_results_table()` for CLI display

### S02 → S04

Produces:
- Working `run-strategy` using `screen_puts()` for the put leg
- Working `run-put-screener` CLI

Consumes from S01:
- `screen_puts()` and `PutRecommendation`

### S03 → S04

Produces:
- Clean codebase with no imports from `core/strategy`, `core/execution.sell_puts`, `core/execution.sell_calls`, or `models/contract`
- Updated `CLAUDE.md` and `README.md`
- Removed obsolete constants from `config/params.py`

Consumes from S02:
- `scripts/run_strategy.py` no longer importing `sell_puts` or `sell_calls`

### S04 (terminal slice)

Produces:
- Verified clean `run-strategy` exercising complete wheel cycle through modern screener modules
- Final test suite confirmation: all tests pass, zero references to deleted modules

Consumes from S03:
- Clean codebase with legacy code removed
