"""Figures and checks generated directly from the GDS layout.

  fig02_bdc_layout   : ebeam_bdc_te1550 geometry with dimensions read from the GDS
Also prints the path-length differences of every MZI, computed from the
waveguide lengths stored by SiEPIC in the layout.
Run from the repository root:  python analysis/layout_figures.py
"""
import re
from pathlib import Path

import numpy as np
import klayout.db as db
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

import plotstyle

ROOT = Path(__file__).resolve().parents[1]
GDS = ROOT / "layout" / "EBeam_Riadh_CWDM.gds"
SI = (1, 0)
FLOORPLAN = (99, 0)

STRUCTURES = {                      # cell name -> (label, color)
    "cwdm2_fsr2nm": ("1×4 demultiplexer", "#1f77b4"),
    "mzi1_fsr4nm": ("MZI stage 1 (test)", "#ff7f0e"),
    "mzi2_fsr8nm": ("MZI stage 2 (test)", "#2ca02c"),
    "bdc": ("BDC (test)", "#9467bd"),
}


def polygons(region, dbu):
    return [np.array([(p.x * dbu, p.y * dbu) for p in poly.each_point_hull()])
            for poly in region.each()]


def mzi_delta_l(ly):
    """Arm lengths of every MZI from the 'Length=' labels of the SiEPIC waveguides."""
    out = {}
    for c in ly.each_cell():
        if c.name not in STRUCTURES:
            continue
        lengths = []
        for inst in c.each_inst():
            if not inst.cell.name.startswith("Waveguide"):
                continue
            for s in inst.cell.shapes(ly.layer(68, 0)).each():
                if s.is_text():
                    m = re.match(r"Spice_param:wg_length=([\d.eE-]+).*points=\"(\[\[.*\]\])\"",
                                 s.text.string)
                    if m:
                        pts = np.array(eval(m.group(2)))
                        lengths.append((float(m.group(1)) * 1e6, pts))
        out[c.name] = lengths
    return out


def main():
    ly = db.Layout()
    ly.read(str(GDS))
    top = ly.top_cells()[0]
    dbu = ly.dbu
    si = ly.layer(*SI)

    # --- path-length differences: arms are the waveguides that start and end on
    # the same x (U-shaped detours between two BDCs); pair them by position
    for name, wgs in mzi_delta_l(ly).items():
        arms = [(L, p) for L, p in wgs
                if np.isclose(p[0][0], p[-1][0]) or np.isclose(p[0][1], p[-1][1])]
        arms = [(L, p) for L, p in arms if len(p) == 6]
        arms.sort(key=lambda a: a[1][0][0] + a[1][0][1])
        for i in range(0, len(arms) - 1, 2):
            (l1, p1), (l2, p2) = arms[i], arms[i + 1]
            print(f"{STRUCTURES[name][0]:22s} arms {l1:8.3f} / {l2:8.3f} um  "
                  f"-> dL = {abs(l1 - l2):.3f} um")

    fp = top.dbbox()
    print(f"cell footprint: {fp.width():.1f} x {fp.height():.1f} um")

    # --- broadband directional coupler geometry
    bdc = ly.cell("ebeam_bdc_te1550")
    breg = db.Region(bdc.begin_shapes_rec(si)).merged()
    bpolys = polygons(breg, dbu)

    def cut(x):
        c = db.Region(db.Box(int(x / dbu), -10000, int(x / dbu) + 1, 10000))
        return sorted((p.bbox().bottom * dbu, p.bbox().top * dbu) for p in (breg & c).each())

    x_cpl = 0.0                               # inside the coupling section
    x_ph = 9.0                                # centre of the phase-control section
    (a0, a1), (b0, b1) = cut(x_cpl)
    (c0, c1), (d0, d1) = cut(x_ph)
    print(f"BDC coupling section: widths {a1-a0:.3f} / {b1-b0:.3f} um, gap {b0-a1:.3f} um")
    print(f"BDC phase section   : widths {c1-c0:.3f} / {d1-d0:.3f} um, gap {d0-c1:.3f} um")

    def plot_bdc(profile):
        P = plotstyle.use(profile, 2)
        plt.rcParams["axes.grid"] = False
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=plotstyle.figsize(profile, 2, 0.48),
                                       gridspec_kw={"height_ratios": [1, 1.3]})
        for ax in (ax1, ax2):
            ax.add_collection(PolyCollection(bpolys, fc="#1f77b4", ec="#1f77b4", lw=0.3))
        bb = bdc.dbbox()
        ax1.set_xlim(bb.left, bb.right)
        ax1.set_ylim(-3.2, 3.2)
        ax1.set_aspect(2.5)
        ax1.axvspan(7.7, 10.2, color="#ff7f0e", alpha=0.18, lw=0)
        ax1.set_ylabel("y (µm)")
        ax1.set_xlabel("x (µm)")
        ax1.set_title("(a) full coupler, vertical scale ×2.5", loc="left", fontsize=P["font"])

        ax2.set_xlim(5.5, 12.5)
        ax2.set_ylim(-1.25, 1.25)
        ax2.set_aspect("equal")
        ax2.set_xlabel("x (µm)")
        ax2.set_ylabel("y (µm)")
        ax2.set_title("(b) phase-control section, true scale", loc="left", fontsize=P["font"])
        def width_dim(x, y0, y1, above):
            """Double arrow across a waveguide, label outside it."""
            ax2.annotate("", (x, y0), (x, y1),
                         arrowprops=dict(arrowstyle="<|-|>", color="white", lw=0.9,
                                         mutation_scale=7, shrinkA=0, shrinkB=0))
            ax2.text(x, y1 + 0.12 if above else y0 - 0.12, f"{(y1 - y0) * 1e3:.0f} nm",
                     ha="center", va="bottom" if above else "top", fontsize=P["small"])

        width_dim(6.4, b0, b1, True)          # upper guide, coupling section
        width_dim(6.4, a0, a1, False)         # lower guide, coupling section
        width_dim(8.95, d0, d1, True)         # upper guide, phase section
        width_dim(8.95, c0, c1, False)        # lower guide, phase section
        xg = 11.3                             # gap, between the two guides
        ax2.annotate("", (xg, a1), (xg, b0),
                     arrowprops=dict(arrowstyle="<|-|>", color="k", lw=0.8,
                                     mutation_scale=6, shrinkA=0, shrinkB=0))
        ax2.annotate(f"gap {(b0 - a1) * 1e3:.0f} nm", (xg + 0.05, (a1 + b0) / 2),
                     (11.55, b1 + 0.25), ha="center", va="bottom", fontsize=P["small"],
                     arrowprops=dict(arrowstyle="-", color="k", lw=0.6, shrinkA=1, shrinkB=1))
        for ax in (ax1, ax2):
            ax.tick_params(direction="in", top=True, right=True)
        fig.tight_layout()
        return fig

    plotstyle.build(plot_bdc, "fig02_bdc_layout")


if __name__ == "__main__":
    main()
