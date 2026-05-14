"""Sensitivity grid — option value and net P&L at spot scenarios × time points."""
from __future__ import annotations

import logging

import pandas as pd

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)

_DEFAULT_PCT_CHANGES = [-0.40, -0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30, 0.40, 0.50]


def build_sensitivity_grid(
    candidate: OptionCandidate,
    market: MarketDataResult,
    cfg: dict,
    expected_price: float | None = None,
) -> pd.DataFrame:
    """
    Rows: spot price scenarios (percentage changes from current spot + user target).
    Cols: time points (heute, 3m, 6m, holding_months, 12m) — clipped to DTE.
    Values: option value in USD and estimated net P&L in EUR (1 contract).
    """
    from src.costs.model import CostModelFactory  # avoid circular import

    otype = candidate.option_type
    K = candidate.strike
    r = market.risk_free_rate
    iv = candidate.implied_vol
    q: float = cfg["underlying"]["dividend_yield"]
    spot = market.spot
    holding_months: int = cfg["analysis"]["holding_months"]
    horizons: list[int] = cfg["analysis"]["horizons_months"]

    cost_model = CostModelFactory.from_config(cfg)

    # Spot scenarios
    spot_scenarios = sorted(
        {round(spot * (1.0 + p), 2) for p in _DEFAULT_PCT_CHANGES}
    )
    if expected_price is not None:
        rounded = round(expected_price, 2)
        if rounded not in spot_scenarios:
            spot_scenarios.append(rounded)
            spot_scenarios.sort()

    # Time points: 0 + standard horizons + holding_months, all <= dte
    time_months = sorted(set([0] + horizons + [holding_months]))
    time_months = [m for m in time_months if m * 30 <= candidate.days_to_expiry]

    rows = []
    for s in spot_scenarios:
        tag = "ziel" if (expected_price is not None and abs(s - expected_price) < 0.01) else ""
        row: dict = {
            "spot_usd": s,
            "aenderung_pct": round((s / spot - 1.0) * 100.0, 1),
            "markierung": tag,
        }
        for m in time_months:
            days_elapsed = int(m * 30.44)
            days_remaining = max(candidate.days_to_expiry - days_elapsed, 0)
            T = days_remaining / 365.0
            val = bs.price(otype, s, K, T, r, iv, q)
            pnl_eur = cost_model.net_pnl_eur(candidate.market_price, val)
            label = "heute" if m == 0 else f"{m}m"
            row[f"wert_{label}_usd"] = round(val, 2)
            row[f"pnl_{label}_eur"] = round(pnl_eur, 0)
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(
        "sensitivity grid: %d spot scenarios x %d time points",
        len(spot_scenarios), len(time_months),
    )
    return df
