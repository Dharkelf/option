"""Prints the live-verification checklist and final product recommendation."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.scenarios.analyzer import CandidateAnalysis

logger = logging.getLogger(__name__)

_SEP = "=" * 70
_LINE = "-" * 70


def _fetch_earnings_dates(ticker: str) -> list[date]:
    """Returns upcoming earnings dates from yfinance calendar. Empty list on failure."""
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None:
            return []
        raw = cal.get("Earnings Date", []) if isinstance(cal, dict) else []
        return [pd.Timestamp(d).date() for d in raw if d]
    except Exception:
        return []


def print_verification_checklist(
    candidates: list[OptionCandidate],
    market: MarketDataResult,
    cfg: dict[str, Any],
) -> None:
    """Prints an actionable checklist of what the user must verify live before buying."""
    ticker = market.ticker
    spot = market.spot
    target_omega: float = cfg["option"]["target_leverage"]
    tol: float = cfg["option"]["leverage_tolerance"]
    holding_months: int = cfg["analysis"]["holding_months"]

    earnings = _fetch_earnings_dates(ticker)

    print(f"\n{_SEP}")
    print("SCHRITT 2 — LIVE-VERIFIKATION (vor dem Kauf)")
    print(_SEP)
    print(f"\nBasiswert: {ticker}  |  Spot: {spot:.2f}  |  Haltedauer: {holding_months} Monate")
    print(f"Ziel-Omega: {target_omega:.1f}x  (Toleranz ±{tol:.1f})\n")

    if earnings:
        print("EARNINGS-TERMINE im Radar:")
        for ed in sorted(earnings):
            within = "  ← INNERHALB der Haltedauer!" if _within_holding(ed, holding_months) else ""
            print(f"  {ed}{within}")
        print(
            "  → Earnings können starke IV-Bewegung auslösen (IV-Crush nach Zahlen).\n"
            "  → Position vor dem Termin oder nach Zahlen aufbauen?\n"
        )

    top = candidates[:3]
    for i, c in enumerate(top, 1):
        label = chr(64 + i)
        print(f"\n[{label}]  {ticker} {c.option_type.upper()}  Strike {c.strike:.2f}  "
              f"Verfall {c.expiration}  ({c.days_to_expiry} Tage)")
        print(f"     Modell-Ask: {c.market_price:.2f}  |  BS-Preis: {c.bs_price:.2f}  "
              f"|  Breakeven: {c.breakeven:.2f}  |  Omega: {c.omega_val:.1f}x")

        # Earnings warning per candidate
        for ed in sorted(earnings):
            if date.today() < ed <= c.expiration:
                print(  # noqa: E501
                    f"     *** EARNINGS {ed} LIEGT INNERHALB DER LAUFZEIT — IV-Crush möglich! ***"
                )

        print("\n     1. Yahoo Finance Options:")
        print(f"        https://finance.yahoo.com/quote/{ticker}/options")
        print(f"        → Verfall '{c.expiration}' wählen → Strike {c.strike:.2f}")
        print(f"        Live Ask:       _______ USD   (Modell: {c.market_price:.2f})")
        print("        Live Bid:       _______ USD")
        print(f"        Open Interest:  _______       (Modell: {c.open_interest:,})")
        if c.open_interest < 100:
            print("        *** WARNUNG: Geringer OI — nur mit strikter Limit-Order handeln! ***")
        print(f"        Live IV:        _______ %     (Modell: {c.implied_vol * 100:.0f}%)")

        print("\n     2. flatex-Terminal:")
        print(f"        → Suche '{ticker}' → Optionen → {c.expiration} → Strike {c.strike:.2f}")
        print("        → Ask-Kurs notieren. IMMER Limit-Order, niemals Market!")
        print(f"        → 1 Kontrakt = 100 Aktien → Investition ≈ "
              f"{c.market_price * 100 / cfg['costs']['eur_usd_rate']:.0f} EUR Prämie + Gebühren")

        print("\n     3. Eigener Hebel-Check (mit Live-Ask):")
        print("        Omega = Delta × Spot / Live-Ask")
        print(f"              = {c.delta_val:.3f} × {spot:.2f} / Live-Ask")
        print(f"        Beispiel bei Ask={c.market_price:.2f}: Omega = {c.omega_val:.1f}x")

        print(f"\n{_LINE}")

    print(
        "\nNach der Verifikation Optionen vergleichen und Empfehlung unten beachten.\n"
    )


def print_recommendation(
    analyses: list[CandidateAnalysis],
    cfg: dict[str, Any],
    expected_price: float | None,
) -> None:
    """Prints the top-ranked candidate with full investment rationale."""
    if not analyses:
        print("\nKeine Kandidaten — Hebel-Toleranz erhöhen oder anderen Strike prüfen.")
        return

    holding_months: int = cfg["analysis"]["holding_months"]
    investment_eur: float = cfg["costs"]["investment_eur"]

    # Pick best at holding_months horizon by target P&L %
    def score(a: CandidateAnalysis) -> float:
        h = next((x for x in a.horizons if x.months == holding_months), None)
        if h is None:
            return -999.0
        return h.net_pnl_target_pct

    ranked = sorted(analyses, key=score, reverse=True)
    best = ranked[0]
    c = best.candidate
    h = next((x for x in best.horizons if x.months == holding_months), best.horizons[-1])

    print(f"\n{_SEP}")
    print("EMPFEHLUNG")
    print(_SEP)
    print(
        f"\n  {c.ticker} {c.option_type.upper()}  Strike {c.strike:.2f}  "
        f"Verfall {c.expiration}  ({c.days_to_expiry} Tage)\n"
    )
    print(f"  Modell-Einstieg:    {c.market_price:.2f} USD / Kontrakt")
    print(f"  Gesamtkosten:       {h.entry_cost_eur:.2f} EUR / Kontrakt  "
          f"(inkl. {cfg['costs']['flatex_base_fee_eur']:.2f} + "
          f"{cfg['costs']['flatex_exchange_fee_eur']:.2f} EUR Gebühren)")
    print(f"  Kontrakte mit {investment_eur:.0f} EUR: {h.contracts}")
    print(f"  Breakeven Spot:     {c.breakeven:.2f} USD")
    print(f"  Delta:              {c.delta_val:.3f}   Gamma: {c.gamma_val:.4f}")
    print(f"  Omega (Hebel):      {c.omega_val:.1f}x")
    print(f"  Theta / Tag:        {c.theta_day:.4f} USD  (Zeitwertverlust pro Kalendertag)")
    print(f"  Vega / 1% IV:       {c.vega_val:.4f} USD")
    print(f"  Open Interest:      {c.open_interest:,}   Volumen: {c.volume:,}")
    print()
    print(f"  Szenario-Analyse bei Haltedauer {holding_months} Monate:")
    if expected_price is not None:
        print(f"    Kurserwartung {expected_price:.2f}:")
        print(f"      Optionswert:  {h.option_value_target:.2f} USD")
        print(f"      Netto P&L:    {h.net_pnl_target_eur:+.2f} EUR / Kontrakt")
        print(f"      Return:       {h.net_pnl_target_pct:+.1f}%")
        print(f"      Gesamtertrag: {h.total_pnl_target_eur:+.2f} EUR ({h.contracts} Kontrakte)")
        print(f"      Profit-Wksl:  {h.prob_profit_target * 100:.0f}%")
    print(f"    Flat-Szenario (Kurs bleibt bei {h.spot_flat:.2f}):")
    print(f"      Optionswert:  {h.option_value_flat:.2f} USD")
    print(f"      Netto P&L:    {h.net_pnl_flat_eur:+.2f} EUR / Kontrakt")
    print(f"      Return:       {h.net_pnl_flat_pct:+.1f}%")
    print(f"      Gesamtertrag: {h.total_pnl_flat_eur:+.2f} EUR ({h.contracts} Kontrakte)")
    print(f"\n{_SEP}\n")


def _within_holding(earnings_date: date, holding_months: int) -> bool:
    from datetime import date as dt
    from datetime import timedelta

    cutoff = dt.today() + timedelta(days=holding_months * 30)
    return dt.today() < earnings_date <= cutoff
