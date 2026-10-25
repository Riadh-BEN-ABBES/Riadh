"""Broadband directional coupler (ebeam_bdc_te1550) test structure.

Raw through/cross powers are compared with the reference waveguide. The apparent
splitting ratio P1/(P1+P2) is computed in the band where the reference is well
above the noise floor. Each port has its own output grating coupler, so this
ratio also contains the mismatch between the two grating-coupler responses: the
script reports the envelope centre of each port so that this bias can be judged.
Run from the repository root:  python analysis/bdc_analysis.py
"""
from pathlib import Path
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d

import plotstyle

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "measurement" / "raw"
OUT = ROOT / "measurement"

BDC = ("bdc_2025-11-17_025107.mat", "channel_1", "channel_2")
REF = ("ref_waveguide_2025-11-17_013227.mat", "channel_2")
SNR_MARGIN_DB = 10.0
SMOOTH_NM = 1.0          # removes the residual Fabry-Perot ripple


def load(fname):
    m = sio.loadmat(RAW / fname, squeeze_me=True, struct_as_record=False)["testResult"]
    return np.asarray(m.header.wavelength, float), m.rows


def envelope_centre(wl, y_db, n):
    s = uniform_filter1d(y_db, n)
    i = s.argmax()
    lo, hi = i, i
    while s[lo] > s[i] - 3:
        lo -= 1
    while s[hi] > s[i] - 3:
        hi += 1
    return wl[i], s[i], wl[hi] - wl[lo]


def main():
    wl, rows = load(BDC[0])
    p1 = np.asarray(getattr(rows, BDC[1]), float)
    p2 = np.asarray(getattr(rows, BDC[2]), float)
    wr, rrows = load(REF[0])
    ref = np.asarray(getattr(rrows, REF[1]), float)
    if not np.allclose(wr, wl):
        raise ValueError("reference wavelength grid differs")

    step = np.diff(wl).mean()
    n = max(1, int(SMOOTH_NM / step))
    floor = np.median(ref[(wl < wl.min() + 10) | (wl > wl.max() - 10)])
    ok = np.flatnonzero(uniform_filter1d(ref, 50) > floor + SNR_MARGIN_DB)
    band = (wl >= wl[ok[0]]) & (wl <= wl[ok[-1]])

    lin = lambda d: 10 ** (d / 10)
    sr = uniform_filter1d(lin(p1) / (lin(p1) + lin(p2)), n) * 100
    excess = uniform_filter1d(10 * np.log10(lin(p1) + lin(p2)) - ref, n)

    print(f"valid band {wl[band].min():.1f}-{wl[band].max():.1f} nm")
    for name, y in (("port 1", p1), ("port 2", p2), ("reference", ref)):
        c, pk, bw = envelope_centre(wl, y, n)
        print(f"{name:9s}: envelope peak {pk:.2f} dBm at {c:.1f} nm, 3-dB width {bw:.1f} nm")
    for lam in (1510, 1530, 1550):
        i = np.abs(wl - lam).argmin()
        print(f"{lam} nm: port 1 / port 2 = {sr[i]:.1f} / {100 - sr[i]:.1f} %, "
              f"(P1+P2) - Pref = {excess[i]:+.2f} dB")

    np.savetxt(OUT / "bdc_ratio.csv",
               np.column_stack([wl[band], p1[band], p2[band], ref[band], sr[band], excess[band]]),
               delimiter=",", fmt="%.4f", comments="",
               header="wavelength_nm,port1_dbm,port2_dbm,ref_dbm,ratio_port1_pct,sum_minus_ref_db")

    def plot(profile):
        # single panel, shown next to the BDC geometry (fig02_bdc_layout) in the README
        P = plotstyle.use(profile, 2)
        w, _ = plotstyle.figsize(profile, 2)
        fig, ax = plt.subplots(figsize=(0.62 * w, 0.46 * w))
        ax.plot(wl[band], sr[band], color="C0", label="Port 1")
        ax.plot(wl[band], 100 - sr[band], color="C1", label="Port 2")
        ax.axhline(50, color="k", ls=":", lw=0.6)
        ax.set(xlabel="Wavelength (nm)", ylabel="Apparent splitting ratio (%)",
               xlim=(wl[band].min(), wl[band].max()), ylim=(25, 75))
        ax.legend(loc="upper right", framealpha=0.9)
        ax.set_title("(c) measured splitting ratio", loc="left", fontsize=P["font"])
        fig.tight_layout()
        return fig

    plotstyle.build(plot, "fig02c_bdc_splitting_ratio")


if __name__ == "__main__":
    main()
