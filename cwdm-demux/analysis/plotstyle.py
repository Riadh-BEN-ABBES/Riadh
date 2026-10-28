"""Shared figure style for the report and the GitHub README.

Two profiles are produced from the same plotting code:
  paper : IEEE column widths, serif 8 pt  -> figures/paper/<stem>.pdf and .png (300 dpi)
  web   : wider canvas, sans-serif 11-13 pt -> figures/<stem>.png (150 dpi, opaque RGB)

The web PNGs are the ones referenced in README.md: opaque white background (readable
in GitHub dark mode), text large enough once GitHub scales the image to the page
width, and file sizes kept small.
"""
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
SIGNATURE = "© Riadh Ben Abbes 2026"

PROFILES = {
    "paper": dict(w1=3.5, w2=7.16, font=8, small=6.5, lw=0.8, dpi=300,
                  family="serif"),
    "web": dict(w1=6.0, w2=10.0, font=11, small=9.5, lw=1.3, dpi=150,
                family="sans-serif"),
}
# Full-width web figures are shrunk more by GitHub (page ~880 px wide) than
# single-column ones (shown with width="600" in the README): enlarge their text
# so that every figure ends up with the same apparent font size.
WEB_WIDE_FONT_SCALE = 1.2


def use(profile, cols=1):
    """Apply the rcParams of a profile and return its settings."""
    p = dict(PROFILES[profile])
    if profile == "web" and cols == 2:
        p["font"] *= WEB_WIDE_FONT_SCALE
        p["small"] *= WEB_WIDE_FONT_SCALE
    plt.rcdefaults()
    plt.rcParams.update({
        "font.family": p["family"], "font.size": p["font"],
        "legend.fontsize": p["small"], "axes.linewidth": 0.8,
        "lines.linewidth": p["lw"], "svg.fonttype": "path",
        "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": True, "ytick.right": True,
        "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.4,
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.facecolor": "white",
    })
    return p


def figsize(profile, cols=1, aspect=0.68):
    """Figure size in inches: cols=1 (single column) or 2 (full width)."""
    p = PROFILES[profile]
    w = p["w1"] if cols == 1 else p["w2"]
    return (w, w * aspect)


def _to_rgb(path):
    """Drop the alpha channel so the image is opaque on any background."""
    im = Image.open(path)
    if im.mode != "RGB":
        im.convert("RGB").save(path, optimize=True)


def save(fig, stem, profile):
    p = PROFILES[profile]
    if profile == "paper":
        out = FIG / "paper"
        out.mkdir(parents=True, exist_ok=True)
        fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
        fig.savefig(out / f"{stem}.png", dpi=p["dpi"], bbox_inches="tight")
        _to_rgb(out / f"{stem}.png")
    else:
        FIG.mkdir(exist_ok=True)
        fig.text(0.995, 0.005, SIGNATURE, ha="right", va="bottom",
                 fontsize=0.75 * p["small"], color="0.55")
        fig.savefig(FIG / f"{stem}.png", dpi=p["dpi"], bbox_inches="tight")
        _to_rgb(FIG / f"{stem}.png")
    plt.close(fig)


def build(plot_fn, stem):
    """Run plot_fn(profile) for both profiles and save the results."""
    for profile in ("paper", "web"):
        fig = plot_fn(profile)
        save(fig, stem, profile)
