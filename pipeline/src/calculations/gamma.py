"""Dealer gamma exposure (GEX) by strike, from real per-strike open interest.

Approximated via Black-Scholes gamma, since no free feed publishes actual
dealer positioning. Convention (see options.html's own "Assumptions" note):
dealers are treated as net long calls / short puts, so call open interest
contributes positive GEX and put open interest contributes negative GEX.
This is the standard retail-flow approximation used by SpotGamma-style
dashboards, not a real position feed.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional

import pandas as pd

RISK_FREE_RATE = 0.045
CONTRACT_MULTIPLIER = 100


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_gamma(spot: float, strike: float, t_years: float, iv: float,
             r: float = RISK_FREE_RATE) -> Optional[float]:
    """Black-Scholes gamma (identical for calls and puts at the same strike)."""
    if spot is None or strike is None or t_years is None or iv is None:
        return None
    if spot <= 0 or strike <= 0 or t_years <= 0 or iv <= 0:
        return None
    d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    return _norm_pdf(d1) / (spot * iv * math.sqrt(t_years))


def strike_gex(strike: float, oi: float, iv: float, spot: float,
                t_years: float, is_call: bool) -> Optional[float]:
    """Dollar gamma exposure ($ per 1% underlying move) for one strike's open interest."""
    g = bs_gamma(spot, strike, t_years, iv)
    if g is None or oi is None or pd.isna(oi) or oi <= 0:
        return None
    dollar_gamma = g * float(oi) * CONTRACT_MULTIPLIER * spot * spot * 0.01
    return dollar_gamma if is_call else -dollar_gamma


def _add_chain_to_totals(
    totals: dict[float, float],
    strikes: list[float],
    bucket_size: float,
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: float,
    t_years: float,
) -> None:
    for df, is_call in ((calls, True), (puts, False)):
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            k = row.get("strike")
            oi = row.get("openInterest")
            iv = row.get("impliedVolatility")
            if k is None or pd.isna(k):
                continue
            bucket = min(strikes, key=lambda s: abs(s - float(k)))
            if abs(bucket - float(k)) > bucket_size:
                continue  # outside the display window
            gex = strike_gex(float(k), oi, iv, spot, t_years, is_call)
            if gex is not None:
                totals[bucket] += gex / 1e9  # → $bn


def _finalize(spot: float, expiration_label: str, strikes: list[float],
              totals: dict[float, float], center: float) -> dict:
    buckets = [{"strike": s, "gex_bn": round(totals[s], 3)} for s in strikes]

    flip = center
    for i in range(len(buckets) - 1):
        a, b = buckets[i], buckets[i + 1]
        if a["gex_bn"] <= 0 <= b["gex_bn"] and a["gex_bn"] != b["gex_bn"]:
            frac = -a["gex_bn"] / (b["gex_bn"] - a["gex_bn"])
            flip = a["strike"] + frac * (b["strike"] - a["strike"])
            break

    return {
        "spot": round(float(spot), 2),
        "flip": round(flip, 1),
        "expiration": expiration_label,
        "buckets": buckets,
    }


def gamma_profile_by_strike(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: float,
    expiration: str,
    bucket_size: float = 10.0,
    window_buckets: int = 11,
) -> Optional[dict]:
    """Single-expiration GEX profile — mainly useful for tests. See
    `gamma_profile_near_term` for the multi-expiration version the pipeline
    actually uses (a single day's 0DTE chain badly overweights one strike).
    """
    if calls is None or puts is None or calls.empty or puts.empty:
        return None
    if spot is None or spot <= 0:
        return None
    try:
        exp_date = date.fromisoformat(str(expiration)[:10])
    except ValueError:
        return None
    t_years = max((exp_date - date.today()).days, 1) / 365.0

    center = round(spot / bucket_size) * bucket_size
    half = (window_buckets // 2) * bucket_size
    strikes = [center - half + i * bucket_size for i in range(window_buckets)]
    totals = {s: 0.0 for s in strikes}
    _add_chain_to_totals(totals, strikes, bucket_size, calls, puts, spot, t_years)
    return _finalize(spot, str(expiration)[:10], strikes, totals, center)


def gamma_profile_near_term(
    chains: list,  # list[OptionsChain] — typed loosely to avoid importing data_providers here
    spot: float,
    bucket_size: float = 10.0,
    window_buckets: int = 11,
) -> Optional[dict]:
    """Aggregate net GEX across every supplied near-term expiration (e.g. all
    expiries through the next monthly) into strike buckets centered on spot.

    A single day's chain is dominated by whatever is expiring that day (SPY
    lists daily expirations, so the very next date is often 0-1 DTE and
    wildly overweights one strike) — summing several near-dated expirations
    gives a profile closer to what "front-month" positioning actually means.
    """
    if not chains or spot is None or spot <= 0:
        return None

    center = round(spot / bucket_size) * bucket_size
    half = (window_buckets // 2) * bucket_size
    strikes = [center - half + i * bucket_size for i in range(window_buckets)]
    totals = {s: 0.0 for s in strikes}

    used_expirations = []
    for chain in chains:
        try:
            exp_date = date.fromisoformat(str(chain.expiration)[:10])
        except ValueError:
            continue
        t_years = max((exp_date - date.today()).days, 1) / 365.0
        _add_chain_to_totals(totals, strikes, bucket_size, chain.calls, chain.puts, spot, t_years)
        used_expirations.append(str(chain.expiration)[:10])

    if not used_expirations:
        return None

    label = f"{used_expirations[0]}..{used_expirations[-1]}" if len(used_expirations) > 1 else used_expirations[0]
    return _finalize(spot, label, strikes, totals, center)
