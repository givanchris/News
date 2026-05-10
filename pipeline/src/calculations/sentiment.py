"""Rule-based sentiment classifiers.

Thresholds live in src/config.py — edit there, not here.
"""
from typing import Optional

from .. import config


def classify_sentiment(
    pc_volume: Optional[float],
    iv_rank: Optional[float] = None,
) -> tuple[str, str]:
    """Returns (label, plain-English reason).

    Label is one of: 'bullish', 'neutral', 'bearish'.
    """
    if pc_volume is None:
        return ("neutral", "Insufficient options volume to classify.")

    parts: list[str] = []

    if pc_volume < config.PUT_CALL_BULLISH:
        label = "bullish"
        parts.append(
            f"P/C volume {pc_volume:.2f} below the {config.PUT_CALL_BULLISH:.2f} bullish threshold"
        )
    elif pc_volume > config.PUT_CALL_BEARISH:
        label = "bearish"
        parts.append(
            f"P/C volume {pc_volume:.2f} above the {config.PUT_CALL_BEARISH:.2f} bearish threshold"
        )
    else:
        label = "neutral"
        parts.append(
            f"P/C volume {pc_volume:.2f} in the neutral zone "
            f"({config.PUT_CALL_BULLISH:.2f}–{config.PUT_CALL_BEARISH:.2f})"
        )

    if iv_rank is not None:
        if iv_rank > config.IV_RANK_HIGH:
            parts.append(f"IV rank {iv_rank:.0f} elevated (fear premium)")
        elif iv_rank < config.IV_RANK_LOW:
            parts.append(f"IV rank {iv_rank:.0f} low (complacency)")
        else:
            parts.append(f"IV rank {iv_rank:.0f} moderate")

    return (label, " · ".join(parts) + ".")


def sector_sentiment_score(pc_volume: Optional[float]) -> str:
    """Lightweight sector classifier: P/C volume → label only."""
    if pc_volume is None:
        return "neutral"
    if pc_volume < config.PUT_CALL_BULLISH:
        return "bullish"
    if pc_volume > config.PUT_CALL_BEARISH:
        return "bearish"
    return "neutral"


def classify_regime(spy_pc: Optional[float], vix: Optional[float]) -> tuple[str, str]:
    """Market regime from SPY P/C + VIX level."""
    bull = bear = 0
    notes: list[str] = []

    if spy_pc is not None:
        if spy_pc < config.PUT_CALL_BULLISH:
            bull += 1
            notes.append(f"SPY P/C {spy_pc:.2f} bullish")
        elif spy_pc > config.PUT_CALL_BEARISH:
            bear += 1
            notes.append(f"SPY P/C {spy_pc:.2f} bearish")
        else:
            notes.append(f"SPY P/C {spy_pc:.2f} neutral")

    if vix is not None:
        if vix < config.VIX_LOW:
            bull += 1
            notes.append(f"VIX {vix:.1f} low (complacency risk)")
        elif vix > config.VIX_HIGH:
            bear += 1
            notes.append(f"VIX {vix:.1f} elevated")
        else:
            notes.append(f"VIX {vix:.1f} moderate")

    if bull > bear:
        regime = "risk-on"
    elif bear > bull:
        regime = "risk-off"
    else:
        regime = "mixed"

    return regime, (" · ".join(notes) + ".") if notes else "Insufficient data."
