"""Implied-volatility metrics: ATM IV, IV rank, IV percentile, skew.

ATM IV and skew are computed from a single front-month chain.
IV rank/percentile require a stored history of past IV values
(populated by the storage layer once Phase 3 ships).
"""
from typing import Optional
import pandas as pd


def atm_iv(calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> Optional[float]:
    """Average IV of strikes nearest spot, returned as a percentage (e.g. 24.5)."""
    if spot is None or spot <= 0 or calls is None or puts is None:
        return None
    if calls.empty or puts.empty:
        return None

    nearest_call = calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]
    nearest_put  = puts.iloc[(puts["strike"]  - spot).abs().argsort()[:1]]

    ivs: list[float] = []
    for row in (nearest_call, nearest_put):
        if row.empty:
            continue
        iv = row["impliedVolatility"].iloc[0]
        if iv is not None and not pd.isna(iv) and iv > 0:
            ivs.append(float(iv))

    if not ivs:
        return None
    return (sum(ivs) / len(ivs)) * 100.0  # convert decimal → %


def calculate_skew(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: float,
    otm_pct: float = 0.05,
) -> Optional[float]:
    """OTM put IV minus OTM call IV, in percentage points.

    Approximates 25-delta skew using strikes ±otm_pct from spot.
    Positive value → puts richer than calls (downside hedging premium).
    """
    if spot is None or spot <= 0 or calls is None or puts is None:
        return None
    if calls.empty or puts.empty:
        return None

    target_call = spot * (1 + otm_pct)
    target_put  = spot * (1 - otm_pct)

    call_row = calls.iloc[(calls["strike"] - target_call).abs().argsort()[:1]]
    put_row  = puts.iloc[(puts["strike"]  - target_put).abs().argsort()[:1]]
    if call_row.empty or put_row.empty:
        return None

    call_iv = call_row["impliedVolatility"].iloc[0]
    put_iv  = put_row["impliedVolatility"].iloc[0]
    if pd.isna(call_iv) or pd.isna(put_iv) or call_iv <= 0 or put_iv <= 0:
        return None

    return (float(put_iv) - float(call_iv)) * 100.0


def iv_rank(current_iv: Optional[float], history: list[float]) -> Optional[float]:
    """Where current IV sits within (min, max) of history. Returns 0–100."""
    if current_iv is None or not history:
        return None
    clean = [v for v in history if v is not None]
    if len(clean) < 2:
        return None
    lo, hi = min(clean), max(clean)
    if hi == lo:
        return None
    return ((current_iv - lo) / (hi - lo)) * 100.0


def iv_percentile(current_iv: Optional[float], history: list[float]) -> Optional[float]:
    """Percent of history strictly below current IV. Returns 0–100."""
    if current_iv is None or not history:
        return None
    clean = [v for v in history if v is not None]
    if not clean:
        return None
    below = sum(1 for v in clean if v < current_iv)
    return (below / len(clean)) * 100.0
