"""Abstract Provider interface.

Implementations: yfinance_provider.YFinanceProvider.
Future: polygon_provider, alpha_vantage_provider — same interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class Quote:
    ticker: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int


@dataclass
class OptionsChain:
    ticker: str
    expiration: str        # YYYY-MM-DD
    spot: float
    calls: pd.DataFrame    # required cols: strike, volume, openInterest, impliedVolatility
    puts: pd.DataFrame


class Provider(ABC):
    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[Quote]:
        ...

    @abstractmethod
    def get_options_chains(self, ticker: str, max_expirations: int = 4) -> list[OptionsChain]:
        ...

    @abstractmethod
    def get_index_value(self, ticker: str) -> Optional[Quote]:
        """For VIX & VIX-term-structure tickers (^VIX, ^VIX9D, ...)."""
        ...
