#!/usr/bin/env python3
"""G.O.S. sensor node rev 3.1 board generator (KiCad 9 pcbnew API).

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" generate_pcb.py

Builds gos_sensor_node.kicad_pcb from the schematic: 40 x 65 mm outline,
M2.5 holes where mechanical/enclosure_gen.scad puts its posts, every
footprint and net from the netlist, and a grouped placement. It does not
route. Run KiCad's DRC afterwards (see HARDWARE.md); the only expected
errors are unrouted connections.

Placement rules it follows:
- module U4 on the top edge, antenna keep-out outward
- USB-C J1 on the bottom edge, socket facing out
- SHT40 U5 and TSL2591 U6 on the side edges, away from the charger and buck
- each passive as close as possible to the chip it belongs to
- no courtyard overlaps (checked here, and again by DRC)
"""
import os
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_schematics import kids, parse, unq  # noqa: E402

KICAD = r"C:\Program Files\KiCad\9.0"
FPDIR = os.environ.get("KICAD9_FOOTPRINT_DIR", KICAD + r"\share\kicad\footprints")
KICAD_CLI = os.environ.get("KICAD_CLI", KICAD + r"\bin\kicad-cli.exe")
BOARD = os.path.join(HERE, "gos_sensor_node.kicad_pcb")

W, H = 40.0, 65.0            # board size, mm (mechanical/enclosure_gen.scad)
OX, OY = 100.0, 100.0        # board origin on the KiCad sheet
HOLE_INSET = 5.0             # enclosure posts sit 5 mm in from each edge
EDGE_KEEP = 0.5              # courtyards stay this far inside the outline
GAP = 0.25                   # extra spacing between courtyards
ANTENNA_CLEAR = 6.5          # no other parts in this strip along the top edge (module antenna is the top 4.3 mm)
SILK_REFS = ("J3", "J5", "SW", "D1")  # labels that stay on the silkscreen (the rest collide with pads)
OVERHANG = {"J1"}             # USB-C socket front sits past the board edge by design

# Fixed parts: (x, y, rotation) in board mm, origin top-left.
FIXED = {
    "U4": (20.0, 8.85, 0),         # module; antenna keep-out at the top edge
    "J1": (20.0, H - 3.1, 0),      # USB-C; footprint marks the board edge 3.1 mm below its origin
    "H1": (HOLE_INSET, HOLE_INSET, 0), "H2": (W - HOLE_INSET, HOLE_INSET, 0),
    "H3": (HOLE_INSET, H - HOLE_INSET, 0), "H4": (W - HOLE_INSET, H - HOLE_INSET, 0),
    "U5": (2.2, 26.0, 90),         # SHT40, left edge, upwind of everything
    "U6": (W - 2.2, 26.0, 90),     # TSL2591, right edge, nothing tall beside it
    "J2": (W - 6.0, 36.0, 0),      # SWD header
    "J3": (2.6, 31.0, 0),          # I2C header, left edge
    "J4": (W - 2.6, 46.5, 0),      # LED-board PWM header, right edge
    "J5": (3.0, 47.0, 0),          # battery lead, left edge
    "U1": (18.0, 42.0, 0),         # charger
    "U2": (29.0, 42.0, 0),         # buck
    "U3": (11.0, 58.0, 0),         # DW01A
    "Q1": (11.5, 46.0, 90),        # FS8205A, beside the battery connector
    "Q2": (11.5, 53.0, 0),         # reverse-cell P-FET
    "SW1": (6.5, 15.0, 0), "SW2": (33.5, 15.0, 0),
}

# Everything else is placed near an anchor part, in this order.
NEAR = {
    "U4": ["C10", "C11", "C12", "Y1", "C8", "C9", "R10", "R11", "C7", "D2", "R12"],
    "U5": ["C13", "R13", "R14", "R15"],
    "U6": ["C14"],
    "U1": ["C1", "C2", "C3", "R1", "R2", "R3", "R4", "TH1", "R5", "R6", "R7", "D1"],
    "U2": ["C4", "L1", "C5"],
    "U3": ["R8", "C6", "R9"],
    "J1": ["F1", "U7", "R16", "R17", "R18", "R19"],
    "J4": ["R20", "R21", "R22", "R23"],
    "J2": ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7"],
}


def mm(v):
    return pcbnew.FromMM(v)


