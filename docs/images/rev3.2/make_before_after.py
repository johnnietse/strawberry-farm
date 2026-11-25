#!/usr/bin/env python3
"""
Before/after figures for documentation/rev3.2_changes.md, from the KiCad 3D renders that
pcbs/*/route_pcb.py writes into each board's docs/ folder (old boards: pcbs/archive/).

    python docs/images/rev3.2/make_before_after.py      # run from the repository root
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))


def board(path):
    """The render cropped to the board (pixels that differ from the corner background)."""
    im = np.asarray(Image.open(path).convert("RGB"))
    mask = np.abs(im.astype(int) - im[5, 5].astype(int)).sum(2) > 30
    ys, xs = np.nonzero(mask)
    return im[ys.min():ys.max(), xs.min():xs.max()]


def sensor():
    pairs = [("sensor node rev 3.1", "pcbs/archive/gos_sensor_node_rev3.1/docs/gos_sensor_node_render_top.png"),
             ("sensor node rev 3.2", "pcbs/gos_sensor_node/docs/gos_sensor_node_render_top.png")]
    fig, axes = plt.subplots(1, 4, figsize=(16, 7.2), gridspec_kw={"width_ratios": [1, 1.1, 1, 1.1]})
    for k, (name, path) in enumerate(pairs):
        b = board(path)
        h, w = b.shape[:2]
        sx, sy = w / 40.0, h / 65.0                      # board is 40 x 65 mm
        ax = axes[2 * k]
        ax.imshow(b)
        ax.set_title(name, fontsize=11)
        ax.axis("off")
        x0, x1, y0, y1 = 0, 14, 18, 36                   # the SHT40 corner, mm
        ax.add_patch(plt.Rectangle((x0 * sx, y0 * sy), (x1 - x0) * sx, (y1 - y0) * sy, fill=False, ec="#00e5ff", lw=2))
        axes[2 * k + 1].imshow(b[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)])
        axes[2 * k + 1].axis("off")
        axes[2 * k + 1].set_title("SHT40 corner (x 0-14, y 18-36 mm)", fontsize=10)
    fig.text(0.5, 0.02, "Rev 3.1: the SHT40 (U5) sits in the ground pour on the board edge, its I2C pull-ups beside it. "
             "Rev 3.2: two notches and a slot cut it free on a tongue with no copper pour; four thin tracks cross "
             "the bridge; J6 (PAR sensor) and the pull-ups sit below.", ha="center", fontsize=9.5, wrap=True)
    plt.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(OUT, "sensor_node_before_after.png"), dpi=110)


def led():
    pairs = [("LED driver rev 1.0", "pcbs/archive/led_driver_rev1.0/docs/led_driver_render_top.png"),
             ("LED driver rev 1.1", "pcbs/led_driver/docs/led_driver_render_top.png")]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    for ax, (name, path) in zip(axes, pairs):
        ax.imshow(board(path))
        ax.set_title(name, fontsize=11)
        ax.axis("off")
    fig.text(0.5, 0.02, "Rev 1.1 adds, per channel, a second 0.30 ohm sense resistor (R5 blue, R6 red) behind a solder "
             "jumper (JP1, JP2; bridge it for 667 mA) and a 10 uF capacitor across the LED string (C6, C7) beside "
             "the inductor.", ha="center", fontsize=9.5)
    plt.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(OUT, "led_driver_before_after.png"), dpi=110)


if __name__ == "__main__":
    sensor()
    led()
