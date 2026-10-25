"""FSR extraction for a stand-alone MZI test structure.

Reads a swept-laser .mat file (testResult.header.wavelength, testResult.rows.channel_N
in dBm), removes the grating-coupler envelope, estimates the fringe period by
autocorrelation, locates the interference minima and reports the free spectral
range (FSR) measured between successive minima.

Example (from the repository root):
    python analysis/mzi_fit.py measurement/raw/mzi_stage1_dL143_2025-11-17_025351.mat \
        --name fig06_mzi_stage1
"""
import argparse
from pathlib import Path

import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks, correlate

import plotstyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "measurement"


def load_mat(path, channel):
    m = sio.loadmat(path, squeeze_me=True, struct_as_record=False)["testResult"]
    wl = np.asarray(m.header.wavelength, float)
    if wl.max() < 10:                      # file stored in metres
        wl = wl * 1e9
    return wl, np.asarray(getattr(m.rows, channel), float)


def period_guess(wl, y):
    """Fringe period from the first autocorrelation maximum (mean removed)."""
    step = np.median(np.diff(wl))
    b = uniform_filter1d(y, max(1, int(0.05 / step)))
    b = b - b.mean()
    r = correlate(b, b, mode="full")[len(b) - 1:]
    r = r / r[0]
    peaks, _ = find_peaks(r, prominence=0.2)
    if len(peaks) == 0:
        raise ValueError("no periodic fringes found")
    return peaks[0] * step


def envelope_db(wl, y, period_nm, order=3):
    """Upper envelope: polynomial through the interference maxima."""
    step = np.median(np.diff(wl))
    ys = uniform_filter1d(y, max(1, int(0.1 / step)))
    idx, _ = find_peaks(ys, distance=max(1, int(0.6 * period_nm / step)), prominence=3)
    x = (wl - wl.mean()) / np.ptp(wl)
    return np.polyval(np.polyfit(x[idx], ys[idx], order), x)


def find_minima(wl, y, period_nm, prominence_db=6.0):
    step = np.median(np.diff(wl))
    ys = uniform_filter1d(y, max(1, int(0.05 / step)))
    idx, _ = find_peaks(-ys, prominence=prominence_db,
                        distance=max(1, int(0.6 * period_nm / step)))
    out = []
    for i in idx:                          # parabolic refinement of each minimum
        if 2 <= i < len(ys) - 2:
            a, b, _ = np.polyfit(wl[i - 2:i + 3], ys[i - 2:i + 3], 2)
            out.append(-b / (2 * a) if a > 0 else wl[i])
    return np.array(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("matfile", type=Path)
    ap.add_argument("--channels", nargs="+", default=["channel_1", "channel_2"])
    ap.add_argument("--window", nargs=2, type=float, default=[1505, 1559],
                    metavar=("MIN_NM", "MAX_NM"))
    ap.add_argument("--ref", nargs=2, metavar=("REF_MAT", "CHANNEL"),
                    help="normalize to a reference waveguide instead of the envelope")
    ap.add_argument("--name", default=None, help="output file stem")
    a = ap.parse_args()
    name = a.name or a.matfile.stem

    traces, results = {}, {}
    for ch in a.channels:
        wl, p = load_mat(a.matfile, ch)
        win = (wl >= a.window[0]) & (wl <= a.window[1])
        wl_w = wl[win]
        period = period_guess(wl_w, p[win])
        if a.ref:
            wr, r = load_mat(Path(a.ref[0]), a.ref[1])
            if not np.allclose(wr, wl):
                raise ValueError("reference wavelength grid differs")
            t_w = (p - r)[win]
        else:                              # envelope fitted inside the window only
            t_w = p[win] - envelope_db(wl_w, p[win], period)
        mins = find_minima(wl_w, t_w, period)
        fsr = np.diff(mins)
        # reject missed or split fringes: more than 3 MAD from the median FSR
        med = np.median(fsr)
        mad = 1.4826 * np.median(np.abs(fsr - med))
        keep = np.abs(fsr - med) < 3 * max(mad, 1e-3)
        f = fsr[keep]
        results[ch] = dict(fsr_mean=f.mean(), fsr_std=f.std(ddof=1),
                           n_minima=len(mins), n_used=len(f))
        traces[ch] = (wl_w, t_w, mins)
        print(f"{ch}: {len(mins)} minima ({len(f)} FSR kept), "
              f"FSR = {f.mean():.3f} +/- {f.std(ddof=1):.3f} nm")

    OUT.mkdir(exist_ok=True)
    wl_out = next(iter(traces.values()))[0]
    np.savetxt(OUT / f"{name}_normalized.csv",
               np.column_stack([wl_out] + [traces[c][1] for c in a.channels]),
               delimiter=",", fmt="%.4f", comments="",
               header="wavelength_nm," + ",".join(f"{c}_db" for c in a.channels))
    with open(OUT / f"{name}_metrics.csv", "w") as fh:
        fh.write("channel,fsr_mean_nm,fsr_std_nm,n_minima,n_fsr_used\n")
        for c, r in results.items():
            fh.write(f"{c},{r['fsr_mean']:.4f},{r['fsr_std']:.4f},"
                     f"{r['n_minima']},{r['n_used']}\n")

    # Figure: spectrum with one FSR marked between two minima near the band centre
    fsr_all = np.mean([r["fsr_mean"] for r in results.values()])
    mins = traces[a.channels[0]][2]
    j = int(np.argmin(np.abs(mins[:-1] - np.mean(a.window))))
    x0, x1 = mins[j], mins[j + 1]

    def plot(profile):
        P = plotstyle.use(profile, 1)
        fig, ax = plt.subplots(figsize=plotstyle.figsize(profile, 1, 0.68))
        for i, c in enumerate(a.channels):
            w, t, _ = traces[c]
            ax.plot(w, t, color=f"C{i}", lw=0.85 * P["lw"],
                    label=c.replace("channel_", "Port "))
        ytop = ax.get_ylim()[0] * 0.08
        ax.annotate("", (x0, ytop), (x1, ytop),
                    arrowprops=dict(arrowstyle="<|-|>", lw=0.8, color="k",
                                    shrinkA=0, shrinkB=0))
        for x in (x0, x1):
            ax.axvline(x, color="k", ls=":", lw=0.6)
        ax.text((x0 + x1) / 2, ytop * 1.6, f"FSR = {fsr_all:.2f} nm", ha="center",
                va="top", fontsize=P["small"] + 1, bbox=dict(fc="white", ec="none", pad=1))
        ax.set(xlabel="Wavelength (nm)", ylabel="Normalized transmission (dB)",
               xlim=a.window)
        ax.legend(loc="lower right", framealpha=0.9)
        fig.tight_layout()
        return fig

    plotstyle.build(plot, name)


if __name__ == "__main__":
    main()
