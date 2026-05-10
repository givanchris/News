from datetime import datetime
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")


def now_mt_iso() -> str:
    return datetime.now(MT).isoformat(timespec="seconds")


def today_mt_str() -> str:
    return datetime.now(MT).strftime("%Y-%m-%d")
