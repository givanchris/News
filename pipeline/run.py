"""CLI for the Options Sentiment pipeline.

Examples:
  python run.py snapshot AAPL          # one ticker → JSON to stdout
  python run.py market                 # full snapshot → latest.json
  python run.py market --dry-run       # full snapshot → stdout (no write)
  python run.py market --tickers AAPL TSLA NVDA
"""
from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Optional

from src import config
from src.data_providers.base import OptionsChain, Provider
from src.data_providers.yfinance_provider import YFinanceProvider
from src.calculations import ratios as R
from src.calculations import volatility as V
from src.calculations import sentiment as S
from src.storage import snapshots
from src.charts import put_call as put_call_chart
from src.utils.dates import now_mt_iso, today_mt_str


# ── per-ticker snapshot ──────────────────────────────────────────────────
def _detect_unusual(chains: list[OptionsChain]) -> bool:
    """Flag if any strike's volume > UNUSUAL_VOL_MULT × open interest."""
    for c in chains:
        for df in (c.calls, c.puts):
            if df is None or df.empty:
                continue
            vol = df["volume"].fillna(0)
            oi  = df["openInterest"].fillna(0)
            mask = (oi > 0) & (vol >= oi * config.UNUSUAL_VOL_MULT) & (vol >= config.UNUSUAL_MIN_VOL)
            if mask.any():
                return True
    return False


def build_ticker_snapshot(provider: Provider, ticker: str) -> Optional[dict[str, Any]]:
    quote = provider.get_quote(ticker)
    if not quote:
        return None

    chains = provider.get_options_chains(ticker, max_expirations=3)
    if not chains:
        return {
            "ticker": ticker,
            "name": quote.name,
            "price": round(quote.price, 2),
            "change": round(quote.change, 2),
            "change_pct": round(quote.change_pct, 2),
            "volume": quote.volume,
            "pc_volume_ratio": None,
            "pc_oi_ratio": None,
            "iv_atm": None,
            "iv_rank": None,
            "iv_percentile": None,
            "skew_25d": None,
            "unusual_activity": False,
            "sentiment": "neutral",
            "sentiment_reason": "No options chain available for this ticker.",
        }

    pc_vol = R.aggregate_pc_volume(chains)
    pc_oi  = R.aggregate_pc_oi(chains)

    front = chains[0]
    iv = V.atm_iv(front.calls, front.puts, front.spot)
    skew = V.calculate_skew(front.calls, front.puts, front.spot)
    unusual = _detect_unusual(chains)

    # IV rank/percentile from stored history (empty until Phase 3 populates).
    history = [h.get("iv_atm") for h in snapshots.read_ticker_history(ticker)
               if h.get("iv_atm") is not None]
    ivr = V.iv_rank(iv, history)
    ivp = V.iv_percentile(iv, history)

    label, reason = S.classify_sentiment(pc_vol, ivr)

    return {
        "ticker": ticker,
        "name": quote.name,
        "price": round(quote.price, 2),
        "change": round(quote.change, 2),
        "change_pct": round(quote.change_pct, 2),
        "volume": quote.volume,
        "pc_volume_ratio": round(pc_vol, 4) if pc_vol is not None else None,
        "pc_oi_ratio":     round(pc_oi, 4)  if pc_oi  is not None else None,
        "iv_atm":          round(iv, 2)     if iv     is not None else None,
        "iv_rank":         round(ivr, 1)    if ivr    is not None else None,
        "iv_percentile":   round(ivp, 1)    if ivp    is not None else None,
        "skew_25d":        round(skew, 2)   if skew   is not None else None,
        "unusual_activity": bool(unusual),
        "sentiment": label,
        "sentiment_reason": reason,
    }


# ── market-wide rows ─────────────────────────────────────────────────────
def build_index_row(provider: Provider, idx: dict) -> dict:
    quote = provider.get_quote(idx["ticker"])
    chains = provider.get_options_chains(idx["ticker"], max_expirations=2)
    pc_vol = R.aggregate_pc_volume(chains) if chains else None
    pc_oi  = R.aggregate_pc_oi(chains) if chains else None
    return {
        "ticker": idx["ticker"],
        "name": idx["name"],
        "price":      round(quote.price, 2)      if quote else None,
        "change":     round(quote.change, 2)     if quote else None,
        "change_pct": round(quote.change_pct, 2) if quote else None,
        "pc_volume":  round(pc_vol, 4) if pc_vol is not None else None,
        "pc_oi":      round(pc_oi, 4)  if pc_oi  is not None else None,
        "sentiment":  S.sector_sentiment_score(pc_vol),
    }


