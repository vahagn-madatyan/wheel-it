# Automated Wheel Strategy

Welcome to the Wheel Strategy automation project!
This script is designed to help you trade the classic ["wheel" options strategy](https://alpaca.markets/learn/options-wheel-strategy) with as little manual work as possible using the [Alpaca Trading API](https://docs.alpaca.markets/).

---

## Strategy Logic

Here's the basic idea:

1. **Sell cash-secured puts** on stocks you wouldn't mind owning.
2. If you **get assigned**, buy the stock.
3. Then **sell covered calls** on the stock you own.
4. Keep collecting premiums until the stock gets called away.
5. Repeat the cycle!

This code helps pick the right puts and calls to sell, tracks your positions, and automatically turns the wheel to the next step.

---

## How to Run the Code

1. **Clone the repository:**

   ```bash
   git clone https://github.com/alpacahq/options-wheel.git
   cd options-wheel
   ```

2. **Create a virtual environment using [`uv`](https://github.com/astral-sh/uv):**

   ```bash
   uv venv
   source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
   ```

3. **Install the required packages:**

   ```bash
   uv pip install -e .
   ```

4. **Set up your API credentials:**

   Create a `.env` file in the project root with the following content:

   ```env
   ALPACA_API_KEY=your_public_key
   ALPACA_SECRET_KEY=your_private_key
   IS_PAPER=true  # Set to false if using a live account
   FINNHUB_API_KEY=your_finnhub_key  # Required for stock screener
   ```

   Your credentials will be loaded from `.env` automatically. Get a free Finnhub API key at [finnhub.io/register](https://finnhub.io/register).

5. **Choose your symbols:**

   The strategy trades only the symbols listed in `config/symbol_list.txt`. Edit this file to include the tickers you want to run the Wheel strategy on - one symbol per line. Choose stocks you'd be comfortable holding long-term.

   > **Tip:** Use `run-screener --update-symbols` to automatically populate this file with screener results (see [Stock Screener](#stock-screener) below).

6. **Configure trading parameters:**

   Adjust values in `config/params.py` to customize things like buying power limits, options characteristics (e.g., greeks / expiry), and scoring thresholds. Each parameter is documented in the file.

7. **Run the strategy**

   Run the strategy (which assumes an empty or fully managed portfolio):

   ```bash
   run-strategy
   ```

   > **Tip:** On your first run, use `--fresh-start` to liquidate all existing positions and start clean.

   There are two types of logging:

   * **Strategy JSON logging** (`--strat-log`):
     Always saves detailed JSON files to disk for analyzing strategy performance.

   * **Runtime logging** (`--log-level` and `--log-to-file`):
     Controls console/file logs for monitoring the current run. Optional and configurable.

   **Flags:**

   * `--fresh-start` - Liquidate all positions before running (recommended first run).
   * `--screen` - Run the stock screener before strategy execution. Updates your symbol list with position-safe symbol export.
   * `--strat-log` - Enable strategy JSON logging (always saved to disk).
   * `--log-level LEVEL` - Set runtime logging verbosity (default: INFO).
   * `--log-to-file` - Save runtime logs to file instead of console.

   Example:

   ```bash
   run-strategy --fresh-start --strat-log --log-level DEBUG --log-to-file
   ```

   For more info:

   ```bash
   run-strategy --help
   ```

---

## Stock Screener

The project includes a built-in stock screener that finds wheel-strategy-suitable stocks using fundamental data from Finnhub and technical data from Alpaca.

### Running the Screener

```bash
run-screener                          # Run with default preset (moderate)
run-screener --preset conservative    # Tighter filters (large-cap, low debt)
run-screener --preset aggressive      # Looser filters (small-cap OK)
run-screener --verbose                # Show per-filter elimination breakdown
run-screener --update-symbols         # Export results to config/symbol_list.txt
```

### Presets

Three preset profiles control all screening thresholds:

| Category | Conservative | Moderate | Aggressive |
|----------|-------------|----------|------------|
| Market Cap Min | $10B | $2B | $500M |
| Debt/Equity Max | 0.5 | 1.5 | 3.0 |
| Avg Volume Min | 1M | 500K | 200K |
| HV Percentile Min | 50 | 30 | 20 |
| Earnings Exclusion | 21 days | 14 days | 7 days |
| Options OI Min | 500 | 100 | 50 |
| Options Spread Max | 5% | 10% | 20% |
| Sector Exclusions | Biotech, Cannabis, O&G | Cannabis | None |

Preset files are in `config/presets/`. You can also create a custom `config/screener.yaml` to override individual values.

### Screening Pipeline

The screener runs a 4-stage filtering pipeline in cheap-first order:

1. **Stage 1 - Technicals** (Alpaca data): Price range, volume, RSI, SMA(200), HV percentile
2. **Stage 1b - Earnings** (Finnhub): Excludes stocks with earnings within the configured window
3. **Stage 2 - Fundamentals** (Finnhub): Market cap, debt/equity, net margin, sales growth, sector
4. **Stage 3 - Options Chain** (Alpaca): Open interest, bid/ask spread on nearest ATM put

Survivors are scored by wheel suitability (capital efficiency 45%, volatility 35%, fundamentals 20%) and displayed as a Rich table with HV percentile and annualized put premium yield columns.

### Symbol Export

`--update-symbols` safely merges screener results into `config/symbol_list.txt`, preserving any symbols with active positions. A colored diff shows what was added/removed.

---

## Covered Call Screener

When the wheel assigns you stock, use the call screener to find the best covered calls to sell:

```bash
run-call-screener AAPL --cost-basis 175.00                    # Screen calls for AAPL
run-call-screener AAPL --cost-basis 175.00 --preset conservative  # Use stricter filters
```

The call screener:
- Fetches OTM call contracts within a 14-60 DTE range
- Filters by **strike ≥ cost basis** (never sell below your entry price)
- Applies OI, bid/ask spread, and delta filters from your preset
- Ranks survivors by **annualized return** (descending)
- Displays a Rich table with strike, DTE, premium, delta, and annualized return

### Automatic Call Screening in Strategy

When `run-strategy` detects assigned stock positions (`long_shares` state), it automatically uses the call screener to select and sell the best covered call - no manual intervention needed.

---

### What the Script Does

* Checks your current positions to identify any assignments and sells covered calls on those.
* Filters your chosen stocks based on buying power (you must be able to afford 100 shares per put).
* Scores put options using `core.strategy.score_options()`, which ranks by annualized return discounted by the probability of assignment.
* Places trades for the top-ranked options.

---

### Notes

* **Account state matters**: This strategy assumes full control of the account - all positions are expected to be managed by this script. For best results, start with a clean account (e.g. by using the `--fresh-start` flag).
* **One contract per symbol**: To simplify risk management, this implementation trades only one contract at a time per symbol. You can modify this logic in `core/strategy.py` to suit more advanced use cases.
* The **user agent** for API calls defaults to `OPTIONS-WHEEL` to help Alpaca track usage of runnable algos and improve user experience.  You can opt out by adjusting the `USER_AGENT` variable in `core/user_agent_mixin.py` - though we kindly hope you'll keep it enabled to support ongoing improvements.
* **Want to customize the strategy?** The `core/strategy.py` module is a great place to start exploring and modifying the logic.

---

## Automating the Wheel

Running the script once will only turn the wheel a single time. To keep it running as a long-term income strategy, you'll want to automate it to run several times per day. This can be done with a cron job on Mac or Linux.

### Setting Up a Cron Job (Mac / Linux)

1. **Find the full path to the `run-strategy` command** by running:

   ```bash
   which run-strategy
   ```

   This will output something like:

   ```bash
   /Users/yourname/.local/share/virtualenvs/options-wheel-abc123/bin/run-strategy
   ```

2. **Open your crontab** for editing:

   ```bash
   crontab -e
   ```

3. **Add the following lines to run the strategy at 10:00 AM, 1:00 PM, and 3:30 PM on weekdays:**

   ```cron
   0 10 * * 1-5 /full/path/to/run-strategy >> /path/to/logs/run_strategy_10am.log 2>&1
   0 13 * * 1-5 /full/path/to/run-strategy >> /path/to/logs/run_strategy_1pm.log 2>&1
   30 15 * * 1-5 /full/path/to/run-strategy >> /path/to/logs/run_strategy_330pm.log 2>&1
   ```

   Replace `/full/path/to/run-strategy` with the output from the `which run-strategy` command above. Also replace `/path/to/logs/` with the directory where you'd like to store log files (create it if needed).

---

## Test Results

To validate the code mechanics, the strategy was tested in an Alpaca paper account over the course of two weeks (May 14 - May 28, 2025). A full report and explanation of each decision point can be found in [`reports/options-wheel-strategy-test.pdf`](./reports/options-wheel-strategy-test.pdf). A high-level summary of the trading results is given below.

### Premiums Collected

| Underlying | Expiry     | Strike | Type | Date Sold  | Premium Collected |
| ---------- | ---------- | ------ | ---- | ---------- | ----------------- |
| PLTR       | 2025-05-23 | 124    | P    | 2025-05-14 | \$261.00          |
| NVDA       | 2025-05-30 | 127    | P    | 2025-05-14 | \$332.00          |
| MP         | 2025-05-23 | 20     | P    | 2025-05-14 | \$28.00           |
| AAL        | 2025-05-30 | 11     | P    | 2025-05-14 | \$20.00           |
| INTC       | 2025-05-30 | 20.50  | P    | 2025-05-14 | \$33.00           |
| CAT        | 2025-05-16 | 345    | P    | 2025-05-14 | \$140.00          |
| AAPL       | 2025-05-23 | 200    | P    | 2025-05-19 | \$110.00          |
| DLR        | 2025-05-30 | 165    | P    | 2025-05-20 | \$67.00           |
| AAPL       | 2025-05-30 | 202.50 | C    | 2025-05-27 | \$110.00          |
| MP         | 2025-05-30 | 20.50  | C    | 2025-05-27 | \$12.00           |
| PLTR       | 2025-05-30 | 132    | C    | 2025-05-27 | \$127.00          |

**Total Premiums Collected:** **\$1,240.00**

---

### Total PnL (Change in Account Liquidating Value)

| Metric                   | Value           |
| ------------------------ | --------------- |
| Starting Balance         | \$100,000.00    |
| Ending Balance           | \$100,951.89    |
| Net PnL                  | **+\$951.89** |

---

### Disclaimer

These results are based on historical, simulated trading in a paper account over a limited timeframe and **do not represent actual live trading performance**. They are provided solely to demonstrate the mechanics of the strategy and its ability to automate the Wheel process in a controlled environment. **Past performance is not indicative of future results.** Trading in live markets involves risk, and there is no guarantee that future performance will match these simulated results.

---

## Core Strategy Logic

The core logic is defined in `core/strategy.py`.

* **Stock Filtering:**
  The strategy filters underlying stocks based on available buying power. It fetches the latest trade prices for each candidate symbol and retains only those where the cost to buy 100 shares (`price × 100`) is within your buying power limit. This keeps trades within capital constraints and can be extended to include custom filters like volatility or technical indicators.

* **Option Filtering:**
  Put options are filtered by absolute delta, which must lie between `DELTA_MIN` and `DELTA_MAX`, by open interest (`OPEN_INTEREST_MIN`) to ensure liquidity, and by yield (between `YIELD_MIN` and `YIELD_MAX`). For short calls, the strategy applies a minimum strike price filter (`min_strike`) to ensure the strike is above the underlying purchase price. This helps avoid immediate assignment and locks in profit if the call is assigned.

* **Option Scoring:**
  Options are scored to estimate their attractiveness based on annualized return, adjusted for assignment risk. The score formula is:

   `score = (1 - |Δ|) × (250 / (DTE + 5)) × (bid price / strike price)`

  Where:

  * $\Delta$ = option delta (a rough proxy for the probability of assignment)
  * DTE = days to expiration
  * The factor 250 approximates the number of trading days in a year
  * Adding 5 days to DTE smooths the score for near-term options

* **Option Selection:**
  From all scored options, the strategy picks the highest-scoring contract per underlying symbol to promote diversification. It filters out options scoring below `SCORE_MIN` and returns either the top N options or all qualifying options.

---

## Ideas for Customization

### Stock Picking

* The built-in screener already uses RSI, SMA(200), HV percentile, and fundamental filters. Customize thresholds in `config/presets/` or add new filters in `screener/pipeline.py`.
* Add additional technical indicators or custom scoring factors to `screener/pipeline.py:compute_wheel_score()`.

### Scoring Function for Puts / Calls

* Modify the scoring formula to weight factors differently or separately for puts vs calls. For example, emphasize calls with strikes just below resistance levels or puts on stocks with strong support.
* Consider adding factors like implied volatility or premium decay to better capture option pricing nuances.
* The screener scoring weights (capital efficiency 45%, volatility 35%, fundamentals 20%) can be adjusted in `screener/pipeline.py`.

### Managing a Larger Portfolio

* Allocate larger trade sizes to higher-scoring options for more efficient capital use.
* Allow multiple wheels per stock to increase position flexibility.
* Set exposure limits per underlying or sector to manage risk.

### Stop Loss When Puts Get Assigned

* Implement logic to cut losses if a stock price falls sharply after assignment, protecting capital from downside.

### Rolling Short Puts as Expiration Nears

* Instead of letting puts expire or get assigned, roll them forward to the next expiration or down to lower strikes to capture additional premium and manage risk.
* (For more, see [this Learn article](https://alpaca.markets/learn/options-wheel-strategy).)

---

## Final Notes

This is a great starting point for automating your trading, but always double-check your live trades - no system is completely hands-off.

Happy wheeling! 🚀

---
<div style="font-size: 0.8em;">
Disclosures

Options trading is not suitable for all investors due to its inherent high risk, which can potentially result in significant losses. Please read [Characteristics and Risks of Standardized Options](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document) before investing in options

The Paper Trading API is offered by AlpacaDB, Inc. and does not require real money or permit a user to transact in real securities in the market. Providing use of the Paper Trading API is not an offer or solicitation to buy or sell securities, securities derivative or futures products of any kind, or any type of trading or investment advice, recommendation or strategy, given or in any manner endorsed by AlpacaDB, Inc. or any AlpacaDB, Inc. affiliate and the information made available through the Paper Trading API is not an offer or solicitation of any kind in any jurisdiction where AlpacaDB, Inc. or any AlpacaDB, Inc. affiliate (collectively, "Alpaca") is not authorized to do business.

All investments involve risk, and the past performance of a security, or financial product does not guarantee future results or returns. There is no guarantee that any investment strategy will achieve its objectives. Please note that diversification does not ensure a profit, or protect against loss. There is always the potential of losing money when you invest in securities, or other financial products. Investors should consider their investment objectives and risks carefully before investing.

Please note that this article is for general informational purposes only and is believed to be accurate as of the posting date but may be subject to change. The examples above are for illustrative purposes only and should not be considered investment advice.

Securities brokerage services are provided by Alpaca Securities LLC ("Alpaca Securities"), member [FINRA](https://www.finra.org/)/[SIPC](https://www.sipc.org/), a wholly-owned subsidiary of AlpacaDB, Inc. Technology and services are offered by AlpacaDB, Inc.

This is not an offer, solicitation of an offer, or advice to buy or sell securities or open a brokerage account in any jurisdiction where Alpaca Securities is not registered or licensed, as applicable.
</div>
