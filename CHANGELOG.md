# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1] - 2026-03-20

### Fixed

- **Put screener selling ITM options** — the put screener had no explicit OTM check and relied solely on delta filtering. Contracts with missing greeks data bypassed the delta filter entirely (D039 rule), allowing deep ITM puts to be selected. Added a hard `strike < stock_price` gate that rejects any ITM or ATM put.
- **Ranking inflated by intrinsic value** — annualized return was computed on total premium (`bid`), which includes intrinsic value for ITM puts. ITM contracts with high intrinsic value ranked above genuinely profitable OTM contracts. Now uses extrinsic (time value) premium only: `extrinsic = bid - max(strike - stock_price, 0)`.

### Added

- **`extrinsic` field on `PutRecommendation`** — shows how much of the premium is time value vs intrinsic. Visible in the CLI table ("Extrinsic" column) and API response.

## [0.3.0] - 2026-03-19

### Added

- **Configurable DTE filtering** — `dte_min` and `dte_max` are now configurable via `config/screener.yaml` and preset profiles. Previously hardcoded to 14–60 days across all screeners.
- **Weekly options support** — set `dte_min: 7` to target weekly expirations. The aggressive preset defaults to `dte_min: 7`.
- **DTE in presets** — conservative (21–45), moderate (14–60), aggressive (7–60). Override in `config/screener.yaml` under `options:`.
- **Validation** — `dte_min >= 0`, `dte_max <= 365`, `dte_max > dte_min` enforced by Pydantic.

## [0.2.1] - 2026-03-18

### Added

- **`--max-risk` flag on `run-strategy`** — sets the maximum dollar risk (total capital budget) for the strategy. Overrides the config value. Usage: `run-strategy --max-risk 100000`.
- **`max_risk` in screener config** — configurable via `config/screener.yaml` or preset profiles. Presets: conservative ($50k), moderate ($80k), aggressive ($120k). Precedence: CLI flag > screener.yaml > preset default.

## [0.2.0] - 2026-03-17

### Fixed

- **`run-strategy --screen` skipping options chain validation** — `option_client` was not passed to `run_pipeline()`, causing Stage 3 (OI, spread, premium yield checks) to be skipped entirely. This resulted in 864+ stocks passing the screener without any options liquidity validation, making the subsequent put screener return empty results. Now all 3 stages run correctly.

### Added

- **`--top-n` flag on `run-strategy`** — caps the number of stocks processed after Stage 1 when using `--screen`. Usage: `run-strategy --screen --top-n 20`. Warns if used without `--screen`.
- **`run-put-screener` reads from `symbol_list.txt`** — symbols argument is now optional. When omitted, loads tickers from `config/symbol_list.txt`. Usage: `run-put-screener --buying-power 50000`.

## [0.1.3] - 2026-03-17

### Added

- Web dashboard (Next.js) with portfolio overview, positions, and trade history pages.
- Settings page with BYOK (Bring Your Own Key) configuration.

## [0.1.2] - 2026-03-16

### Added

- `--top-n` usage docs and recommended commands for free API tiers.

## [0.1.1] - 2026-03-16

### Fixed

- Clone URL after repo rename from wheeely to wheel-it.
- README rewritten for end users with pip install and attribution.

## [1.0] - 2026-03-15

### Added

- Automated stock screening module for wheel strategy suitability.
- 10 screening filters (fundamentals + technicals) with cheap-first pipeline.
- Wheel suitability scoring (capital efficiency, volatility, fundamentals).
- Rich table output with color-coded scores and progress indicators.
- Standalone `run-screener` CLI and `run-strategy --screen` integration.
- Position-safe symbol list export.
- Covered call screening and strategy integration.
- Put screener module with CLI.
- HV rank and earnings calendar integration.
- Options chain validation (Stage 3).
- Monthly performance and pipeline cap (`--top-n` on `run-screener`).
