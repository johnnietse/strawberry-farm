#!/usr/bin/env python3
"""
LED driver rev 1.0 (333 mA) against rev 1.1 with JP1 / JP2 bridged (667 mA): inductor current
of one AL8860 channel at 24 V and, for rev 1.1, the LED current behind the 10 uF capacitor, blue and red strings with typical LEDs (steps 4 and 5 of
led_channel.cir and led_channel_667mA.cir), plus the measured table from both LTspice logs.

    # run both netlists in LTspice, export I(L1) of steps 4 and 5 with the LTspice MCP
    # export_raw_waveforms (first 30 us of the saved window; I(L1), and I(Dled) for rev 1.1) to
    # these two files, then:
    python plot_led_option.py led_channel_333mA_window.db led_channel_667mA.db \
        led_channel.log led_channel_667mA.log
"""
import os
import re
import sqlite3
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def wave(db, step, signal="I(L1)"):
    rows = sqlite3.connect(db).execute(
        f'SELECT time, "{signal}" FROM samples WHERE step = ? AND time <= 2e-5 ORDER BY point', [step]).fetchall()
    return [r[0] * 1e6 for r in rows], [r[1] * 1e3 for r in rows]


def measurements(log):
    text = open(log, encoding="latin-1").read()
    out = {}
    for m in re.finditer(r"Measurement: (\w+)\n.*?\n((?:\s+\d+\s+\S+.*\n)+)", text):
        out[m.group(1)] = [float(line.split()[1]) for line in m.group(2).strip().splitlines()]
    return out


def main(db333, db667, log333, log667):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, (step, colour) in zip(axes, ((4, "blue string, 4 x SP-01-V4"), (5, "red string, 4 x SP-01-D2"))):
        for db, label, c in ((db333, "rev 1.0, 333 mA: inductor = LED current", "#7f7f7f"),
                             (db667, "rev 1.1 bridged, 667 mA: inductor current", "#ff9896")):
            t, i = wave(db, step)
            ax.plot(t, i, lw=1.3, color=c, label=label)
        t, i = wave(db667, step, "I(Dled)")
        ax.plot(t, i, lw=2.2, color="#d62728", label="rev 1.1 bridged: LED current (10 uF across the string)")
        ax.axhline(333, color="#7f7f7f", ls=":", lw=1)
        ax.axhline(667, color="#d62728", ls=":", lw=1)
        ax.axhline(700, color="black", ls="--", lw=1)
        ax.text(19.8, 708, "deep red Rebel: 700 mA DC maximum", ha="right", fontsize=8)
        ax.axhline(920, color="#9467bd", ls="--", lw=1)
        ax.text(19.8, 928, "inductor rating 0.92 A", ha="right", fontsize=8, color="#9467bd")
        ax.set_title(f"AL8860 channel at 24 V, {colour}", fontsize=10)
        ax.set_xlabel("time (us)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("inductor / LED current (mA)")
    axes[0].set_ylim(200, 1000)
    axes[0].legend(loc="lower left", fontsize=8)
    a, b = measurements(log333), measurements(log667)

    def rng(m, k, scale=1.0, fmt="{:.0f}"):
        return f"{fmt.format(min(m[k]) * scale)} to {fmt.format(max(m[k]) * scale)}"
    fig.suptitle(f"LED current option: {rng(a, 'i_led_avg', 1e3)} mA -> {rng(b, 'i_led_avg', 1e3)} mA, "
                 f"switching {rng(a, 'f_sw', 1e-3)} kHz -> {rng(b, 'f_sw', 1e-3)} kHz "
                 "(12 corners: 20 / 24 / 28 V, typical and maximum LED voltage)", fontsize=10)
    fig.tight_layout()
    os.makedirs(os.path.join(HERE, "plots"), exist_ok=True)
    fig.savefig(os.path.join(HERE, "plots", "led_current_option.png"), dpi=120)
    for name, m in (("333 mA", a), ("667 mA", b)):
        print(name, {k: (round(min(v), 4), round(max(v), 4)) for k, v in m.items()
                     if k in ("i_led_avg", "i_l_max", "f_sw", "t_on", "duty", "efficiency", "p_switch", "p_rsense")})


if __name__ == "__main__":
    main(*sys.argv[1:5])
