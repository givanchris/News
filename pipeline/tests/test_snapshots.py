"""Published snapshots must stay strict JSON, and blank Yahoo rows must be skipped."""
import json
import math

import pandas as pd

from src import config
from src.data_providers.yfinance_provider import YFinanceProvider
from src.storage import snapshots


def _reject(token):
    raise AssertionError(f"non-standard JSON constant: {token}")


def test_write_latest_replaces_non_finite_values(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    payload = {"price": math.nan, "rows": [{"iv": math.inf}, {"iv": 0.4}]}

    path = snapshots.write_latest(payload)

    data = json.loads(path.read_text(), parse_constant=_reject)
    assert data == {"price": None, "rows": [{"iv": None}, {"iv": 0.4}]}


def test_quote_uses_last_row_with_a_close():
    class FakeTicker:
        info = {"shortName": "Test Co"}
        fast_info = None

        def history(self, **_):
            return pd.DataFrame({
                "Close": [100.0, 110.0, math.nan],
                "Volume": [1, 2, math.nan],
            })

    quote = YFinanceProvider()._quote_from_ticker_obj("TST", FakeTicker())

    assert quote.price == 110.0
    assert quote.change == 10.0


def test_quote_is_none_when_no_row_has_a_close():
    class FakeTicker:
        def history(self, **_):
            return pd.DataFrame({"Close": [math.nan], "Volume": [math.nan]})

    assert YFinanceProvider()._quote_from_ticker_obj("TST", FakeTicker()) is None
