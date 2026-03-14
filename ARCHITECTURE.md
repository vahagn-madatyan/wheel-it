# Current Architecture

This project is a Python CLI application with three entrypoints built around two related workflows:

- Wheel strategy execution and order placement
- Stock and covered-call screening

The diagram below reflects the current code in `scripts/`, `core/`, `screener/`, `models/`, `config/`, and `logging/`.

```mermaid
flowchart LR
    user([Operator])

    subgraph cli["CLI Entrypoints (scripts/)"]
        runStrategy["run-strategy<br/>wheel orchestration"]
        runScreener["run-screener<br/>stock screener"]
        runCall["run-call-screener<br/>covered-call screener"]
    end

    subgraph cfgState["Configuration & Local State"]
        env[".env<br/>API credentials"]
        params["config.params<br/>strategy thresholds"]
        screenerCfg["config/screener.yaml<br/>+ config/presets/*.yaml"]
        symbolList["config/symbol_list.txt<br/>tradable watchlist"]
        localLogs["logs directory<br/>run.log + strategy_log.json"]
    end

    subgraph core["Core Trading Layer (core/)"]
        broker["broker_client.py<br/>Alpaca client wrapper"]
        cliCommon["cli_common.py<br/>shared CLI bootstrap"]
        state["state_manager.py<br/>wheel state + risk"]
        execution["execution.py<br/>sell puts"]
        strategy["strategy.py<br/>filter / score / select options"]
        utils["utils.py<br/>symbol + time helpers"]
    end

    subgraph screening["Screening Layer (screener/)"]
        configLoader["config_loader.py<br/>preset merge + validation"]
        pipeline["pipeline.py<br/>universe -> Stage 1 -> 1b -> 2 -> 3 -> score"]
        marketData["market_data.py<br/>bars + indicators"]
        finnhubClient["finnhub_client.py<br/>fundamentals + earnings"]
        callScreener["call_screener.py<br/>covered-call ranking"]
        display["display.py<br/>Rich tables + progress"]
        export["export.py<br/>protected symbol updates"]
    end

    subgraph modelsLogs["Models & Logging"]
        contract["models/contract.py<br/>option contract model"]
        screened["models/screened_stock.py<br/>screening result model"]
        runtimeLogger["logging/logger_setup.py<br/>console/file logger"]
        strategyLogger["logging/strategy_logger.py<br/>JSON strategy log"]
    end

    subgraph external["External Services"]
        alpaca["Alpaca Trading + Market Data APIs"]
        finnhub["Finnhub API"]
    end

    user --> runStrategy
    user --> runScreener
    user --> runCall

    env --> runStrategy
    env --> runScreener
    env --> runCall
    params --> runStrategy
    screenerCfg --> configLoader
    symbolList --> runStrategy
    symbolList --> pipeline

    runStrategy --> broker
    runStrategy --> state
    runStrategy --> execution
    runStrategy --> configLoader
    runStrategy --> pipeline
    runStrategy --> callScreener
    runStrategy --> display
    runStrategy --> export
    runStrategy --> runtimeLogger
    runStrategy --> strategyLogger

    runScreener --> cliCommon
    cliCommon --> broker
    runScreener --> configLoader
    runScreener --> pipeline
    runScreener --> display
    runScreener --> export
    runScreener --> state

    runCall --> cliCommon
    runCall --> configLoader
    runCall --> callScreener
    runCall --> display

    execution --> strategy
    execution --> contract
    state --> utils
    strategyLogger --> utils

    pipeline --> marketData
    pipeline --> finnhubClient
    pipeline --> screened
    callScreener --> configLoader

    broker --> alpaca
    marketData --> alpaca
    pipeline --> alpaca
    callScreener --> alpaca
    finnhubClient --> finnhub

    export --> symbolList
    runtimeLogger --> localLogs
    strategyLogger --> localLogs
```

## Runtime Flows

1. `run-strategy` loads credentials and thresholds, optionally runs the screener pipeline, reconciles current portfolio state, sells covered calls for assigned shares, then scans and sells puts through the execution layer.
2. `run-screener` builds a broker client, loads screener config, runs the multi-stage screening pipeline, renders Rich output, and optionally writes a position-safe `config/symbol_list.txt`.
3. `run-call-screener` reuses the screener config and Alpaca clients to rank covered calls for a single underlying and cost basis.

## Key Design Points

- Alpaca is the primary execution and market-data dependency.
- Finnhub is isolated behind `screener/finnhub_client.py` for fundamentals and earnings lookups.
- The screening pipeline is intentionally staged so cheap Alpaca-based filters run before slower Finnhub and options-chain checks.
- `run-strategy` is the integration point where screening, portfolio-state management, execution, and logging meet.
