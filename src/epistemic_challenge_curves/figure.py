"""Create the paper's main challenge-curve figure as a dependency-free SVG."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .analysis import CLAUDE, GLM, GPT, GROK, MODEL_LABELS, MODEL_ORDER


COLORS = {
    CLAUDE: "#2563eb",
    GPT: "#d97706",
    GROK: "#6b8e23",
    GLM: "#db2777",
}
DASHES = {CLAUDE: "", GPT: "8 5", GROK: "3 4", GLM: "10 4 2 4"}


def write_challenge_curve_svg(results: dict[str, Any], output: Path) -> None:
    """Write a clear, GitHub-renderable version of Figure 1."""

    width, height = 900, 560
    # Chart contract: an ordered multi-series line chart showing how challenge
    # rate changes over six exact surprisal levels. Color is reinforced with
    # distinct line patterns, and the subtitle states the point denominator.
    left, right, top, bottom = 90, 35, 95, 125
    plot_width = width - left - right
    plot_height = height - top - bottom

    def x_position(surprisal: int) -> float:
        return left + (surprisal - 1) / 9 * plot_width

    def y_position(rate: float) -> float:
        return top + (1 - rate) * plot_height

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Challenge rate by objective surprisal</title>",
        "<desc>Four model challenge curves. Every plotted point contains 30 responses: six scenario families times five generations.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111827}.title{font-size:21px;font-weight:700}.subtitle{font-size:13px;fill:#4b5563}.tick{font-size:13px}.axis{font-size:15px}.legend{font-size:14px}</style>',
        '<text class="title" x="90" y="31">Challenge rate by objective surprisal</text>',
        '<text class="subtitle" x="90" y="55">Four models; each point contains 30 responses (six scenario families x five generations)</text>',
    ]

    for value in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y_position(value)
        svg.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#d1d5db" stroke-width="1"/>'
        )
        svg.append(
            f'<text class="tick" x="{left-12}" y="{y+4:.1f}" text-anchor="end">{value:g}</text>'
        )

    for surprisal in (1, 2, 4, 6, 8, 10):
        x = x_position(surprisal)
        svg.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+plot_height}" stroke="#f3f4f6" stroke-width="1"/>'
        )
        svg.append(
            f'<text class="tick" x="{x:.1f}" y="{top+plot_height+24}" text-anchor="middle">{surprisal}</text>'
        )

    svg.extend(
        [
            f'<line x1="{left}" y1="{top+plot_height}" x2="{width-right}" y2="{top+plot_height}" stroke="#111827" stroke-width="1.5"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_height}" stroke="#111827" stroke-width="1.5"/>',
            f'<text class="axis" x="{left+plot_width/2:.1f}" y="{height-70}" text-anchor="middle">Objective surprisal, -log10(p)</text>',
            f'<text class="axis" x="25" y="{top+plot_height/2:.1f}" text-anchor="middle" transform="rotate(-90 25 {top+plot_height/2:.1f})">Any-challenge rate</text>',
        ]
    )

    for model in MODEL_ORDER:
        points = results["models"][model]["challenge_curve"]
        coordinates = [
            (x_position(int(point["surprisal_log10"])), y_position(float(point["any_challenge_rate"])))
            for point in points
        ]
        path = " ".join(
            ("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}"
            for index, (x, y) in enumerate(coordinates)
        )
        dash = f' stroke-dasharray="{DASHES[model]}"' if DASHES[model] else ""
        svg.append(
            f'<path d="{path}" fill="none" stroke="{COLORS[model]}" stroke-width="3"{dash}/>'
        )
        for x, y in coordinates:
            svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="white" stroke="{COLORS[model]}" stroke-width="2.5"/>'
            )

    legend_y = height - 30
    legend_width = plot_width / len(MODEL_ORDER)
    for index, model in enumerate(MODEL_ORDER):
        x = left + index * legend_width
        dash = f' stroke-dasharray="{DASHES[model]}"' if DASHES[model] else ""
        svg.append(
            f'<line x1="{x:.1f}" y1="{legend_y}" x2="{x+30:.1f}" y2="{legend_y}" stroke="{COLORS[model]}" stroke-width="3"{dash}/>'
        )
        svg.append(
            f'<text class="legend" x="{x+38:.1f}" y="{legend_y+5}">{escape(MODEL_LABELS[model])}</text>'
        )

    svg.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")
