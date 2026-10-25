"""Concept figure: 4-channel CWDM link (MUX, single fiber, DEMUX).

Channel colors match the annotated micrograph (lambda1 red, lambda2 blue,
lambda3 green, lambda4 orange).
Run from the repository root:  python analysis/cwdm_concept.py
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

import plotstyle

CHANNELS = [(1, 1553, "#e41a1c"), (2, 1555, "#1f9ce0"),
            (3, 1557, "#2ca02c"), (4, 1559, "#ff9f1c")]


def plot(profile):
    P = plotstyle.use(profile, 2)
    plt.rcParams["axes.grid"] = False
    fig, ax = plt.subplots(figsize=plotstyle.figsize(profile, 2, 0.34))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.4)
    ax.set_axis_off()

    ys = [2.55, 1.95, 1.35, 0.75]          # channel rows
    lw = 2.4 * P["lw"]
    fiber = [1.80, 1.70, 1.60, 1.50]       # stripes inside the single fiber

    # trapezoids: MUX (wide on the left) and DEMUX (wide on the right)
    mux = Polygon([(2.6, 3.0), (3.6, 2.35), (3.6, 0.95), (2.6, 0.3)],
                  closed=True, fc="white", ec="k", lw=1.2, zorder=3)
    demux = Polygon([(6.4, 2.35), (7.4, 3.0), (7.4, 0.3), (6.4, 0.95)],
                    closed=True, fc="white", ec="k", lw=1.2, zorder=3)
    ax.add_patch(mux)
    ax.add_patch(demux)
    ax.text(3.1, 1.65, "CWDM\nMUX", ha="center", va="center", zorder=4,
            linespacing=1.2)
    ax.text(6.9, 1.65, "CWDM\nDEMUX", ha="center", va="center", zorder=4,
            linespacing=1.2)

    for (k, lam, col), y, yf in zip(CHANNELS, ys, fiber):
        ax.plot([0.9, 2.6], [y, y], color=col, lw=lw, solid_capstyle="butt")
        ax.plot([3.6, 6.4], [yf, yf], color=col, lw=lw * 0.9, solid_capstyle="butt")
        ax.plot([7.4, 9.1], [y, y], color=col, lw=lw, solid_capstyle="butt")
        ax.text(9.2, y, f"λ{'₁₂₃₄'[k - 1]}  {lam} nm", color=col, va="center",
                fontweight="bold")
    # fiber cladding outline
    ax.plot([3.6, 6.4], [1.90, 1.90], color="0.35", lw=0.8)
    ax.plot([3.6, 6.4], [1.40, 1.40], color="0.35", lw=0.8)

    ax.text(1.75, 3.05, "Transmitters", ha="center", va="bottom")
    ax.text(8.25, 3.05, "Receivers", ha="center", va="bottom")
    ax.text(5.0, 2.05, "Single fiber", ha="center", va="bottom")
    ax.text(6.9, 0.05, "this work", ha="center", va="bottom",
            fontsize=P["small"], style="italic")
    fig.subplots_adjust(0.01, 0.01, 0.92, 0.99)
    return fig


if __name__ == "__main__":
    plotstyle.build(plot, "fig01_cwdm_concept")
