"""yfinance implementation of the Provider interface.

Notes:
- yfinance prices are 15-minute delayed (free data feed).
- Options chains include strike, lastPrice, bid/ask, volume, openInterest,
  impliedVolatility per row.
- Index symbols use the ^ prefix (^VIX, ^VIX9D, ^VIX3M, ^VIX6M).
"""
import time
from typing import Optional

import pandas as pd
import yfinance as yf

from .base import Provider, Quote, OptionsChain


class YFinanceProvider(Provider):
    def __init__(self, throttle_sec: float = 0.15):
        self.throttle_sec = throttle_sec

    # ── internals ────────────────────────────────────────────────────────
    def _quote_from_ticker_obj(self, sym: str, t: yf.Ticker) -> Optional[Quote]:
        try:
            hist = t.history(period="5d", auto_adjust=False)
        except Exception:
            return None
        if hist is None or hist.empty:
            return None

        last = hist.iloc[-1]
        price = float(last["Close"])
        if len(hist) >= 2:
            prev_close = float(hist.iloc[-2]["Close"])
        else:
            prev_close = price

        # info is sometimes slow / missing — best-effort name lookup
        name = sym
        try:
            info = t.fast_info
            # fast_info doesn't carry name; fall back to .info if needed
            name = getattr(info, "shortName", None) or sym
        except Exception:
            pass
        if name == sym:
            try:
                full = t.info or {}
                name = full.get("shortName") or full.get("longName") or sym
            except Exception:
                pass

        change = price - prev_close
        change_pct = (change / prev_close * 100.0) if prev_close else 0.0
        volume = int(last["Volume"]) if pd.notna(last["Volume"]) else 0

        return Quote(
            ticker=sym,
            name=name,
            price=price,
            change=change,
            change_pct=change_pct,
            volume=volume,
        )

    # ── public API ───────────────────────────────────────────────────────
    def get_quote(self, ticker: str) -> Optional[Quote]:
        time.sleep(self.throttle_sec)
        return self._quote_from_ticker_obj(ticker, yf.Ticker(ticker))

    def get_options_chains(self, ticker: str, max_expirations: int = 4) -> list[OptionsChain]:
        time.sleep(self.throttle_sec)
        t = yf.Ticker(ticker)
        try:
            expirations = list(t.options or [])[:max_expirations]
        except Exception:
            return []
        if not expirations:
            return []

        spot_q = self._quote_from_ticker_obj(ticker, t)
        spot = spot_q.price if spot_q else 0.0

        chains: list[OptionsChain] = []
        for exp in expirations:
            try:
                chain = t.option_chain(exp)
            except Exception:
                continue
            chains.append(OptionsChain(
                ticker=ticker,
                expiration=exp,
                spot=spot,
                calls=chain.calls,
                puts=chain.puts,
            ))
            time.sleep(self.throttle_sec)
        return chains

    def get_index_value(self, ticker: str) -> Optional[Quote]:
        return self.get_quote(ticker)