def build_sector_row(provider: Provider, sec: dict) -> dict:
    chains = provider.get_options_chains(sec["ticker"], max_expirations=2)
    pc_vol = R.aggregate_pc_volume(chains) if chains else None
    iv = (V.atm_iv(chains[0].calls, chains[0].puts, chains[0].spot)
          if chains else None)
    history = [h.get("iv_atm") for h in snapshots.read_ticker_history(sec["ticker"])
               if h.get("iv_atm") is not None]
    ivr = V.iv_rank(iv, history) if iv is not None else None
    return {
        "ticker": sec["ticker"],
        "name": sec["name"],
        "pc_volume": round(pc_vol, 4) if pc_vol is not None else None,
        "iv_rank":   round(ivr, 1)    if ivr    is not None else None,
        "sentiment": S.sector_sentiment_score(pc_vol),
    }


def build_vix(provider: Provider) -> dict:
    spot = provider.get_index_value("^VIX")
    term = []
    for sym, label in config.VIX_TERM:
        q = provider.get_index_value(sym)
        if q:
            term.append({"label": label, "value": round(q.price, 2)})
    return {
        "vix": {
            "value":      round(spot.price, 2)      if spot else None,
            "change":     round(spot.change, 2)     if spot else None,
            "change_pct": round(spot.change_pct, 2) if spot else None,
        },
        "vix_term_structure": term,
    }


# ── CLI commands ─────────────────────────────────────────────────────────
def cmd_snapshot(args: argparse.Namespace) -> None:
    provider = YFinanceProvider()
    snap = build_ticker_snapshot(provider, args.ticker.upper())
    if not snap:
        print(f"Ticker {args.ticker} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(snap, indent=2))


def cmd_market(args: argparse.Namespace) -> None:
    provider = YFinanceProvider()

    print("→ VIX & term structure", file=sys.stderr)
    vix = build_vix(provider)

    print("→ Index P/C ratios (SPY/QQQ/IWM)", file=sys.stderr)
    indices = [build_index_row(provider, i) for i in config.INDICES]

    print("→ Sector ETFs", file=sys.stderr)
    sectors = [build_sector_row(provider, s) for s in config.SECTORS]

    universe = args.tickers if args.tickers else config.WATCHLIST
    print(f"→ Watchlist ({len(universe)} tickers)", file=sys.stderr)
    tickers = []
    for sym in universe:
        print(f"  · {sym}", file=sys.stderr)
        s = build_ticker_snapshot(provider, sym)
        if s:
            tickers.append(s)

    spy_pc = next((i["pc_volume"] for i in indices if i["ticker"] == "SPY"), None)
    regime, regime_summary = S.classify_regime(spy_pc, vix["vix"].get("value"))

    payload = {
        "as_of": now_mt_iso(),
        "is_mock": False,
        "market": {
            **vix,
            "indices": indices,
            "regime": regime,
            "regime_summary": regime_summary,
        },
        "sectors": sectors,
        "tickers": tickers,
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    out = snapshots.write_latest(payload)
    print(f"\n✓ Wrote {out}", file=sys.stderr)

    # ── History persistence ──────────────────────────────────────────────
    if not args.no_history:
        date = today_mt_str()
        for t in tickers:
            snapshots.append_ticker_history(t["ticker"], snapshots.ticker_history_record(date, t))
        snapshots.append_sectors_history(date, sectors)
        snapshots.append_vix_history(date, vix["vix"], vix["vix_term_structure"])
        snapshots.append_indices_history(date, indices)
        print(f"✓ Appended history for {date}", file=sys.stderr)

    # ── Chart regeneration ────────────────────────────────────────────────
    if not args.no_history and not args.no_charts:
        chart_path = put_call_chart.generate()
        if chart_path:
            print(f"✓ Regenerated {chart_path}", file=sys.stderr)
        else:
            print("· Skipped put_call.svg — no indices history yet", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(prog="options-dashboard",
                                description="Options sentiment pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("snapshot", help="Snapshot one ticker → JSON to stdout")
    sp.add_argument("ticker")
    sp.set_defaults(func=cmd_snapshot)

    mp = sub.add_parser("market", help="Full market snapshot → latest.json")
    mp.add_argument("--dry-run", action="store_true",
                    help="Print to stdout without writing any files")
    mp.add_argument("--no-history", action="store_true",
                    help="Write latest.json only, skip per-ticker / sector / VIX history")
    mp.add_argument("--no-charts", action="store_true",
                    help="Skip regenerating charts/put_call.svg from history")
    mp.add_argument("--tickers", nargs="*",
                    help="Override the default watchlist")
    mp.set_defaults(func=cmd_market)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
