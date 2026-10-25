"""Measured transmission of the fabricated 1x4 cascaded-MZI demultiplexer.

Loads the raw .mat files from the swept-laser setup (testResult.header.wavelength,
testResult.rows.channel_1..4 in dBm), normalizes each output to the on-chip
reference waveguide, restricts the analysis to the band where the reference is
well above the noise floor, extracts passband metrics and saves the figure.
Run from the repository root:  python analysis/meas_demux.py
"""
from pathlib import Path
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

import plotstyle
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "measurement" / "raw"
OUT = ROOT / "measurement"

# (file, detector channel) for each recorded demux output.
# Detector channels without signal in a file are not listed.
TRACES = {
    "A": ("demux_3outputs_2025-11-17_025511.mat", "channel_1"),
    "B": ("demux_3outputs_2025-11-17_025511.mat", "channel_2"),
    "C": ("demux_3outputs_2025-11-17_025511.mat", "channel_4"),
    "D": ("demux_1output_2025-11-16_231348.mat", "channel_4"),   # duplicate demux, 4th output
}
REFERENCE = ("ref_waveguide_2025-11-17_013227.mat", "channel_2")
SNR_MARGIN_DB = 10.0      # reference must exceed the noise floor by this much
SMOOTH_NM = 0.2           # smoothing used only for metric extraction
# Output / channel of each trace, under the -3.5 nm offset hypothesis (README, Section VIII).
# Colors and output numbers match the simulation figure (sim_interconnect.py).
OUTPUT = {"A": (2, 1559), "B": (1, 1555), "C": (3, 1557), "D": (4, 1553)}
COLOR = {"A": "#ff7f0e", "B": "#1f77b4", "C": "#2ca02c", "D": "#d62728"}
PLOT_ORDER = ("D", "B", "C", "A")          # same legend order as the simulation
CHANNEL_NO = {1553: 1, 1555: 2, 1557: 3, 1559: 4}


def load(fname, channel):
    m = sio.loadmat(RAW / fname, squeeze_me=True, struct_as_record=False)["testResult"]
    return np.asarray(m.header.wavelength, float), np.asarray(getattr(m.rows, channel), float)


def valid_band(wl, ref):
    floor = np.median(ref[(wl < wl.min() + 10) | (wl > wl.max() - 10)])
    ok = uniform_filter1d(ref, 50) > floor + SNR_MARGIN_DB
    idx = np.flatnonzero(ok)
    return wl[idx[0]], wl[idx[-1]]


def passband_metrics(x, t_db, step_nm):
    """Main passbands: peak wavelength, normalized level, 3-dB bandwidth, ER."""
    t = uniform_filter1d(t_db, max(1, int(SMOOTH_NM / step_nm)))
    peaks, _ = find_peaks(t, prominence=8, distance=int(5 / step_nm))
    rows = []
    for i in peaks:
        pk, lo, hi = t[i], i, i
        while lo > 0 and t[lo] > pk - 3:
            lo -= 1
        while hi < len(t) - 1 and t[hi] > pk - 3:
            hi += 1
        if lo == 0 or hi == len(t) - 1:
            continue                       # passband cut by the band edge
        win = (x > x[i] - 4) & (x < x[i] + 4)
        rows.append((x[i], pk, x[hi] - x[lo], pk - t[win].min()))
    return np.array(rows)


