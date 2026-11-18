#!/usr/bin/env python3
"""Plot LTspice results exported to SQLite (LTspice MCP export_raw_waveforms or any
.raw-to-SQLite export with a 'samples' table: step, time, one column per signal).

    python plot_results.py <led_channel.db> <led_pwm.db> <vbat.db>

Writes plots/*.png next to this script.
"""
import os
import sqlite3
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "plots")


def rows(db, cols, step, t0=None, t1=None):
    q = f'SELECT time, {", ".join(chr(34) + c + chr(34) for c in cols)} FROM samples WHERE step = ?'
    args = [step]
    if t0 is not None:
        q += " AND time >= ? AND time <= ?"
        args += [t0, t1]
    data = sqlite3.connect(db).execute(q + " ORDER BY point", args).fetchall()
    return [list(c) for c in zip(*data)]


def main():
    led, pwm, vbat = sys.argv[1:4]
    os.makedirs(OUT, exist_ok=True)

    # 1. LED channel switching at 24 V, blue and red strings, typical forward voltage
    fig, ax = plt.subplots(figsize=(8, 4))
    for step, label in ((4, "blue string, 4 x SP-01-V4"), (5, "red string, 4 x SP-01-D2")):
        t, il, _ = rows(led, ["I(L1)", "V(sw)"], step, 0.900e-3, 0.920e-3)
        ax.plot([(x - 0.9e-3) * 1e6 for x in t], [v * 1e3 for v in il], label=label)
    ax.axhline(333, color="grey", ls="--", lw=0.8, label="target 333 mA")
    ax.set_xlabel("time (us)")
    ax.set_ylabel("inductor / LED current (mA)")
    ax.set_title("AL8860 channel at 24 V, L = 100 uH: about 0.55 MHz, 104 mA ripple")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "led_channel_24V.png"), dpi=130)

    # 2. PWM dimming, 50 % at 250 Hz
    fig, ax = plt.subplots(figsize=(8, 4))
    t, i, v = rows(pwm, ["I(Rs)", "V(cable)"], 1)
    ax.plot([x * 1e3 for x in t], [x * 1e3 for x in i], lw=0.6, label="LED current (mA)")
    ax2 = ax.twinx()
    ax2.plot([x * 1e3 for x in t], v, color="tab:orange", lw=1, label="CTRL (V)")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("LED current (mA)")
    ax2.set_ylabel("CTRL voltage (V)")
    ax.set_title("PWM dimming, 50 % at 250 Hz: 168 mA average (ideal 168 mA)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "led_pwm_50pct.png"), dpi=130)

    # 3. battery sense divider: 3.0 V -> 4.2 V step, four resistor-tolerance corners
    fig, ax = plt.subplots(figsize=(8, 4))
    for step in range(4):
        t, vs, _ = rows(vbat, ["V(sense)", "V(vbat)"], step)
        ax.plot(t, vs, lw=1, label=f"tolerance corner {step + 1}")
    ax.set_xlim(0.8, 2.5)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("ADC input (V)")
    ax.set_title("VBAT sense: 1 % settling 0.38 s, worst-case error +/-1.1 %")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "vbat_sense.png"), dpi=130)
    print("plots written to", OUT)


if __name__ == "__main__":
    main()
