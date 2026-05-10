"""Disk persistence for snapshots.

- latest.json          → most recent market snapshot (overwritten daily)
- tickers/<SYM>.json   → per-ticker chronological history (one entry per day)
- sectors.json         → sector heatmap history
- vix.json             → VIX & term-structure history
"""
import json
from pathlib import Path
from typing import Any

from .. import config


# ── latest snapshot ──────────────────────────────────────────────────────
def write_latest(payload: dict[str, Any]) -> Path:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.OUTPUT_DIR / "latest.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


# ── helpers ──────────────────────────────────────────────────────────────
def _read_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _upsert_by_date(history: list[dict], record: dict) -> list[dict]:
    """Replace any existing same-date entry, then sort chronologically."""
    today = record.get("date")
    out = [h for h in history if h.get("date") != today]
    out.append(record)
    out.sort(key=lambda h: h.get("date", ""))
    return out


# ── per-ticker history ───────────────────────────────────────────────────
def read_ticker_history(ticker: str) -> list[dict]:
    return _read_list(config.OUTPUT_DIR / "tickers" / f"{ticker}.json")


def append_ticker_history(ticker: str, snapshot: dict[str, Any]) -> Path:
    tdir = config.OUTPUT_DIR / "tickers"
    tdir.mkdir(parents=True, exist_ok=True)
    path = tdir / f"{ticker}.json"
    history = _upsert_by_date(read_ticker_history(ticker), snapshot)
    path.write_text(json.dumps(history, indent=2, default=str))
    return path


def ticker_history_record(date: str, ticker_snap: dict) -> dict:
    """Trim a full ticker snapshot to the time-series fields worth keeping."""
    return {
        "date": date,
        "price": ticker_snap.get("price"),
        "pc_volume_ratio": ticker_snap.get("pc_volume_ratio"),
        "pc_oi_ratio": ticker_snap.get("pc_oi_ratio"),
        "iv_atm": ticker_snap.get("iv_atm"),
        "iv_rank": ticker_snap.get("iv_rank"),
        "iv_percentile": ticker_snap.get("iv_percentile"),
        "skew_25d": ticker_snap.get("skew_25d"),
        "sentiment": ticker_snap.get("sentiment"),
        "unusual_activity": ticker_snap.get("unusual_activity"),
    }


# ── sectors history ──────────────────────────────────────────────────────
def append_sectors_history(date: str, sectors: list[dict]) -> Path:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.OUTPUT_DIR / "sectors.json"
    history = _upsert_by_date(_read_list(path), {"date": date, "sectors": sectors})
    path.write_text(json.dumps(history, indent=2, default=str))
    return path


# ── VIX history ──────────────────────────────────────────────────────────
def append_vix_history(date: str, vix: dict, term: list[dict]) -> Path:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.OUTPUT_DIR / "vix.json"
    record = {
        "date": date,
        "value": vix.get("value"),
        "change": vix.get("change"),
        "change_pct": vix.get("change_pct"),
        "term": term,
    }
    history = _upsert_by_date(_read_list(path), record)
    path.write_text(json.dumps(history, indent=2, default=str))
    return path