def main():
    wl, ref = load(*REFERENCE)
    lo, hi = valid_band(wl, ref)
    band = (wl >= lo) & (wl <= hi)
    step = np.diff(wl).mean()
    print(f"sweep {wl.min():.1f}-{wl.max():.1f} nm, step {step*1e3:.0f} pm, "
          f"valid band {lo:.1f}-{hi:.1f} nm")

    norm, table = {}, []
    for name, (f, ch) in TRACES.items():
        w, p = load(f, ch)
        if not np.allclose(w, wl):
            raise ValueError(f"{f}: wavelength grid differs from reference")
        norm[name] = p - ref
        m = passband_metrics(wl[band], norm[name][band], step)
        fsr = np.median(np.diff(m[:, 0]))  # median: robust to a missed passband
        print(f"\nTrace {name} ({f}, {ch})  FSR {fsr:.2f} nm")
        for pk_nm, lvl, bw, er in m:
            print(f"   peak {pk_nm:.2f} nm  {lvl:+.2f} dB  BW3dB {bw:.2f} nm  ER {er:.1f} dB")
            table.append((name, pk_nm, lvl, bw, er))

    np.savetxt(OUT / "demux_normalized.csv",
               np.column_stack([wl[band]] + [norm[k][band] for k in TRACES]),
               delimiter=",", fmt="%.4f", comments="",
               header="wavelength_nm," + ",".join(f"trace_{k}_db" for k in TRACES))
    with open(OUT / "demux_passbands.csv", "w") as fh:
        fh.write("trace,peak_nm,level_db,bw3db_nm,er_db\n")
        for r in table:
            fh.write(f"{r[0]},{r[1]:.3f},{r[2]:.2f},{r[3]:.3f},{r[4]:.1f}\n")

    # Annotated channel window: for each output, the passband closest to its target
    # (shifted by the -3.5 nm offset hypothesis), its extinction and the channel spacings.
    OFFSET = -3.5
    smooth = {k: uniform_filter1d(norm[k], max(1, int(SMOOTH_NM / step))) for k in TRACES}
    ann = {}
    for k in TRACES:
        out, lam = OUTPUT[k]
        rows = [r for r in table if r[0] == k and 1547 <= r[1] <= hi]   # inside the channel window
        pk = min(rows, key=lambda r: abs(r[1] - (lam + OFFSET)))
        i = np.abs(wl - pk[1]).argmin()
        win = np.flatnonzero(np.abs(wl - pk[1]) < 4)
        j = win[np.argmin(smooth[k][win])]
        ann[k] = dict(peak=pk[1], level=smooth[k][i], er=pk[4], null_x=wl[j],
                      null_y=smooth[k][j])
        print(f"Output {out}: peak {pk[1]:.2f} nm, ER {pk[4]:.1f} dB")

    def plot(profile):
        P = plotstyle.use(profile, 2)
        fig, (ax0, ax1) = plt.subplots(2, 1, figsize=plotstyle.figsize(profile, 2, 0.78),
                                       gridspec_kw={"height_ratios": [1, 1.6]})
        for ax, (x0, x1) in ((ax0, (lo, hi)), (ax1, (1547, hi))):
            for k in PLOT_ORDER:
                out, lam = OUTPUT[k]
                ax.plot(wl[band], norm[k][band], color=COLOR[k], lw=0.75 * P["lw"],
                        label=f"Output {out} (Ch. {CHANNEL_NO[lam]}, {ann[k]['peak']:.2f} nm)")
            ax.set_xlim(x0, x1)
            ax.set_ylim(-40, 3)
            ax.set_ylabel("Transmission (dB)")
        ax1.set_xlabel("Wavelength (nm)")
        ax1.xaxis.set_major_locator(MultipleLocator(1))
        ax0.set_title("(a) analysis band", loc="left", fontsize=P["font"])
        ax1.set_title("(b) channel window", loc="left", fontsize=P["font"], pad=48)

        # peak labels above the axes, staggered so neighbouring boxes do not overlap
        order = sorted(ann, key=lambda k: ann[k]["peak"])
        for n, k in enumerate(order):
            a_ = ann[k]
            ax1.annotate(f"{a_['peak']:.2f} nm", (a_["peak"], a_["level"]),
                         (a_["peak"], 9 + 8 * (n % 2)), color=COLOR[k], ha="center",
                         fontsize=P["small"], fontweight="bold", annotation_clip=False,
                         bbox=dict(boxstyle="square,pad=0.25", fc="white", ec=COLOR[k], lw=1),
                         arrowprops=dict(arrowstyle="-|>", color=COLOR[k], lw=1))
            ax1.axvline(a_["peak"], color=COLOR[k], ls="--", lw=0.8, alpha=0.8)
            # extinction: vertical arrow from the peak level down to the null
            ax1.annotate("", (a_["null_x"], a_["null_y"]), (a_["null_x"], a_["level"]),
                         arrowprops=dict(arrowstyle="<|-|>", color=COLOR[k], lw=0.9,
                                         shrinkA=0, shrinkB=0))
            ax1.text(a_["null_x"], -38.5, f"≈ {a_['er']:.0f} dB", color=COLOR[k],
                     ha="center", va="bottom", fontsize=P["small"], fontweight="bold",
                     bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
        # channel spacing between the outputs recorded in the same scan
        same = sorted((k for k in ann if k != "D"), key=lambda k: ann[k]["peak"])
        for k1, k2 in zip(same[:-1], same[1:]):
            x1_, x2_ = ann[k1]["peak"], ann[k2]["peak"]
            ax1.annotate("", (x1_, -27), (x2_, -27),
                         arrowprops=dict(arrowstyle="<|-|>", color="0.25", lw=0.9,
                                         shrinkA=0, shrinkB=0))
            ax1.text((x1_ + x2_) / 2, -28.2, f"{x2_ - x1_:.2f} nm", ha="center", va="top",
                     fontsize=P["small"], color="0.25",
                     bbox=dict(fc="white", ec="none", pad=0.5))
        handles, labels = ax1.get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False,
                   bbox_to_anchor=(0.5, -0.01))
        fig.tight_layout(rect=(0, 0.09, 1, 1))
        return fig

    plotstyle.build(plot, "fig10_meas_transmission")


if __name__ == "__main__":
    main()
