#!/usr/bin/env python3
"""G.O.S. LED driver board rev 1.1 board generator (KiCad 9 pcbnew API).

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" generate_pcb.py
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" ..\\gos_sensor_node\\route_pcb.py .

Uses the sensor node's board builder (pcbs/gos_sensor_node/generate_pcb.py)
with this board's placement. 60 x 45 mm, four M3 holes, 4 layers (two inner GND planes).

Layout:
- J1 24 V jack on the left edge, plug entry facing out; F1, D1 and C1 beside it
- blue channel (U1) in the top half, red channel (U2) in the bottom half
- J3 / J4 LED terminals on the right edge, wire entry facing out
- J2 PWM header along the bottom edge
- rev 1.1: a 10 uF capacitor across each LED string beside its inductor (C6, C7)
- rev 1.1: each channel's second sense resistor (R5 blue, R6 red) and its solder jumper (JP1,
  JP2) beside the first sense resistor, so the 667 mA option keeps the SET loop short
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
        # switching loops placed by hand: input cap at VIN, diode anode and inductor at SW
        "C2": (35.0, 9.20, 90),     # input cap, pad 1 (VIN) by the AL8860 VIN pin
        "D2": (37.6, 13.40, 180),   # freewheel diode, anode by the SW pins
        "L1": (37.6, 18.60, 180),   # inductor, pad 2 (SW) under the diode anode
        "C4": (35.0, 30.20, 90),     # input cap, pad 1 (VIN) by the AL8860 VIN pin
        "D3": (37.6, 34.40, 180),   # freewheel diode, anode by the SW pins
        "L2": (37.6, 39.60, 180),   # inductor, pad 2 (SW) under the diode anode
    },
    "near": {
        "U1": ["C3", "R1", "R2", "R5", "JP1"],
        "U2": ["C5", "R3", "R4", "R6", "JP2"],
        "L1": ["C6"],                  # rev 1.1: across the blue string (SET to LEDK), beside its inductor
        "L2": ["C7"],                  # rev 1.1: across the red string
        "J1": ["F1", "D1", "C1"],
    },
    "silk_refs": ("J2", "J3", "J4"),  # the rest sit too close to pads; F.Fab has them (rev 1.1: L1 / L2 labels now meet C6 / C7)
    "overhang": {"J1", "J3", "J4"},   # connector courtyards reach just past the board edge
    "placement_keepouts": [],
    "copper_keepouts": [],
    "netclasses": NETCLASSES,
    "netclass_nets": {"Power": POWER_NETS},
    # locked copper laid by hand before autorouting (F.Cu): short SW nodes, VIN at the input caps
    "preroute_tracks": [
        ('/SW_BLUE', 0.4, [(32.11, 12.33), (32.11, 12.97), (33.6, 12.97), (35.6, 13.4), (35.55, 18.6)]),
        ('/VIN', 0.4, [(35.0, 10.68), (33.0, 11.03), (32.11, 11.03)]),
        ('/VIN', 0.4, [(39.6, 13.4), (39.6, 11.2), (36.0, 11.2), (35.0, 10.68)]),
        ('GND', 0.4, [(35.0, 7.72), (35.0, 6.6)]),
        ('/SW_RED', 0.4, [(32.11, 33.33), (32.11, 33.97), (33.6, 33.97), (35.6, 34.4), (35.55, 39.6)]),
        ('/VIN', 0.4, [(35.0, 31.68), (33.0, 32.03), (32.11, 32.03)]),
        ('/VIN', 0.4, [(39.6, 34.4), (39.6, 32.2), (36.0, 32.2), (35.0, 31.68)]),
        ('GND', 0.4, [(35.0, 28.72), (35.0, 27.6)]),
    ],
    "preroute_vias": [('GND', 35.0, 6.6), ('GND', 35.0, 27.6)],
}


if __name__ == "__main__":
    gp.build(CONFIG)
