"""Lumerical INTERCONNECT simulation of the 1x4 cascaded-MZI demultiplexer.

Reads the four raw ONA exports in simulation/raw/, writes a clean CSV,
extracts per-channel metrics and saves the simulated transmission figure.
Run from the repository root:  python analysis/sim_interconnect.py
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

import plotstyle

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "simulation" / "raw"
OUT_CSV = ROOT / "simulation" / "interconnect_demux_outputs.csv"

# Output port -> design channel (nm)
CHANNEL = {4: 1553, 1: 1555, 3: 1557, 2: 1559}
COLOR = {4: "#d62728", 1: "#1f77b4", 3: "#2ca02c", 2: "#ff7f0e"}


def load_ona(path):
    """Parse an INTERCONNECT text export (header lines, blank lines, CRLF tolerated)."""
    wl, y = [], []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        a, b = line.split(",")
        wl.append(float(a))
        y.append(float(b))
    wl, y = np.array(wl), np.array(y)
    order = np.argsort(wl)
    return wl[order], y[order]


def channel_metrics(wl, T, port, lam0):
    """Peak position, peak level, 3-dB bandwidth, normalized IL and isolation."""
    y = T[port]
    win = (wl > lam0 - 1.5) & (wl < lam0 + 1.5)
    i = np.flatnonzero(win)[y[win].argmax()]
    pk = y[i]
    lo = i
    while y[lo] > pk - 3:
        lo -= 1
    hi = i
    while y[hi] > pk - 3:
        hi += 1
    total = sum(10 ** (T[p] / 10) for p in T)  # sum of the 4 outputs (removes GC envelope)
    il_norm = -10 * np.log10(10 ** (pk / 10) / total[i])
    others = max(T[p][i] for p in T if p != port)
    return dict(port=port, design=lam0, peak_nm=wl[i], peak_db=pk,
                bw3db_nm=wl[hi] - wl[lo], il_norm_db=il_norm,
                isolation_db=pk - others)


def main():
    T, wl = {}, None
    for port in (1, 2, 3, 4):
        w, y = load_ona(RAW / f"interconnect_out{port}.txt")
        if wl is not None and not np.allclose(w, wl):
            raise ValueError("wavelength grids differ between outputs")
        wl, T[port] = w, y

    header = "wavelength_nm,out1_db,out2_db,out3_db,out4_db"
    np.savetxt(OUT_CSV, np.column_stack([wl] + [T[p] for p in (1, 2, 3, 4)]),
               delimiter=",", header=header, comments="", fmt="%.4f")

    print(f"{len(wl)} points, {wl.min():.2f}-{wl.max():.2f} nm, "
          f"mean step {np.diff(wl).mean() * 1e3:.1f} pm")
    rows = [channel_metrics(wl, T, p, lam) for p, lam in CHANNEL.items()]
    print("port  design  peak(nm)  shift  peak(dB)  BW3dB  IL_norm  isolation")
    for r in rows:
        print(f"Out{r['port']}  {r['design']}  {r['peak_nm']:.2f}  "
              f"{r['peak_nm'] - r['design']:+.2f}  {r['peak_db']:.2f}  "
              f"{r['bw3db_nm']:.2f}  {r['il_norm_db']:.2f}  {r['isolation_db']:.1f}")
    peaks = sorted(r["peak_nm"] for r in rows)
    print("channel spacing (nm):", np.round(np.diff(peaks), 2))

    # Figure: (a) full span, (b) zoom on the channel window
    def plot(profile):
        P = plotstyle.use(profile, 2)
        fig, axs = plt.subplots(1, 2, figsize=plotstyle.figsize(profile, 2, 0.36),
                                gridspec_kw={"width_ratios": [1.2, 1]})
        for ax, (lo, hi) in zip(axs, [(1500, 1600), (1549, 1563)]):
            for p in (4, 1, 3, 2):
                ax.plot(wl, T[p], color=COLOR[p], lw=P["lw"],
                        label=f"Output {p} ({CHANNEL[p]} nm)")
            for lam in CHANNEL.values():
                ax.axvline(lam, color="k", ls=":", lw=0.6)
            ax.set_xlim(lo, hi)
            ax.set_ylim(-70, 0)
            ax.set_xlabel("Wavelength (nm)")
        axs[0].set_ylabel("Transmission (dB)")
        axs[1].xaxis.set_major_locator(MultipleLocator(5))
        axs[1].legend(loc="lower right", framealpha=0.9)
        axs[0].set_title("(a)", loc="left", fontsize=P["font"])
        axs[1].set_title("(b)", loc="left", fontsize=P["font"])
        fig.tight_layout()
        return fig

    plotstyle.build(plot, "fig09_sim_transmission")


if __name__ == "__main__":
    main()
