#!/usr/bin/env python3
"""Measure the layout areas that need a hand review (sensor node).

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" review_layout.py

Prints, for the routed board:
- USB 2.0 pair: length of each line, mismatch, vias, layers, spacing to other copper
- buck converter (U2 TPS62740): switching-loop path lengths and part distances
- antenna strip: any copper, via or pour inside the keep-out on any layer
Results are summarised in documentation/design_review.md.
"""
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OX, OY = 100.0, 100.0
T = pcbnew.ToMM


def xy(v):
    return (round(T(v.x) - OX, 2), round(T(v.y) - OY, 2))


def net_report(board, name):
    tracks = [t for t in board.GetTracks() if t.GetNetname() == name]
    segs = [t for t in tracks if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in tracks if t.GetClass() == "PCB_VIA"]
    length = sum(T(t.GetLength()) for t in segs)
    layers = sorted({pcbnew.LayerName(t.GetLayer()) for t in segs})
    widths = sorted({round(T(t.GetWidth()), 2) for t in segs})
    return length, len(vias), layers, widths


def pad(board, ref, num):
    for p in board.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            return p
    raise KeyError(ref + "." + num)


def dist(a, b):
    pa, pb = a.GetPosition(), b.GetPosition()
    return math.hypot(T(pa.x - pb.x), T(pa.y - pb.y))


def main():
    board = pcbnew.LoadBoard(os.path.join(HERE, "gos_sensor_node.kicad_pcb"))

    print("== USB 2.0 full-speed pair (12 Mbit/s)")
    for pair in (("/Connectors/USB_CONN_DP", "/Connectors/USB_CONN_DN"), ("USB_DP", "USB_DN")):
        r = [net_report(board, n) for n in pair]
        for n, (length, vias, layers, widths) in zip(pair, r):
            print(f"  {n:26s} {length:6.1f} mm, {vias} vias, layers {layers}, width {widths}")
        print(f"  mismatch {abs(r[0][0] - r[1][0]):.1f} mm")

    print("== Buck converter U2 (TPS62740) switching loop")
    sw, vin, gnd = pad(board, "U2", "2"), pad(board, "U2", "1"), pad(board, "U2", "3")
    for ref in ("L1", "C4", "C5"):
        fp = board.FindFootprintByReference(ref)
        nets = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
        print(f"  {ref} {fp.GetValue():14s} at {xy(fp.GetPosition())}, nets {nets}, "
              f"{dist(fp, board.FindFootprintByReference('U2')):.1f} mm from U2")
    for name in ("/Power/BUCK_SW",):
        length, vias, layers, widths = net_report(board, name)
        print(f"  {name}: {length:.1f} mm of track, {vias} vias, layers {layers}, width {widths}")
    c4 = board.FindFootprintByReference("C4")
    vin_cap = [p for p in c4.Pads() if p.GetNetname() == "VSYS"]
    if vin_cap:
        print(f"  input cap C4 pad to U2 VIN pin: {dist(vin_cap[0], vin):.2f} mm (centre to centre)")
    print(f"  U2 SW pin to GND pin: {dist(sw, gnd):.2f} mm")

    print("== Antenna keep-out (y < 4.9 mm, full width, every copper layer)")
    limit = pcbnew.FromMM(OY + 4.9)
    hits = []
    for t in board.GetTracks():
        bb = t.GetBoundingBox()
        if bb.GetTop() < limit:
            hits.append(f"{t.GetClass()} {t.GetNetname()} {xy(t.GetPosition())}")
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in z.GetLayerSet().CuStack():
            poly = z.GetFilledPolysList(layer)
            for i in range(poly.OutlineCount()):
                bb = poly.Outline(i).BBox()
                if bb.GetTop() < limit:
                    hits.append(f"pour {z.GetZoneName()} on {pcbnew.LayerName(layer)} reaches y {T(bb.GetTop()) - OY:.2f}")
    module_pads = [p for p in board.FindFootprintByReference("U4").Pads() if p.GetBoundingBox().GetTop() < limit]
    print(f"  tracks/vias/pours inside: {len(hits)}" + "".join("\n    " + h for h in hits))
    print(f"  module pads inside (expected, part of the module): {len(module_pads)}")


if __name__ == "__main__":
    main()
