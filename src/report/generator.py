"""Full report: candidate table, theta decay, sensitivity grid, Parquet export."""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.scenarios.analyzer import CandidateAnalysis
from src.utils.paths import PathRepository

logger = logging.getLogger(__name__)


def run(
    cfg: dict,
    market: MarketDataResult,
    analyses: list[CandidateAnalysis],
    theta_tables: dict[str, pd.DataFrame],
    sensitivity_grids: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Prints full analysis to stdout and saves Parquet. Returns candidate summary DataFrame."""
    if not analyses:
        logger.warning("keine Kandidaten zum Ausgeben")
        return pd.DataFrame()

    holding_months: int = cfg["analysis"]["holding_months"]
    ticker = market.ticker

    df = _build_summary_df(analyses, holding_months)
    _print_candidate_table(df, holding_months)
    _print_theta_tables(theta_tables)
    _print_sensitivity_grids(sensitivity_grids)

    paths = PathRepository(cfg)
    paths.ensure_dirs()
    out = paths.processed_file(f"candidates_{ticker}_{date.today()}")
    df.to_parquet(out)
    logger.info("Ergebnisse gespeichert: %s", out)

    return df


def _build_summary_df(analyses: list[CandidateAnalysis], holding_months: int) -> pd.DataFrame:
    rows = []
    for a in analyses:
        c = a.candidate
        h = next((x for x in a.horizons if x.months == holding_months), a.horizons[-1])
        rows.append(
            {
                "ticker": c.ticker,
                "verfall": c.expiration,
                "strike": round(c.strike, 2),
                "typ": c.option_type,
                "dte": c.days_to_expiry,
                "ask_usd": round(c.market_price, 4),
                "bs_usd": round(c.bs_price, 4),
                "delta": round(c.delta_val, 3),
                "gamma": round(c.gamma_val, 4),
                "theta_tag_usd": round(c.theta_day, 4),
                "vega_1pct_usd": round(c.vega_val, 4),
                "omega": round(c.omega_val, 2),
                "iv_pct": round(c.implied_vol * 100, 1),
                "open_interest": c.open_interest,
                "volumen": c.volume,
                "breakeven": round(c.breakeven, 2),
                "haltedauer_m": holding_months,
                "spot_ziel": round(h.spot_target, 2),
                "option_wert_ziel_usd": round(h.option_value_target, 4),
                "option_wert_flat_usd": round(h.option_value_flat, 4),
                "kosten_eur": round(h.entry_cost_eur, 2),
                "kontrakte": h.contracts,
                "pnl_ziel_eur": round(h.net_pnl_target_eur, 2),
                "pnl_flat_eur": round(h.net_pnl_flat_eur, 2),
                "pnl_ziel_pct": round(h.net_pnl_target_pct, 1),
                "pnl_flat_pct": round(h.net_pnl_flat_pct, 1),
                "gesamt_pnl_ziel_eur": round(h.total_pnl_target_eur, 2),
                "gesamt_pnl_flat_eur": round(h.total_pnl_flat_eur, 2),
                "profit_wksl_ziel_pct": round(h.prob_profit_target * 100, 1),
                "profit_wksl_flat_pct": round(h.prob_profit_flat * 100, 1),
            }
        )

    df = pd.DataFrame(rows)
    df.sort_values("pnl_ziel_pct", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _print_candidate_table(df: pd.DataFrame, holding_months: int) -> None:
    cols = [
        "verfall", "strike", "typ", "dte", "omega",
        "ask_usd", "breakeven", "spot_ziel",
        "option_wert_ziel_usd", "kosten_eur", "kontrakte",
        "pnl_ziel_eur", "pnl_ziel_pct",
        "pnl_flat_eur", "pnl_flat_pct",
        "profit_wksl_ziel_pct", "open_interest",
    ]
    available = [c for c in cols if c in df.columns]
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"SCHRITT 1 — KANDIDATEN-ÜBERSICHT (Haltedauer: {holding_months} Monate)")
    print(sep)
    print(df[available].to_string(index=True))
    print(
        "\nSpalten: pnl_ziel = Ihr Kursziel | pnl_flat = Kurs bleibt unverändert\n"
        "Sortiert nach pnl_ziel_pct (beste Rendite zuerst)\n"
    )


def _print_theta_tables(theta_tables: dict[str, pd.DataFrame]) -> None:
    if not theta_tables:
        return
    sep = "=" * 70
    print(f"\n{sep}")
    print("THETA-DECAY — Zeitwertverlust bei konstantem Kurs")
    print(sep)
    for label, df in theta_tables.items():
        print(f"\n  {label}")
        print(df.to_string(index=False))
        print()


def _print_sensitivity_grids(sensitivity_grids: dict[str, pd.DataFrame]) -> None:
    if not sensitivity_grids:
        return
    sep = "=" * 70
    print(f"\n{sep}")
    print("SENSITIVITÄTS-GRID — Optionswert (USD) und P&L (EUR) je Kursszenario")
    print(sep)
    for label, df in sensitivity_grids.items():
        print(f"\n  {label}")
        # Show value columns only to keep it readable
        val_cols = [c for c in df.columns if c.startswith("wert_") or c in ("spot_usd", "aenderung_pct", "markierung")]
        pnl_cols = [c for c in df.columns if c.startswith("pnl_") or c in ("spot_usd", "aenderung_pct", "markierung")]
        print("  Optionswert in USD:")
        print(df[val_cols].to_string(index=False))
        print("\n  Netto-P&L in EUR (1 Kontrakt, inkl. Gebühren):")
        print(df[pnl_cols].to_string(index=False))
        print()
