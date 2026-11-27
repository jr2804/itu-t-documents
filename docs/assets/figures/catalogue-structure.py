# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Render the hierarchy of a study group as a light/dark SVG pair.

The figure is drawn from explicit coordinates so the four kinds of row keep
their order: the plenary, the working groups, the other groups and the
questions. The dashed edges carry the one relation the page needs: a question
is handled by its working group, or by the plenary when it is a plenary
question.

Run it with::

    uv run docs/assets/figures/catalogue-structure.py --variant light
    uv run docs/assets/figures/catalogue-structure.py --variant dark
"""

from __future__ import annotations

import argparse
from pathlib import Path

WIDTH = 760
HEIGHT = 430

PALETTES = {
    "light": {
        "background": "#FFFFFF",
        "text": "#27272A",
        "detail": "#52525B",
        "node": "#F4F4F5",
        "border": "#D4D4D8",
        "arrow": "#71717A",
    },
    "dark": {
        "background": "#18181B",
        "text": "#FAFAFA",
        "detail": "#A1A1AA",
        "node": "#27272A",
        "border": "#3F3F46",
        "arrow": "#A1A1AA",
    },
}


def node(x: int, y: int, width: int, height: int, title: str, detail: str, palette: dict[str, str]) -> str:
    """Return the SVG for one rounded node with a title and a detail line."""
    center = x + width / 2
    return f"""\
  <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="{palette["node"]}" stroke="{palette["border"]}" stroke-width="1.5"/>
  <text x="{center}" y="{y + 22}" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="15" font-weight="600" fill="{palette["text"]}">{title}</text>
  <text x="{center}" y="{y + 42}" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{palette["detail"]}">{detail}</text>
"""


def edge(path: str, palette: dict[str, str], *, dashed: bool = False) -> str:
    """Return one arrow with the marker of the palette."""
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return (
        f'  <path d="{path}" fill="none" stroke="{palette["arrow"]}" stroke-width="1.5"'
        f'{dash} marker-end="url(#arrow)"/>\n'
    )


def build(variant: str) -> str:
    """Return the SVG document for the given variant."""
    palette = PALETTES[variant]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img">',
        "  <title>The structure of a study group</title>",
        "  <desc>A study period holds a study group. The study group lists a plenary, working groups, other groups and questions. The plenary and the working groups handle the questions.</desc>",
        "  <defs>",
        f'    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="{palette["arrow"]}"/></marker>',
        "  </defs>",
        f'  <rect width="{WIDTH}" height="{HEIGHT}" fill="{palette["background"]}"/>',
        "  <!-- Edges are drawn before the nodes so every line ends cleanly on a border. -->",
    ]
    # The period holds the group.
    parts.append(edge("M380 72 L380 110", palette))
    # The group lists its four kinds of row.
    parts.append(edge("M380 164 L380 188 L120 188 L120 208", palette))
    parts.append(edge("M380 164 L380 208", palette))
    parts.append(edge("M380 164 L380 188 L620 188 L620 208", palette))
    # The plenary and the working groups handle the questions.
    parts.append(edge("M120 266 L120 300 L250 300 L250 328", palette, dashed=True))
    parts.append(edge("M380 266 L380 328", palette, dashed=True))

    parts.extend(
        [
            node(280, 20, 200, 52, "Study period", "2025-2028", palette),
            node(280, 112, 200, 52, "Study group", "SG12", palette),
            node(20, 210, 200, 56, "Plenary", "PLEN", palette),
            node(280, 210, 200, 56, "Working groups", "WP1/12 · WP2/12 · WP3/12", palette),
            node(540, 210, 200, 56, "Other groups", "regional · focus · …", palette),
            node(150, 330, 460, 60, "Questions under study", "Q1/12 · Q2/12 · Q4/12 · …", palette),
            f'  <text x="388" y="97" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{palette["detail"]}">holds</text>',
            f'  <text x="388" y="314" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{palette["detail"]}">handles</text>',
        ]
    )
    parts.append("</svg>\n")
    return "\n".join(parts)


def main() -> None:
    """Render the requested variant next to this script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(PALETTES), default="light")
    arguments = parser.parse_args()

    output = Path(__file__).with_name(f"catalogue-structure-{arguments.variant}.svg")
    output.write_text(build(arguments.variant), encoding="utf-8")
    print(f"Rendered: {output}")


if __name__ == "__main__":
    main()
