# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "matplotlib>=3.8",
# ]
# ///
"""Render the figure that compares the aggregate listing with the sub-type listings.

The numbers were measured on the live ITU-T pages on 2026-11-27: the meeting
``T25-SG13-250303`` holds 549 temporary documents in six sub-types, and the
aggregate listing of the meeting previews five documents per sub-type.

Run it with::

    uv run docs/assets/figures/listing-counts.py --variant light
    uv run docs/assets/figures/listing-counts.py --variant dark
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

#: The sub-types of the temporary documents of T25-SG13-250303, in the order
#: the aggregate listing offers them, with the number of documents each of the
#: sub-type listings holds.
SUBTYPES = ("GEN", "PLEN", "WP1", "WP2", "WP3", "WP4")
DOCUMENTS = (82, 71, 118, 63, 86, 129)

#: The number of documents the aggregate listing previews per sub-type.
PREVIEW = 5

#: Okabe-Ito: distinguishable under protan, deutan and tritan vision.
BLUE = "#0072B2"
ORANGE = "#E69F00"

VARIANTS = {
    "light": {"background": "#FFFFFF", "text": "#27272A", "grid": "#D4D4D8", "accent": BLUE, "muted": ORANGE},
    "dark": {"background": "#18181B", "text": "#FAFAFA", "grid": "#3F3F46", "accent": "#56B4E9", "muted": "#E8B339"},
}


def build(variant: str) -> plt.Figure:
    """Return the figure for the given variant.

    Args:
        variant: ``light`` or ``dark``.

    Returns:
        The matplotlib figure.
    """
    palette = VARIANTS[variant]
    fig, ax = plt.subplots(figsize=(7.0, 3.6), constrained_layout=True)
    fig.patch.set_facecolor(palette["background"])
    ax.set_facecolor(palette["background"])

    positions = range(len(SUBTYPES))
    offset = 0.2
    ax.barh(
        [value - offset for value in positions],
        [PREVIEW] * len(SUBTYPES),
        height=0.36,
        color=palette["muted"],
        label="rows in the aggregate listing",
    )
    ax.barh(
        [value + offset for value in positions],
        DOCUMENTS,
        height=0.36,
        color=palette["accent"],
        label="documents in the sub-type listing",
    )

    ax.set_yticks(list(positions), SUBTYPES)
    ax.invert_yaxis()
    ax.set_xlim(0, max(DOCUMENTS) * 1.14)
    ax.set_xlabel("documents", color=palette["text"], fontsize=9)
    ax.tick_params(colors=palette["text"], labelsize=9)
    ax.xaxis.grid(True, color=palette["grid"], linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(palette["grid"])

    legend = ax.legend(
        frameon=False,
        fontsize=9,
        loc="lower left",
        bbox_to_anchor=(0, 1.02, 1, 0.1),
        mode="expand",
        borderaxespad=0,
        ncols=2,
    )
    for text in legend.get_texts():
        text.set_color(palette["text"])

    for index, count in enumerate(DOCUMENTS):
        ax.text(
            count + 2,
            index + offset,
            str(count),
            va="center",
            ha="left",
            fontsize=8,
            color=palette["text"],
        )

    return fig


def main() -> None:
    """Render the requested variant next to this script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="light")
    arguments = parser.parse_args()

    fig = build(arguments.variant)
    output = Path(__file__).with_name(f"listing-counts-{arguments.variant}.svg")
    fig.savefig(output, format="svg", facecolor=fig.get_facecolor())
    print(f"Rendered: {output}")


if __name__ == "__main__":
    main()
