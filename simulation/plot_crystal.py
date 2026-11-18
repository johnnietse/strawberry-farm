#!/usr/bin/env python3
"""Results of crystal_lfxo.cir (LTspice), exported to SQLite with the LTspice MCP
export_raw_waveforms (signal V(xl1), cartesian).

    python plot_crystal.py crystal_lfxo.db

For every step it finds the oscillation point of the broken Pierce loop (V(xl1)/i real and
negative), prints the frequency error and the minimum amplifier transconductance, checks the
result against the closed-form load-resonance formula, and writes plots/crystal_lfxo.png.
"""
import math
import os
import sqlite3
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
F0, C0, CPIN, CEXT, CLSPEC, R1 = 32768.0, 1.2e-12, 4e-12, 12e-12, 9e-12, 70e3
SURFACE, INK, INK2, GRID = "#fcfcfb", "#1f1f1e", "#5f5e58", "#e6e5e0"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "semibold",
    "axes.titlecolor": INK, "axes.titlelocation": "left", "lines.linewidth": 2, "legend.frameon": False,
})


def analytic_fosc(c1m, cpcb):
    """Load resonance: f = fs (1 + C1 / (2 (C0 + CL))), CL = series of the two sides."""
    fs = F0 / (1 + c1m / (2 * (C0 + CLSPEC)))
    cl = (CEXT + CPIN + cpcb) / 2
    return fs * (1 + c1m / (2 * (C0 + cl)))


def main():
    db = sqlite3.connect(sys.argv[1])
    params = {}
    for step, name, value in db.execute("SELECT step, name, value FROM step_params"):
        params.setdefault(step, {})[name] = value
    results = []
    curves = {}
    for step in sorted(params):
        rows = db.execute('SELECT frequency, "V(xl1)|real", "V(xl1)|imag" FROM samples '
                          "WHERE step = ? ORDER BY point", (step,)).fetchall()
        # oscillation point: Im crosses zero where Re < 0 (|Zt| peaks there)
        best = None
        for (f1, r1, i1), (f2, r2, i2) in zip(rows, rows[1:]):
            if i1 == 0 or (i1 < 0) != (i2 < 0):
                if r1 < 0 and (best is None or abs(r1) > abs(best[1])):
                    t = i1 / (i1 - i2) if i1 != i2 else 0.0
                    best = (f1 + t * (f2 - f1), r1 + t * (r2 - r1))
        c1m, cpcb = params[step]["c1m"], params[step]["cpcb"]
        fosc, zt = best
        results.append({"c1m": c1m, "cpcb": cpcb, "fosc": fosc, "ppm": (fosc / F0 - 1) * 1e6,
                        "gm_uA_per_V": 1e6 / abs(zt), "ppm_formula": (analytic_fosc(c1m, cpcb) / F0 - 1) * 1e6})
        curves[step] = rows
    print(f"{'C1 (fF)':>8} {'stray (pF)':>10} {'CL (pF)':>8} {'f (Hz)':>12} {'error ppm':>10} "
          f"{'formula ppm':>12} {'gm min uA/V':>12}")
    for r in results:
        print(f"{r['c1m']*1e15:8.1f} {r['cpcb']*1e12:10.0f} {(CEXT+CPIN+r['cpcb'])/2*1e12:8.1f} "
              f"{r['fosc']:12.4f} {r['ppm']:10.2f} {r['ppm_formula']:12.2f} {r['gm_uA_per_V']:12.3f}")

    fig, (a, b, c) = plt.subplots(1, 3, figsize=(14, 4.2), constrained_layout=True)
    for c1m, color, label in ((2.3e-15, S1, "C1 2.3 fF (Q 30 000)"), (6.9e-15, S2, "C1 6.9 fF (Q 10 000)")):
        pts = sorted((r["cpcb"] * 1e12, r["ppm"]) for r in results if abs(r["c1m"] - c1m) < 1e-17)
        a.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=color, ms=6, mec=SURFACE, label=label)
    a.axhspan(-20, 20, color=S3, alpha=0.12, lw=0)
    a.text(0.05, 17, "crystal's own tolerance at 25 C, +/-20 ppm", color=INK2, fontsize=8.5)
    a.axvline(2, color=INK2, lw=0.8, ls=(0, (4, 2)))
    a.text(2.08, 30, "design value 2 pF", color=INK2, fontsize=8.5)
    a.set_xlabel("board stray capacitance per side, pF")
    a.set_ylabel("frequency error, ppm")
    a.set_title("Oscillation frequency vs board stray (LTspice)")
    a.legend(loc="lower left", bbox_to_anchor=(0, 0.02))

    nominal = next(s for s in params if abs(params[s]["c1m"] - 2.3e-15) < 1e-17 and abs(params[s]["cpcb"] - 2e-12) < 1e-13)
    rows = curves[nominal]
    f = [x[0] for x in rows]
    mag = [math.hypot(x[1], x[2]) / 1e6 for x in rows]
    b.plot([(x - F0) for x in f], mag, color=S1)
    r_nom = next(r for r in results if abs(r["c1m"] - 2.3e-15) < 1e-17 and abs(r["cpcb"] - 2e-12) < 1e-13)
    b.axvline(r_nom["fosc"] - F0, color=INK2, lw=0.8, ls=(0, (4, 2)))
    b.annotate(f"oscillates at {r_nom['fosc']:.3f} Hz\n({r_nom['ppm']:+.1f} ppm), needs gm >= {r_nom['gm_uA_per_V']:.2f} uA/V",
               (r_nom["fosc"] - F0, max(mag)), xytext=(8, -30), textcoords="offset points", color=INK, fontsize=8.5)
    b.set_xlim(-3, 3)
    b.set_xlabel("frequency - 32 768 Hz, Hz")
    b.set_ylabel("|Zt| = |V(XL1) / i|, MOhm")
    b.set_title("Loop transimpedance, 2 pF stray, C1 2.3 fF")

    # drive level: crystal current ~ 2 pi f Cside V(XL2); P = I_rms^2 R1 (worst-case R1)
    cside = CEXT + CPIN + 2e-12
    vpp = [0.1 + 0.01 * i for i in range(191)]
    p_uw = [((2 * math.pi * F0 * cside * v / (2 * math.sqrt(2))) ** 2 * R1) * 1e6 for v in vpp]
    c.plot(vpp, p_uw, color=S1, label="drive level in the crystal")
    c.axhline(0.5, color=S2, lw=1.5, ls=(0, (4, 2)), label="limit, ABS07 and nRF52840: 0.5 uW")
    c.set_xlabel("oscillation amplitude at XL2, V peak to peak")
    c.set_ylabel("power, uW")
    c.set_title("Crystal drive level (ESR 70 kOhm, worst case)")
    c.legend(loc="upper left")
    os.makedirs(os.path.join(HERE, "plots"), exist_ok=True)
    fig.savefig(os.path.join(HERE, "plots", "crystal_lfxo.png"), dpi=150)
    vmax = 2 * math.sqrt(2) * math.sqrt(0.5e-6 / R1) / (2 * math.pi * F0 * cside)
    print(f"drive level reaches 0.5 uW at {vmax:.2f} Vpp at XL2 (worst-case ESR)")


if __name__ == "__main__":
    main()
