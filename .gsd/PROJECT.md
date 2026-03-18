# Wheeely

## What This Is

An options wheel strategy platform. Started as a CLI bot that screens stocks and sells cash-secured puts / covered calls via the Alpaca Trading API. Now expanding into a multi-tenant SaaS where traders sign up, connect their own API keys (BYOK), and run screeners from a browser — free tier matches CLI capabilities, premium tier adds additional data providers (FMP, ORATS), cloud auto-trading, and LLM analysis.

The CLI remains standalone and untouched. Premium features live in a separate `/premium` directory following the GitLab open-core model (free + paid tiers, same codebase).

## Core Value

Data-driven options wheel stock screening — replacing manual symbol selection with automated fundamental + technical + options chain filtering, configurable via presets, accessible via CLI or web.

## Current State

**CLI (complete):** Fully functional 4-stage screening pipeline (technicals → earnings → fundamentals → options chain) with 3 presets, HV percentile, earnings proximity exclusion, put + call screeners, strategy bot integration, and top-N performance cap. 425 tests passing, zero failures.

**Web (M004 — in progress):** Building the free-tier online experience. S01 complete — FastAPI wraps the existing screening engine with 5 endpoints, per-request Alpaca client construction, and async background task execution (31 API tests). S02 complete — Supabase auth (JWT middleware), 4-table database schema with RLS, envelope encryption for API keys, and key management CRUD endpoints (31 S02 tests, 62 total API tests). S03 complete — Next.js 16 app shell with Supabase auth (login/signup), middleware route protection, sidebar navigation (Dashboard, Put Screener, Call Screener, Settings), and apiFetch() API client with Bearer token injection. S04 complete — Settings page with Alpaca (api_key + secret_key + paper/live toggle) and Finnhub (api_key) provider cards, store/auto-verify/delete flows wired to S02 backend via apiFetch(), extracted ProviderCard component with FormField pattern. Next: screener UI (S05), positions + rate limiting (S06), and deployment (S07).

Tech stack:
- CLI: Python 3.13, alpaca-py, finnhub-python, ta, pydantic, rich, typer, pyyaml
- Web: FastAPI, Next.js 16, Supabase, Redis, Render

## Architecture / Key Patterns

- **CLI entry points:** `run-strategy`, `run-screener`, `run-call-screener`, `run-put-screener` — registered in `pyproject.toml`
- **Pipeline:** `screener/pipeline.py:run_pipeline()` — 4-stage orchestrator with pure filter functions
- **Screeners:** Symmetric `screen_puts()` / `screen_calls()` with preset-configurable thresholds
- **Config:** YAML presets + Pydantic validation via `screener/config_loader.py`
- **Display:** Rich tables with Console injection for testability
- **Data:** `screener/finnhub_client.py` (rate-limited) + `screener/market_data.py` (Alpaca bars)
- **Logging shadow:** Project's `logging/` package shadows stdlib; all modules use `import logging as stdlib_logging`
- **BYOK model:** All API keys are user-owned. Platform never absorbs data provider costs.
- **Open-core licensing:** Free tier = Finnhub + Alpaca (CLI-equivalent online). Premium adds FMP, ORATS, auto-trading, LLM — additive, never replaces free-tier providers.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Screener Fix + Covered Calls — Fixed broken pipeline, added HV percentile, earnings filter, options chain validation, covered call screening
- [x] M002: Top-N Performance Cap — `--top-n` CLI flag limits expensive stage processing by selecting worst monthly performers
- [x] M003: Modern Put Screener + Legacy Cleanup — Symmetric `screen_puts()`, `run-put-screener` CLI, removed legacy code, 425 tests
- [ ] M004: Free Tier Online — Multi-tenant SaaS: FastAPI + Supabase + Next.js, BYOK key storage, screener UI, positions dashboard, deployed on Render
