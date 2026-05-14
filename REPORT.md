# REPORT.md — Observed Runtime Behaviour

This document records **actual observed results** from running the tool.
Update it alongside every code change that affects data flow, pricing, or output.

---

## Data Collection

| Run date | Ticker | Rows fetched | Date range | File size |
|---|---|---|---|---|
| 2026-05-14 | SGHC | ~252 | 2025-05 – 2026-05 | ~40 KB |

---

## Option Candidates

| Run date | Ticker | Chain expirations found | Candidates after leverage filter | Saved to |
|---|---|---|---|---|
| 2026-05-14 | SGHC | 7 (Jul/Aug/Sep/Oct/Nov/Dec/Jan) | 1 | data/processed/candidates_SGHC_2026-05-14.parquet |

**Observation:** Only 1 candidate passed the Omega=4x±1.5 filter.
- Jul–Sep expiries: all OTM strikes have omega >> 4x (short DTE = small premium relative to spot). ITM strikes have omega < 2.5x.
- Dec-18 K=10 (DTE ≈ 218): omega=3.8x — sole match.
- Dec-18 K=10 market price = 2.15 USD vs. intrinsic = 3.05 USD → **stale quote** (bid=0, ask=0). Now flagged via `stale_quote=True`.
- Workaround: set `target_leverage: 3.0` or `leverage_tolerance: 2.0` in input file to surface more candidates.

---

## Valuation Results

| Run date | Ticker | Spot | IV used | Risk-free rate | Candidates priced |
|---|---|---|---|---|---|
| 2026-05-14 | SGHC | 13.05 | 0.46 (realised; yfinance IV=0.000010 → fallback) | 4.5% | 1 |

**Observation:** yfinance returns `impliedVolatility = 0.000010` for most SGHC strikes.
The tool correctly falls back to `realised_vol = 0.46`. Near-ATM market IV was ~0.25 (25%) —
realised vol overstates it by ~84%, leading to inflated OTM BS prices. Acceptable for directional
planning; verify with live Yahoo Finance IV before final sizing.

---

## Scenario Results

| Run date | Ticker | Horizon | User price target | Best candidate omega | Net P&L (EUR) |
|---|---|---|---|---|---|
| 2026-05-14 | SGHC | 6 months | 17.00 USD | 3.8x | not computed (stale quote — no live fill) |

---

## Known Issues

1. **SGHC stale quotes (Dec K=10):** bid=ask=0, market_price < intrinsic. Now detected and flagged via `stale_quote=True`. User must verify live Ask in flatex/Yahoo before ordering.
2. **yfinance IV quality (SGHC):** per-strike IV reported as ~0.000010. Tool falls back to realised_vol. For accurate Greeks, check market IV manually on Yahoo Options page.
3. **EUR/USD rate:** previously static (1.09). Now fetched live from `EURUSD=X` at run time. Falls back to 1.09 if Yahoo Finance is unreachable.
4. **Single candidate for SGHC:** Omega=4x ±1.5 returns only Dec K=10. If more candidates are needed, set `target_leverage: 3.0` or `leverage_tolerance: 2.0` in the input YAML.
