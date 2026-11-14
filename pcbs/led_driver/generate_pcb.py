#!/usr/bin/env python3
"""G.O.S. LED driver board rev 1.0 board generator (KiCad 9 pcbnew API).

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" generate_pcb.py
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" ..\\gos_sensor_node\\route_pcb.py .

Uses the sensor node's board builder (pcbs/gos_sensor_node/generate_pcb.py)
with this board's placement. 60 x 45 mm, four M3 holes, 2 layers.

Layout:
- J1 24 V jack on the left edge, plug entry facing out; F1, D1 and C1 beside it
- blue channel (U1) in the top half, red channel (U2) in the bottom half
- J3 / J4 LED terminals on the right edge, wire entry facing out
- J2 PWM header along the bottom edge
- each channel's input capacitor, freewheel diode and inductor packed around
  its AL8860 to keep the switching loop (VIN cap, SW, diode) small
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gos_sensor_node"))
import generate_pcb as gp  # noqa: E402

W, H = 60.0, 45.0
HOLE_INSET = 4.0

# (track width, clearance, via diameter, via drill), mm. Power nets carry the
# 0.35 A input and up to 0.4 A inductor peak; 0.4 mm on 1 oz copper carries
# well over 1 A and still reaches the AL8860's SET pin beside its GND pin
# (0.65 mm pitch). 0.15 mm clearance is ample for 24 V on outer layers.
NETCLASSES = {
    "Default": (0.25, 0.2, 0.8, 0.4),
    "Power": (0.4, 0.15, 0.8, 0.4),
}
POWER_NETS = ["GND", "/VIN*", "/SW_*", "/LEDK_*", "/SET_*"]  # root-sheet nets carry a "/" prefix

CONFIG = {
    "here": HERE,
    "project": "led_driver",
    "size": (W, H),
    "fixed": {
        "H1": (HOLE_INSET, HOLE_INSET, 0), "H2": (W - HOLE_INSET, HOLE_INSET, 0),
        "H3": (HOLE_INSET, H - HOLE_INSET, 0), "H4": (W - HOLE_INSET, H - HOLE_INSET, 0),
        "J1": (12.5, 22.5, 270),       # plug entry 0.5 mm in from the left edge (silkscreen stays on the board)
        "J3": (W - 8.5, 15.0, 90),     # blue string, wire entry 0.5 mm in from the right edge
        "J4": (W - 8.5, 34.0, 90),     # red string
        "J2": (14.0, H - 3.5, 90),     # PWM from the sensor node
        "U1": (30.0, 12.0, 0),
        "U2": (30.0, 33.0, 0),
        # switch node: AL8860 SW pins (right side), then diode, then inductor, then terminal
        "D2": (35.5, 12.0, 90), "L1": (42.5, 11.5, 90),
        "D3": (35.5, 33.0, 90), "L2": (42.5, 32.5, 90),
    },
    "near": {
        "U1": ["C3", "C2", "R1", "R2"],
        "U2": ["C5", "C4", "R3", "R4"],
        "J1": ["F1", "D1", "C1"],
    },
    "silk_refs": ("J2", "J3", "J4", "L"),  # the rest sit too close to pads; F.Fab has them
    "overhang": {"J1", "J3", "J4"},   # connector courtyards reach just past the board edge
    "placement_keepouts": [],
    "copper_keepouts": [],
    "netclasses": NETCLASSES,
    "netclass_nets": {"Power": POWER_NETS},
}


if __name__ == "__main__":
    gp.build(CONFIG)
