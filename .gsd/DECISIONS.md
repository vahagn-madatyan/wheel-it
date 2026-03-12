# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001/S01 | convention | logging module shadow | `import logging as stdlib_logging` pattern + `importlib.util.spec_from_file_location` in `__init__.py` | Project's `logging/` package shadows stdlib; this re-exports cleanly | No |
| D002 | M001/S01 | convention | YAML integer format | Plain integers only, no underscores | PyYAML parsing issues with underscore separators | No |
| D003 | M001/S01 | pattern | Config validation | Early preset name validation in `load_config()` → `ValidationError` not `FileNotFoundError` | User gets actionable error message | No |
| D004 | M001/S02 | pattern | Rate limit retry | Lambda wrappers in `company_profile`/`company_metrics` to separate SDK kwargs from logging kwargs in `_call_with_retry` | Clean separation of concerns | No |
| D005 | M001/S02 | pattern | Finnhub mock pattern | Preserve real `FinnhubAPIException` class when patching the finnhub module | Prevents `TypeError` on `except` clauses | No |
| D006 | M001/S02 | convention | Test date handling | `pd.bdate_range` with fixed end date instead of `datetime.now()` | Avoids non-deterministic business-day alignment | No |
| D007 | M001/S02 | convention | Indicator minimums | 30 bars for RSI(14), 200 bars for SMA(200) — below threshold returns None | Prevents garbage computations | No |
| D008 | M001/S03 | arch | Filter function purity | Take `ScreenedStock` + config → return `FilterResult`, never raise | Composable, testable pipeline stages | No |
| D009 | M001/S03 | data | market_cap storage | Raw dollars on `ScreenedStock`; Finnhub millions conversion in `run_stage_2_filters` | Single unit system, conversion at boundary | No |
| D010 | M001/S03 | arch | Stage 2 responsibility | Stage 2 runner handles Finnhub data fetch + field population, keeping filter functions data-agnostic | Filters don't know about API calls | No |
| D011 | M001/S03 | convention | HV computation | Log returns with ddof=1 std dev, annualized by sqrt(252) | Standard financial convention | No |
| D012 | M001/S03 | arch | Scoring weights | Capital efficiency 0.45, volatility 0.35, fundamentals 0.20 | Capital efficiency dominant for wheel strategy | Yes — if strategy changes |
| D013 | M001/S03 | pattern | None handling in scoring | None HV and None fundamentals get neutral 0.5 score | Avoids penalizing stocks with partial data | No |
| D014 | M001/S03 | pattern | Min-max normalization | 0.5 fallback when all values identical (single stock or equal metrics) | Prevents division by zero | No |
| D015 | M001/S04 | pattern | Console injection | Console parameter injection for testability (default `_default_console`) | Testable without side effects | No |
| D016 | M001/S04 | convention | Score coloring | Sorted thirds: top green, middle yellow, bottom red | Relative ranking, not absolute thresholds | No |
| D017 | M001/S04 | convention | Filter breakdown display | Only shows filters that actually removed stocks | Reduces noise | No |
| D018 | M001/S05 | pattern | Protected symbols | `get_protected_symbols` accepts `update_state_fn` as parameter (not import) | Testable, decoupled | No |
| D019 | M001/S05 | pattern | CLI imports | Module-level imports in CLI entry points for patchability with `unittest.mock.patch` | Deferred imports prevent `@patch` from finding targets | No |
| D020 | M001/S05 | convention | Default screener mode | Output-only by default (no `--output-only` flag needed) | Satisfies CLI-04, least surprise | No |
| D021 | M001/S06 | pattern | dotenv test isolation | Patch `dotenv.load_dotenv` at source module, not at `config.credentials.load_dotenv` | `importlib.reload()` creates fresh binding | No |
| D022 | M001/S06 | convention | CLI error output | `Console(stderr=True)` for error output, `typer.Exit(code=1)` for clean exit on validation failure | Error semantics, consistent with Typer framework | No |
| D023 | M001 | arch | Slice ordering for v1.1 | Fix pipeline first (S07), then cheap pre-filters (S08), then expensive post-filters (S09), then new capability (S10) | Risk-first: broken pipeline is highest risk; cheap-first ordering matches existing pipeline architecture | No |
| D024 | M001 | scope | Free APIs only | Approximate IV Rank from HV percentile, use Finnhub earnings calendar — no paid data sources (ORATS, Barchart) | User decided free APIs only; HV percentile is adequate proxy | No |
| D025 | M001 | scope | Call screener dual mode | Standalone `run-call-screener` CLI + integrated into `run-strategy` flow for assigned positions | Serves both exploration and automation use cases | No |
| D026 | M001 | scope | Debug first, features second | Fix zero-results pipeline bug before adding any new screening features | Must validate existing infrastructure works before extending it | No |
| D027 | M001/S07 | data | D/E normalization heuristic | If Finnhub `debt_equity > 10`, divide by 100 to convert percentage to ratio; values ≤ 10 assumed already ratio | Handles both Finnhub percentage and ratio formats; threshold > 10 safe because Pydantic validator caps `debt_equity_max` at 10 | Yes — if Finnhub format changes |
| D028 | M001/S07 | pattern | None-handling split by stage | Stage 1 (Alpaca) filters: `None` → `passed=False` (no bar data = unscreenable); Stage 2 (Finnhub) filters: `None` → `passed=True` with neutral reason (patchy coverage, not stock fault) | Prevents Finnhub data gaps from silently eliminating tradeable stocks; Stage 1 None means genuinely no data | No |
| D029 | M001/S08 | arch | HV percentile in Stage 1, earnings in Stage 1b | HV percentile uses existing Alpaca bar data (zero extra API calls) → Stage 1. Earnings proximity needs one Finnhub call per symbol → Stage 1b (after Stage 1, before Stage 2) | Cheap-first ordering: avoid expensive Finnhub fundamental calls for stocks that fail cheap filters | No |
| D030 | M001/S08 | convention | Earnings boundary inclusive | `days_to_earnings <= exclusion_days` → fail (inclusive boundary) | Day-of-earnings and day-before-earnings are both risky for options selling | No |
| D031 | M001/S08 | pattern | None earnings/HV → neutral pass | Both `filter_hv_percentile` and `filter_earnings_proximity` pass with neutral score when data is None | Consistent with D028 pattern; absence of data should not eliminate a tradeable stock | No |
| D032 | M001/S09 | convention | Options DTE lookup range | 14–60 day DTE range hardcoded as `_OPTIONS_DTE_MIN` / `_OPTIONS_DTE_MAX` module constants | Requirements specify OI/spread configurability only; DTE range is a screening concern, not a trading parameter | Yes — if users need different windows |
| D033 | M001/S09 | pattern | Nearest ATM put selection | `min(contracts, key=abs(strike - price))` — closest strike to current stock price | Simple, deterministic; single ATM put sufficient to validate liquidity of underlying's options chain | No |
| D034 | M001/S09 | convention | Spread computation | `(ask - bid) / midpoint` where `midpoint = (bid + ask) / 2` | Standard financial percentage spread; avoids divide-by-zero when midpoint > 0 check applied | No |
| D035 | M001/S09 | arch | option_client optional | `run_pipeline(option_client=None)` — Stage 3 skipped when absent | Backward compatible: 244 existing tests pass unchanged; callers opt in to options chain validation | No |
| D036 | M001/S09 | pattern | OI from contract, bid/ask from snapshot | OI read from `trade_client.get_option_contracts()` response; bid/ask from `option_client.get_option_snapshot()` | Avoids extra API call when OI already fails the filter; snapshot only fetched for OI-passing contracts | No |
| D037 | M001/S10 | arch | Call screener reuses put screener thresholds | DTE range (14-60 days), OI/spread from ScreenerConfig presets, delta from config/params.py | CALL-04 requires same filters; avoids config proliferation; single source of truth for options liquidity thresholds | Yes — if calls need separate thresholds |
| D038 | M001/S10 | arch | Strategy integration replaces sell_calls | `screen_calls()` replaces `core/execution.py:sell_calls()` for long_shares state in run_strategy.py | New path is strictly better: preset-configurable thresholds + annualized return ranking vs fixed params | No |
| D039 | M001/S10 | pattern | No-greeks contracts pass delta filter | When snapshot.greeks is None, contract passes delta filter (included in results) | Consistent with D028/D031 None-tolerance pattern; absence of greeks data shouldn't eliminate tradeable contracts | No |
| D040 | M001/S10 | pattern | Insufficient shares logged, not raised | `run_strategy.py` logs error for <100 shares instead of raising ValueError | Strategy should continue processing other symbols; old sell_calls crash halted entire run | No |
| D041 | M002 | convention | Monthly perf lookback | Fixed 22 trading days (~1 calendar month) | Simple, consistent; no need for configurable window for this use case | Yes — if users want different periods |
| D042 | M002 | arch | top_n is CLI-only | `--top-n` flag on run-screener, not configurable per preset in YAML | Keeps presets focused on filter thresholds; top_n is an operational concern | Yes — if presets should control it |
| D043 | M002 | arch | Cap placement | Sort/cap after Stage 1 (all Alpaca-based filters) but before Stage 1b (Finnhub earnings) | Maximizes savings — all expensive per-symbol API calls are after the cap | No |
| D044 | M002 | pattern | None perf_1m sorts last | Stocks with insufficient bar data for perf computation get perf_1m=None and sort to end of list | Don't drop them; just deprioritize when cap is active | No |
