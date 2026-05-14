"""Generates ranked console table and Parquet export for all candidates x horizons."""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from src.scenarios.analyzer import CandidateAnalysis
from src.utils.paths import PathRepository

logger = logging.getLogger(__name__)

_LIQUIDITY_WARN_OI = 100


def _warn_liquidity(oi: int, ticker: str, strike: float) -> None:
    if oi < _LIQUIDITY_WARN_OI:
        logger.warning("LOW LIQUIDITY: %s K=%.2f OI=%d — use limit orders", ticker, strike, oi)


def _build_row(a: CandidateAnalysis, months: int) -> dict:
    c = a.candidate
    h = next((x for x in a.horizons if x.months == months), None)
    if h is None:
        return {}

    row: dict = {
        "ticker": c.ticker,
        "expiration": c.expiration,
        "strike": round(c.strike, 2),
        "type": c.option_type,
        "dte": c.days_to_expiry,
        "market_price_usd": round(c.market_price, 4),
        "bs_price_usd": round(c.bs_price, 4),
        "delta": round(c.delta_val, 3),
        "gamma": round(c.gamma_val, 4),
        "theta_day": round(c.theta_day, 4),
        "vega_1pct": round(c.vega_val, 4),
        "omega": round(c.omega_val, 2),
        "iv": round(c.implied_vol, 3),
        "open_interest": c.open_interest,
        "volume": c.volume,
        "breakeven_spot": round(c.breakeven, 2),
        "horizon_months": months,
        "spot_target_usd": round(h.spot_target, 2),
        "spot_flat_usd": round(h.spot_flat, 2),
        "option_value_target_usd": round(h.option_value_target, 4),
        "option_value_flat_usd": round(h.option_value_flat, 4),
        "prob_profit_target_pct": round(h.prob_profit_target * 100, 1),
        "prob_profit_flat_pct": round(h.prob_profit_flat * 100, 1),
    }

    for attr in ("entry_cost_eur", "exit_value_target_eur", "exit_value_flat_eur",
                 "net_pnl_target_eur", "net_pnl_flat_eur",
                 "net_pnl_target_pct", "net_pnl_flat_pct"):
        val = getattr(h, attr, None)
        row[attr] = round(float(val), 2) if val is not None else None

    return row


def run(cfg: dict, analyses: list[CandidateAnalysis]) -> pd.DataFrame:
    if not analyses:
        logger.warning("no candidates to report")
        return pd.DataFrame()

    horizons: list[int] = cfg["analysis"]["horizons_months"]
    rows: list[dict] = []
    for a in analyses:
        _warn_liquidity(a.candidate.open_interest, a.candidate.ticker, a.candidate.strike)
        for m in horizons:
            row = _build_row(a, m)
            if row:
                rows.append(row)

    df = pd.DataFrame(rows)
    df.sort_values(["horizon_months", "net_pnl_target_pct"], ascending=[True, False], inplace=True)
    df.reset_index(drop=True, inplace=True)

    _print_console(df)

    paths = PathRepository(cfg)
    paths.ensure_dirs()
    ticker = analyses[0].candidate.ticker
    out_path = paths.processed_file(f"candidates_{ticker}_{date.today()}")
    df.to_parquet(out_path)
    logger.info("results saved: %s", out_path)

    return df


def _print_console(df: pd.DataFrame) -> None:
    cols = [
        "horizon_months", "expiration", "strike", "type", "dte", "omega",
        "market_price_usd", "breakeven_spot",
        "spot_target_usd", "option_value_target_usd",
        "net_pnl_target_eur", "net_pnl_target_pct",
        "net_pnl_flat_eur", "net_pnl_flat_pct",
        "prob_profit_target_pct", "open_interest",
    ]
    available = [c for c in cols if c in df.columns]
    logger.info(
        "\n\n=== OPTION ANALYSIS RESULTS ===\n%s\n",
        df[available].to_string(index=False),
    )
