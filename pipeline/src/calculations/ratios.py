"""Put/Call ratio calculations.

All functions return float or None — None when data is insufficient.
"""
from typing import Optional
import pandas as pd

from ..data_providers.base import OptionsChain


def _safe_div(num: float, den: float) -> Optional[float]:
    if den is None or den == 0 or pd.isna(den):
        return None
    return num / den


def put_call_volume_ratio(calls: pd.DataFrame, puts: pd.DataFrame) -> Optional[float]:
    """P/C ratio for a single chain: sum(put volume) / sum(call volume)."""
    cv = float(calls["volume"].fillna(0).sum())
    pv = float(puts["volume"].fillna(0).sum())
    return _safe_div(pv, cv)


def put_call_open_interest_ratio(calls: pd.DataFrame, puts: pd.DataFrame) -> Optional[float]:
    """P/C OI ratio for a single chain."""
    coi = float(calls["openInterest"].fillna(0).sum())
    poi = float(puts["openInterest"].fillna(0).sum())
    return _safe_div(poi, coi)


def aggregate_pc_volume(chains: list[OptionsChain]) -> Optional[float]:
    """P/C volume aggregated across multiple expirations."""
    total_calls = total_puts = 0.0
    for c in chains:
        total_calls += float(c.calls["volume"].fillna(0).sum())
        total_puts  += float(c.puts["volume"].fillna(0).sum())
    return _safe_div(total_puts, total_calls)


def aggregate_pc_oi(chains: list[OptionsChain]) -> Optional[float]:
    """P/C open interest aggregated across multiple expirations."""
    total_calls = total_puts = 0.0
    for c in chains:
        total_calls += float(c.calls["openInterest"].fillna(0).sum())
        total_puts  += float(c.puts["openInterest"].fillna(0).sum())
    return _safe_div(total_puts, total_calls)