def netlist():
    path = os.path.join(tempfile.mkdtemp(prefix="gos_pcb_"), "net.net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", path,
                    os.path.join(HERE, "gos_sensor_node.kicad_sch")], check=True, capture_output=True)
    with open(path, encoding="utf-8") as f:
        tree = parse(f.read())
    comps = {}
    for c in kids(kids(tree, "components")[0], "comp"):
        ref = unq(kids(c, "ref")[0][1])
        sheet = unq(kids(kids(c, "sheetpath")[0], "tstamps")[0][1])
        comps[ref] = {
            "value": unq(kids(c, "value")[0][1]),
            "footprint": unq(kids(c, "footprint")[0][1]),
            "path": sheet + unq(kids(c, "tstamps")[0][1]),
            "sheetname": unq(kids(kids(c, "sheetpath")[0], "names")[0][1]),
        }
    nets = {}
    for n in kids(kids(tree, "nets")[0], "net"):
        name = unq(kids(n, "name")[0][1])
        for node in kids(n, "node"):
            nets[(unq(kids(node, "ref")[0][1]), unq(kids(node, "pin")[0][1]))] = name
    return comps, nets


def courtyard(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    box = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(box.GetLeft()) - OX, pcbnew.ToMM(box.GetTop()) - OY,
            pcbnew.ToMM(box.GetRight()) - OX, pcbnew.ToMM(box.GetBottom()) - OY)


def overlaps(a, b, gap=GAP):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def inside(box):
    return (box[0] >= EDGE_KEEP and box[1] >= EDGE_KEEP and
            box[2] <= W - EDGE_KEEP and box[3] <= H - EDGE_KEEP)


def place_near(fp, ax, ay, taken, rotations=(0, 90)):
    """Spiral out from (ax, ay) until the courtyard fits without overlap."""
    step = 0.25
    for ring in range(0, 200):
        r = ring * step
        points = [(0.0, 0.0)] if ring == 0 else []
        n = max(8, ring * 8)
        for i in range(n):
            import math
            a = 2 * math.pi * i / n
            points.append((r * math.cos(a), r * math.sin(a)))
        for dx, dy in points:
            for rot in rotations:
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(pcbnew.VECTOR2I(mm(OX + ax + dx), mm(OY + ay + dy)))
                box = courtyard(fp)
                if inside(box) and not any(overlaps(box, t) for t in taken):
                    return box
    raise SystemExit("no room for " + fp.GetReference())


def main():
    comps, nets = netlist()
    board = pcbnew.NewBoard(BOARD)  # fresh board each run; the file is fully generated
    board.SetCopperLayerCount(2)

    netinfo = {}
    for name in sorted(set(nets.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    # outline
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(mm(OX + x1), mm(OY + y1)))
        seg.SetEnd(pcbnew.VECTOR2I(mm(OX + x2), mm(OY + y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)

    footprints = {}
    for ref, c in comps.items():
        lib, name = c["footprint"].split(":")
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
        if fp is None:
            raise SystemExit(f"footprint {c['footprint']} not found for {ref}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetSheetname(c["sheetname"].strip("/"))
        if not ref.startswith(SILK_REFS):
            # dense board: small-part labels go on the assembly drawing, not the silkscreen
            fp.Reference().SetLayer(pcbnew.F_Fab)
        if ref.startswith("TP"):
            fp.SetAttributes(fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_BOM)
        for pad in fp.Pads():
            net = nets.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netinfo[net])
        board.Add(fp)
        footprints[ref] = fp

    planned = set(FIXED) | {r for group in NEAR.values() for r in group}
    missing = set(footprints) - planned
    extra = planned - set(footprints)
    if missing or extra:
        raise SystemExit(f"placement table out of date: unplaced {sorted(missing)}, unknown {sorted(extra)}")

    taken = []
    for ref, (x, y, rot) in FIXED.items():
        fp = footprints[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
        box = courtyard(fp)
        if ref not in OVERHANG and not inside(box):
            raise SystemExit(f"{ref} courtyard {box} leaves the board")
        clash = [o for o, t in taken if overlaps(box, t, 0)]
        if clash:
            raise SystemExit(f"{ref} overlaps {clash}")
        taken.append((ref, box))
    # keep the module's antenna corridor clear of other parts, full board width
    taken.append(("antenna", (0.0, 0.0, W, ANTENNA_CLEAR)))

    for anchor, group in NEAR.items():
        ax, ay = (pcbnew.ToMM(footprints[anchor].GetPosition().x) - OX,
                  pcbnew.ToMM(footprints[anchor].GetPosition().y) - OY)
        for ref in group:
            box = place_near(footprints[ref], ax, ay, [t for _, t in taken])
            taken.append((ref, box))

    board.Save(BOARD)
    print(f"placed {len(footprints)} footprints, {len(netinfo)} nets, board {W} x {H} mm")


if __name__ == "__main__":
    main()
