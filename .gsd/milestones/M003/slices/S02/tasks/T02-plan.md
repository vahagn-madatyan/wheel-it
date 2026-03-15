---
estimated_steps: 7
estimated_files: 3
---

# T02: Wire screen_puts() into run-strategy and remove sell_puts/sell_calls imports

**Slice:** S02 — Put Screener CLI + Strategy Integration
**Milestone:** M003

## Description

Replace the `sell_puts()` call in `run-strategy` with `screen_puts()` + order execution loop. Remove dead imports of `sell_puts` and `sell_calls` from `core.execution`.

## Steps

1. Read `scripts/run_strategy.py` lines 200–220 to understand the current `sell_puts()` call site.
2. Remove `from core.execution import sell_puts, sell_calls` from `scripts/run_strategy.py`.
3. Add `from screener.put_screener import screen_puts` to `scripts/run_strategy.py`.
4. Replace the `sell_puts(client, allowed_symbols, buying_power, strat_logger)` call with: load screener config (reuse `call_config` or load fresh), call `screen_puts(client.trade_client, client.option_client, allowed_symbols, buying_power, config=cfg)`, iterate recommendations calling `client.market_sell(rec.symbol)` for each, deduct `100 * rec.strike` from buying_power, stop when buying_power < 0 or recommendations exhausted.
5. Log each put sold with details (symbol, strike, DTE, premium, annualized return).
6. Update `strat_logger.log_sold_puts()` to receive the new recommendation format.
7. Update/write tests in `tests/test_cli_strategy.py`: verify `screen_puts` is called instead of `sell_puts`, verify no `core.execution` imports remain, verify buying power deduction, verify empty recommendations handled gracefully.

## Must-Haves

- [ ] `scripts/run_strategy.py` no longer imports from `core.execution`
- [ ] `scripts/run_strategy.py` imports and calls `screen_puts()` for the put-selling leg
- [ ] Each recommendation triggers `client.market_sell(rec.symbol)` with buying power tracking
- [ ] Empty recommendations list → no orders placed, no crash
- [ ] Strategy integration tests pass

## Verification

- `python -m pytest tests/test_cli_strategy.py -v` — all pass
- `python -m pytest tests/ -q` — all pass
- `rg "from core.execution" scripts/` — zero matches

## Observability Impact

- Signals added: logs each put sold with contract details and remaining buying power
- Failure state exposed: logs "No put recommendations found" when `screen_puts()` returns empty

## Inputs

- `screener/put_screener.py` — `screen_puts()` from S01
- `scripts/run_strategy.py` — current strategy code using `sell_puts()`

## Expected Output

- `scripts/run_strategy.py` — modernized to use `screen_puts()` exclusively
- `tests/test_cli_strategy.py` — updated strategy integration tests
