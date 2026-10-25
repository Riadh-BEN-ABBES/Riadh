"""Annotated optical micrograph of the fabricated 1x4 demultiplexer.

Annotation set follows the author's slide (optic.pptx). Pixel coordinates refer
to figures/micrograph_demux_raw.jpg (2576 x 1832 px). Scale: grating couplers on
a 127 um pitch are 525 px apart.
Run from the repository root:  python analysis/annotate_micrograph.py
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "figures" / "micrograph_demux_raw.jpg"
OUT = ROOT / "figures" / "fig08b_micrograph_annotated.jpg"
CROP = (185, 2330, 1775, 0)    # x0, x1, y_bottom, y_top: drops the neighbouring devices

WHITE = "white"
LAMBDA_COLOR = {1: "#ff2a2a", 2: "#29b6f6", 3: "#2ecc40", 4: "#ffc000"}
FS = 9

# grating-coupler labels: (text, x, y)
GC_LABELS = [
    ("Output\nGC1", 270, 215),
    ("Input\nGC", 270, 745),
    ("Output\nGC2", 270, 1270),
    ("Output\nGC3", 270, 1585),
]
# wavelength labels at the stage-2 outputs: (channels, x, y)
LAMBDAS = [                # one column, same x: MZI 2A outputs then MZI 2B outputs
    ((2,), 1880, 228),
    ((4,), 1880, 348),
    ((3,), 1880, 762),
    ((1,), 1880, 866),
]
# arrows: (text, target x, target y, text x, text y)
ARROWS = [
    ("Taper", 1912, 289, 1640, 150),
    ("Taper", 1988, 655, 1690, 760),
    ("Broadband\nDirectional Coupler", 1960, 1360, 1610, 1500),
]
GC_COLUMN_Y = [113, 637, 1162, 1692]   # right-hand grating-coupler column
PITCH_X = 2248


def main():
    im = Image.open(IMG)
    x0, x1, yb, yt = CROP
    w, h = x1 - x0, yb - yt
    fig, ax = plt.subplots(figsize=(7.16, 7.16 * h / w))
    ax.imshow(im)
    ax.set_xlim(x0, x1)
    ax.set_ylim(yb, yt)
    ax.set_axis_off()

    # dashed frames: demultiplexer and test-structure coupler
    ax.add_patch(Rectangle((385, 200), 1600, 690, fill=False, ec=WHITE,
                           ls=(0, (2, 2)), lw=1.0))
    ax.text(560, 265, "1×4 demux", color=WHITE, fontsize=FS, fontweight="bold",
            va="center")
    ax.add_patch(Rectangle((1955, 1090), 75, 310, fill=False, ec=WHITE,
                           ls=(0, (2, 2)), lw=1.0))

    for text, x, y in GC_LABELS:
        ax.text(x, y, text, color=WHITE, fontsize=FS, ha="center", va="center",
                linespacing=1.1)

    for chans, x, y in LAMBDAS:
        dx = 0
        for i, c in enumerate(chans):
            ax.text(x + dx, y, "λ" + "₀₁₂₃₄"[c], color=LAMBDA_COLOR[c],
                    fontsize=FS + 1, fontweight="bold", va="center")
            if i < len(chans) - 1:
                ax.text(x + dx + 58, y, "/", color=WHITE, fontsize=FS + 1, va="center")
                dx += 92

    for text, x, y, tx, ty in ARROWS:
        ax.annotate(text, (x, y), (tx, ty), color=WHITE, fontsize=FS,
                    ha="center", va="center", linespacing=1.1,
                    arrowprops=dict(arrowstyle="-|>", color=WHITE, lw=0.9,
                                    shrinkA=6, shrinkB=1))

    # 127 um pitch between the right-hand grating couplers
    for y0, y1 in zip(GC_COLUMN_Y[:-1], GC_COLUMN_Y[1:]):
        ax.annotate("", (PITCH_X, y0), (PITCH_X, y1),
                    arrowprops=dict(arrowstyle="<|-|>", color=WHITE, lw=0.9,
                                    shrinkA=0, shrinkB=0))
        ax.text(PITCH_X - 25, (y0 + y1) / 2, "127 µm", color=WHITE, fontsize=FS,
                ha="right", va="center")

    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(OUT, dpi=250, pil_kwargs={"quality": 90})


if __name__ == "__main__":
    main()
