#!/usr/bin/env python3
"""
How much the charger warms the SHT40: sensor node rev 3.1 (no slots, copper everywhere) against
rev 3.2 (SHT40 on a tongue cut free by two edge notches and a slot, no pour, no planes, no
vias on it, reached by four 0.127 mm tracks over a 2.2 mm FR-4 bridge).

A steady-state 2-D finite-difference model of the 40 x 65 mm board, 0.25 mm cells. Each cell
conducts in the board plane with a sheet conductance (k x thickness, W/K) made of:
  - FR-4, 1.6 mm, k = 0.3 W/m K                                  0.48 mW/K
  - inner GND planes In1 / In2, 2 x 15.2 um copper, full         11.7 mW/K
  - outer layers F.Cu / B.Cu, 2 x 35 um copper, 60 % covered     16.2 mW/K
On the rev 3.2 tongue and bridge only FR-4 remains, plus the four 0.127 mm tracks (35 um) laid
along their routes. Slot cells conduct nothing. Both faces lose heat to the enclosure air by
natural convection, h = 10 W/m2 K each side; the board edges are taken as insulated.

Heat sources: the BQ24074 charging a cell at 494 mA (R_ISET 1.8k) dissipates
(V_BUS - V_BAT) x I = (5.0 - 3.7) V x 0.494 A = 0.64 W at U1 (18, 42), spread over its
3.5 x 3.5 mm package. Everything else is small and left out (the light node's radio is about
20 mW). Board coordinates as in pcbs/gos_sensor_node/generate_pcb.py (mm, origin top left).

This is an estimate, not a measurement: the coefficients (copper coverage, h) are typical
values, so read the result as a comparison of the two boards, then measure on the bench
(bring_up.md: SHT40 reading while charging against an external reference).

    python thermal_sht40.py        # writes plots/thermal_sht40.png and prints the rise at U5
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.sparse import lil_matrix  # noqa: E402
from scipy.sparse.linalg import spsolve  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, D = 40.0, 65.0, 0.25            # board mm, cell mm
NX, NY = int(W / D), int(H / D)

FR4 = 0.3 * 1.6e-3                    # W/K per square
PLANES = 2 * 385 * 15.2e-6
OUTER = 2 * 385 * 35e-6 * 0.60
TRACK = 385 * 35e-6 * 0.127 / D       # one 0.127 mm track along a row of cells, as a sheet value
H_CONV = 10.0                         # W/m2 K, each face
P_CHARGER = (5.0 - 3.7) * 0.494       # W
U1, U5 = (18.0, 42.0), (3.0, 26.0)

# rev 3.2 geometry (generate_pcb.py CONFIG)
SLOTS = [(0.0, 21.6, 7.8, 22.6), (0.0, 29.0, 7.8, 30.0), (6.8, 21.6, 7.8, 26.8)]   # notches + slot
ISLAND = (0.0, 22.6, 7.8, 29.0)
TRACKS = [  # hand-laid tongue tracks, (x, y) polylines (generate_pcb.py "preroute_tongue")
    [(2.6, 25.12), (2.6, 24.1)], [(2.225, 23.7), (1.4, 24.5), (1.4, 28.35), (8.6, 28.35), (9.0, 29.25)],
    [(3.4, 25.12), (3.4, 24.0)], [(3.775, 23.7), (5.9, 23.7), (5.9, 27.45), (8.6, 27.45), (9.0, 26.55)],
    [(3.4, 26.88), (3.4, 27.75), (9.6, 27.75), (10.2, 27.6)],
    [(2.6, 26.88), (2.6, 28.05), (9.6, 28.05), (10.2, 28.6)],
]


def cells(rect):
    x1, y1, x2, y2 = rect
    xs = np.arange(NX) * D + D / 2
    ys = np.arange(NY) * D + D / 2
    return np.outer((ys >= y1) & (ys <= y2), (xs >= x1) & (xs <= x2))


def model(rev32: bool):
    g = np.full((NY, NX), FR4 + PLANES + OUTER)
    solid = np.ones((NY, NX), bool)
    if rev32:
        g[cells(ISLAND)] = FR4
        for pts in TRACKS:
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                n = int(max(abs(xb - xa), abs(yb - ya)) / (D / 2)) + 1
                for t in np.linspace(0, 1, n):
                    i, j = int((ya + t * (yb - ya)) / D), int((xa + t * (xb - xa)) / D)
                    g[i, j] = max(g[i, j], FR4 + TRACK)
        for s in SLOTS:
            solid &= ~cells(s)
    return g, solid


def solve(g, solid):
    idx = -np.ones((NY, NX), int)
    idx[solid] = np.arange(solid.sum())
    A = lil_matrix((solid.sum(),) * 2)
    b = np.zeros(solid.sum())
    conv = 2 * H_CONV * (D * 1e-3) ** 2                 # W/K to the air, both faces
    src = cells((U1[0] - 1.75, U1[1] - 1.75, U1[0] + 1.75, U1[1] + 1.75)) & solid
    for i, j in zip(*np.nonzero(solid)):
        k = idx[i, j]
        A[k, k] += conv
        if src[i, j]:
            b[k] += P_CHARGER / src.sum()
        for di, dj in ((1, 0), (0, 1)):
            ii, jj = i + di, j + dj
            if ii < NY and jj < NX and solid[ii, jj]:
                # series sheet conductance between two cell centres (square cells: G = g)
                gij = 2 * g[i, j] * g[ii, jj] / (g[i, j] + g[ii, jj])
                kk = idx[ii, jj]
                A[k, k] += gij
                A[kk, kk] += gij
                A[k, kk] -= gij
                A[kk, k] -= gij
    t = spsolve(A.tocsr(), b)
    out = np.full((NY, NX), np.nan)
    out[solid] = t
    return out


def at(t, p):
    return t[int(p[1] / D), int(p[0] / D)]


def main():
    res = {}
    for name, rev32 in (("rev 3.1", False), ("rev 3.2", True)):
        res[name] = solve(*model(rev32))
        print(f"{name}: SHT40 (U5) {at(res[name], U5):.2f} K above the air, charger (U1) "
              f"{at(res[name], U1):.1f} K, board mean {np.nanmean(res[name]):.2f} K")
    a, b = at(res["rev 3.1"], U5), at(res["rev 3.2"], U5)
    print(f"SHT40 error from charging: {a:.2f} K -> {b:.2f} K ({100 * (1 - b / a):.0f} % less)")

    vmax = max(np.nanmax(t) for t in res.values())
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.6), gridspec_kw={"width_ratios": [1, 1, 1.25]})
    for ax, (name, t) in zip(axes[:2], res.items()):
        im = ax.imshow(t, extent=[0, W, H, 0], cmap="inferno", vmin=0, vmax=vmax)
        ax.plot(*U5, "o", mfc="none", mec="#00e5ff", mew=2, ms=11)
        ax.annotate(f"SHT40\n+{at(t, U5):.2f} K", U5, (8, 14), color="#00e5ff", fontsize=10,
                    arrowprops=dict(arrowstyle="-", color="#00e5ff"))
        ax.annotate(f"charger\n+{at(t, U1):.1f} K", U1, (24, 55), color="white", fontsize=10,
                    arrowprops=dict(arrowstyle="-", color="white"))
        ax.set_title(name + (": tongue, notches, slot" if name == "rev 3.2" else ": no slots"), fontsize=10)
        ax.set_xlabel("x, mm")
        ax.set_ylabel("y, mm")
    fig.colorbar(im, ax=axes[:2], shrink=0.8, label="K above enclosure air")
    ax = axes[2]
    xs = np.arange(NX) * D + D / 2
    row = int(U5[1] / D)
    for name, t in res.items():
        ax.plot(xs, t[row], lw=2, label=name)
    ax.axvline(U5[0], color="grey", ls=":")
    ax.text(U5[0] + 0.4, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] else 1, "SHT40", fontsize=9)
    ax.axvspan(6.8, 7.8, color="grey", alpha=0.15)   # slot / bridge column
    ax.set_title("Rise along the row through the SHT40 (y = 26 mm)", fontsize=10)
    ax.set_xlabel("x, mm (bridge shaded)")
    ax.set_ylabel("K above enclosure air")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.suptitle(f"Board temperature rise while charging (0.64 W in the BQ24074). SHT40: {a:.2f} K (rev 3.1) "
                 f"vs {b:.2f} K (rev 3.2), 2-D estimate", fontsize=12)
    os.makedirs(os.path.join(HERE, "plots"), exist_ok=True)
    fig.savefig(os.path.join(HERE, "plots", "thermal_sht40.png"), dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()
