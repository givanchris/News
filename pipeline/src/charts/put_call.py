"""Regenerate charts/put_call.svg from real SPY put/call history.

Reads data/options/indices.json (written by snapshots.append_indices_history),
takes the trailing window of SPY pc_volume readings, and draws the same
22-session line chart the fed-signal/options pages already embed as
<img src="charts/put_call.svg">. Replaces the old hand-authored,
manually-regenerated illustrative version with something the daily
cron keeps in sync automatically.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config

FF = 'font-family="\'JetBrains Mono\', monospace"'
WINDOW = 22
VMIN, VMAX = 0.6, 1.2


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def render_svg(points: list[tuple[str, float]]) -> str:
    """points: list of (date, spy_pc_volume_ratio), oldest first, already trimmed to window."""
    W, H = 620, 320
    x0, x1 = 54, 592
    y0, y_top = 288, 20

    n = len(points)
    if n == 0:
        raise ValueError("no put/call history to plot")

    def y_for(v: float) -> float:
        v = _clamp(v, VMIN, VMAX)
        return y0 - 20 - (y0 - 20 - y_top) * ((v - VMIN) / (VMAX - VMIN))

    xs = [x0] if n == 1 else [x0 + i * (x1 - x0) / (n - 1) for i in range(n)]
    vals = [v for _, v in points]
    pts = list(zip(xs, [y_for(v) for v in vals]))

    path_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) if n > 1 else ""

    gridlines = []
    for gv in [0.7, 0.8, 0.9, 1.0, 1.1]:
        gy = y_for(gv)
        gridlines.append(
            f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="#d8dfe9" stroke-width="1"/>'
            f'<text x="{x0-8}" y="{gy+3:.1f}" text-anchor="end" {FF} font-size="9" fill="#5a6f87">{gv}</text>'
        )

    fear_y = y_for(1.0)
    circles = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#1a5fd4"/>' for x, y in pts[:-1])
    last_x, last_y = pts[-1]
    last_val = vals[-1]
    first_label = points[0][0] if n > 1 else ""

    line_el = f'<path d="{path_d}" fill="none" stroke="#1a5fd4" stroke-width="1.8"/>' if path_d else ""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Equity put to call ratio over the trailing {n} sessions" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block">
  <rect x="0" y="0" width="{W}" height="{H}" fill="white"/>
  {"".join(gridlines)}
  <line x1="{x0}" y1="{fear_y:.1f}" x2="{x1}" y2="{fear_y:.1f}" stroke="#bf3232" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>
  <text x="{x1}" y="{fear_y-6:.1f}" text-anchor="end" {FF} font-size="8" fill="#bf3232">FEAR &gt; 1.0</text>
  {line_el}
  {circles}
  <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3.5" fill="#0e2240"/>
  <text x="{last_x-6:.1f}" y="{last_y-8:.1f}" text-anchor="end" {FF} font-size="9" font-weight="bold" fill="#0e2240">{last_val:.2f}</text>
  <text x="54" y="14" {FF} font-size="9" letter-spacing="0.1em" fill="#0e2240">EQUITY PUT/CALL RATIO · TRAILING {n} SESSION{"S" if n != 1 else ""}</text>
  <text x="54" y="308" {FF} font-size="8.5" fill="#5a6f87">{first_label}</text>
  <text x="592" y="308" text-anchor="end" {FF} font-size="8.5" fill="#5a6f87">Today</text>
</svg>'''


def load_spy_series(window: int = WINDOW) -> list[tuple[str, float]]:
    """Pull the trailing SPY pc_volume series from data/options/indices.json."""
    from ..storage import snapshots  # local import avoids a cycle at module load

    history = snapshots.read_indices_history()
    series: list[tuple[str, float]] = []
    for rec in history:
        date = rec.get("date")
        spy = next((i for i in rec.get("indices", []) if i.get("ticker") == "SPY"), None)
        if spy and spy.get("pc_volume") is not None and date:
            series.append((date, float(spy["pc_volume"])))
    series.sort(key=lambda p: p[0])
    return series[-window:]


def generate(out_path: Path | None = None, window: int = WINDOW) -> Path | None:
    """Regenerate charts/put_call.svg. Returns the written path, or None if no data yet."""
    series = load_spy_series(window)
    if not series:
        return None
    svg = render_svg(series)
    out_path = out_path or (config.CHARTS_DIR / "put_call.svg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg)
    return out_path
