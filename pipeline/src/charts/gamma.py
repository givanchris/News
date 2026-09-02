"""Regenerate charts/gamma.svg from real per-strike dealer gamma exposure.

Reads data/options/gamma.json (written by run.py from a live SPY option
chain via calculations/gamma.py) and draws the by-strike bar chart the
options page embeds as <img src="charts/gamma.svg">.
"""
from __future__ import annotations

from pathlib import Path

from .. import config

FF = 'font-family="\'JetBrains Mono\', monospace"'


def render_svg(spot: float, flip: float, buckets: list[dict], ticker: str = "SPY") -> str:
    W, H = 620, 340
    x0, x1 = 58, 592
    y_mid = 165
    y_top = 34
    y_bot = 235
    y_strike_labels = 252
    y_caption = 320

    n = len(buckets)
    gap = 10
    bw = (x1 - x0 - gap * (n - 1)) / n

    max_abs = max((abs(b["gex_bn"]) for b in buckets), default=0) or 1.0
    half_range = min(y_mid - y_top, y_bot - y_mid) - 20
    scale = half_range / (max_abs * 1.1)

    bars = []
    for i, b in enumerate(buckets):
        v = b["gex_bn"]
        s = b["strike"]
        bx = x0 + i * (bw + gap)
        bh = abs(v) * scale
        by = y_mid - bh if v > 0 else y_mid
        color = "#2c7a57" if v > 0 else ("#b23b2e" if v < 0 else "#d8dfe9")
        cx = bx + bw / 2
        label_y = by - 6 if v >= 0 else y_mid + bh + 12
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" {FF} font-size="7.5" fill="#5a6f87">{v:+.1f}</text>'
            f'<text x="{cx:.1f}" y="{y_strike_labels}" text-anchor="middle" {FF} font-size="8" fill="#5a6f87">{s:.0f}</text>'
        )

    flip_idx = min(range(n), key=lambda i: abs(buckets[i]["strike"] - flip)) if n else 0
    flip_x = x0 + flip_idx * (bw + gap) + bw / 2

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Dealer gamma exposure by strike for {ticker}, negative below spot and positive above, gamma flip near {flip:.0f}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block">
  <rect x="0" y="0" width="{W}" height="{H}" fill="white"/>
  <line x1="{x0}" y1="{y_mid}" x2="{x1}" y2="{y_mid}" stroke="#0e2240" stroke-width="1"/>
  <line x1="{flip_x:.1f}" y1="{y_top}" x2="{flip_x:.1f}" y2="{y_bot}" stroke="#5a6f87" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>
  {"".join(bars)}
  <text x="{flip_x:.1f}" y="{y_top-8}" text-anchor="middle" {FF} font-size="8.5" font-weight="bold" fill="#0e2240">SPOT ${spot:.0f} / FLIP &#8776; {flip:.0f}</text>
  <text x="58" y="16" {FF} font-size="9" letter-spacing="0.1em" fill="#0e2240">DEALER GAMMA EXPOSURE ($BN / 1% MOVE) BY STRIKE</text>
  <text x="58" y="{y_caption}" {FF} font-size="8.5" fill="#5a6f87">{ticker} · near-term expirations · negative gamma below spot = trend-amplifying</text>
</svg>'''


def generate(out_path: Path | None = None) -> Path | None:
    """Regenerate charts/gamma.svg from the latest stored gamma snapshot."""
    from ..storage import snapshots  # local import avoids a cycle at module load

    snap = snapshots.read_gamma_snapshot()
    if not snap or not snap.get("buckets"):
        return None
    svg = render_svg(snap["spot"], snap["flip"], snap["buckets"])
    out_path = out_path or (config.CHARTS_DIR / "gamma.svg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg)
    return out_path
