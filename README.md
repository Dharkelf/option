# option — CBOE Option Analysis Tool

## Overview

CLI tool for Austrian retail investors (broker: flatex.at) to analyse CBOE-listed options
before buying. Given a ticker, option type, target leverage and personal price estimates,
it fetches the live option chain, filters by leverage, and computes expected option values
and net P&L at 3-, 6- and 12-month horizons — net of flatex transaction costs.

---

## Architecture

```
config/settings.yaml
       |
       v
  main.py (CLI entry point — wires modules, no logic)
       |
       +---> market_data  ---> [spot price, 1yr history, realised vol, risk-free rate]
       |                              |
       +---> option_search  <---------+  [CBOE chain, leverage filter, ranking]
       |            |
       +---> valuation  <------------+  [Black-Scholes price, Greeks per candidate]
       |            |
       +---> scenarios  <-----------+  [option value at 3/6/12m per user estimates]
       |            |
       +---> costs  <---------------+  [flatex fees, EUR/USD conversion, net P&L]
       |            |
       +---> report  <--------------+  [console table + Parquet export]
```

### Module / Component Overview

```
┌──────────────────────────────────────────────────────────┐
│                        main.py                           │
└──────────────┬───────────────────────────────────────────┘
               |
   ┌───────────▼──────────┐
   │     market_data      │  yfinance: history, spot, IV, risk-free rate
   └───────────┬──────────┘
               |
   ┌───────────▼──────────┐
   │    option_search     │  CBOE chain -> filter by type + omega target
   └───────────┬──────────┘
               |
   ┌───────────▼──────────┐
   │      valuation       │  Black-Scholes price + Delta/Gamma/Theta/Vega/Omega
   └───────────┬──────────┘
               |
   ┌───────────▼──────────┐
   │      scenarios       │  User price estimates -> option value at 3/6/12m
   │                      │  + break-even + probability of profit
   └───────────┬──────────┘
               |
   ┌───────────▼──────────┐
   │        costs         │  flatex fees + EUR/USD conversion -> net P&L
   └───────────┬──────────┘
               |
   ┌───────────▼──────────┐
   │        report        │  Console table + data/processed/*.parquet
   └──────────────────────┘
```

### Incremental Fetch (market_data)

```
last stored timestamp
        |
        v
  fetch delta only (yfinance)
        |
        v
  append to data/raw/<ticker>.parquet
        |
        v
  return full DataFrame
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

Copy and fill the env template (only needed if future API keys are added):
```bash
cp .env.example .env
```

---

## Configuration

All parameters in `config/settings.yaml`. No hard-coded values anywhere else.

| Key | Description | Example |
|---|---|---|
| `underlying.ticker` | Yahoo Finance ticker symbol | `SGHC` |
| `underlying.dividend_yield` | Annual dividend yield (decimal) | `0.025` |
| `option.type` | `call` or `put` | `call` |
| `option.target_leverage` | Desired Omega (effective leverage) | `4.0` |
| `option.leverage_tolerance` | Accepted deviation from target Omega | `1.5` |
| `option.min_open_interest` | Liquidity guard — skip illiquid strikes | `50` |
| `scenario.price_3m` | Your estimated underlying price in 3 months | `15.50` |
| `scenario.price_6m` | Your estimated underlying price in 6 months | `17.00` |
| `scenario.price_12m` | Your estimated underlying price in 12 months | `20.00` |
| `scenario.flat_price` | Current price repeated — models the "nothing happens" case | `null` |
| `analysis.lookback_years` | Historical window for realised volatility | `1` |
| `analysis.risk_free_ticker` | Yahoo ticker for 10yr treasury yield | `^TNX` |
| `analysis.horizons_months` | List of evaluation horizons | `[3, 6, 12]` |
| `costs.flatex_base_fee_eur` | flatex base commission per trade | `5.90` |
| `costs.flatex_exchange_fee_eur` | Exchange/settlement fee per trade | `3.00` |
| `costs.spread_buffer_pct` | Extra % added to option ask for realistic fill | `2.0` |
| `costs.eur_usd_rate` | EUR/USD exchange rate for cost conversion | `1.09` |
| `logging.level` | `DEBUG`, `INFO`, `WARNING` | `INFO` |

---

## Usage

```bash
# Full analysis with current settings.yaml
python main.py

# Override ticker and option type on the command line
python main.py --ticker AAPL --type call

# Use a different config file
python main.py --config config/my_scenario.yaml
```

---

## Data

| File | Format | Description |
|---|---|---|
| `data/raw/<ticker>.parquet` | Parquet (UTC timestamps) | 1yr daily OHLCV history |
| `data/processed/candidates_<ticker>_<date>.parquet` | Parquet | All ranked candidates with Greeks + scenario P&L |

Schema of `candidates_*.parquet`:

| Column | Type | Description |
|---|---|---|
| `ticker` | str | Underlying symbol |
| `expiration` | date | Option expiration date |
| `strike` | float | Strike price (USD) |
| `type` | str | `call` or `put` |
| `market_price` | float | Option mid-price (USD) |
| `bs_price` | float | Black-Scholes theoretical price |
| `delta` | float | Delta |
| `omega` | float | Effective leverage |
| `iv` | float | Implied volatility (annualised) |
| `dte` | int | Days to expiry |
| `open_interest` | int | CBOE open interest |
| `volume` | int | Daily volume |
| `horizon_months` | int | 3, 6, or 12 |
| `spot_target` | float | User's price estimate at this horizon |
| `option_value` | float | BS-estimated option value at horizon |
| `entry_cost_eur` | float | Total cost to enter (1 contract, EUR) |
| `exit_value_eur` | float | Estimated exit value at horizon (EUR) |
| `net_pnl_eur` | float | Profit/loss after all fees (EUR) |
| `net_pnl_pct` | float | Return on invested capital (%) |
| `breakeven_spot` | float | Underlying price needed to break even |
| `prob_profit` | float | Probability of profit at expiry (log-normal) |

---

## Development

```bash
# Run tests
pytest tests/

# Lint + format + type check + tests
pre-commit run --all-files

# Add a new module
# 1. Create src/<module>/__init__.py and src/<module>/<module>.py
# 2. Add run() function with correct signature
# 3. Wire into main.py
# 4. Write tests/test_<module>.py
# 5. Update README.md and AGENTS.md module table
```

---

## Known Limitations

- yfinance option data can be stale (15-min delay, sometimes missing OI/volume).
- Black-Scholes assumes constant volatility and log-normal returns — real options deviate.
- Implied volatility fetched from near-ATM near-term option; may differ per strike (skew not modelled).
- EUR/USD rate is a static config value — not fetched live.
- No automatic earnings-date warning (user must check manually).
- flatex costs are approximate — check current Preisaushang at flatex.at.

---

## Future Improvements

1. Live EUR/USD rate via yfinance (`EURUSD=X`)
2. IV surface / skew modelling (volatility smile)
3. Earnings date warning from yfinance `calendar`
4. Position tracking: save opened position, re-run to update live P&L
5. Theta decay table: daily option value over the holding period
6. Scenario sensitivity: show P&L across a grid of underlying prices × dates

---

## References

- yfinance: https://github.com/ranaroussi/yfinance
- Black-Scholes formula: Hull, *Options, Futures, and Other Derivatives*, Ch. 15
- flatex Preisaushang: https://www.flatex.at/konditionen/
- CBOE options calendar: https://cdn.cboe.com/resources/options/Cboe2026OPTIONSCalendar.pdf
- 10yr treasury (^TNX): https://finance.yahoo.com/quote/%5ETNX
