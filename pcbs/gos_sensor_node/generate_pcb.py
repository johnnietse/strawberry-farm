#!/usr/bin/env python3
"""G.O.S. sensor node rev 3.1 board generator (KiCad 9 pcbnew API).

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" generate_pcb.py
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" route_pcb.py

generate_pcb.py builds gos_sensor_node.kicad_pcb from the schematic: 40 x 65 mm
outline, M2.5 holes where mechanical/enclosure_gen.scad puts its posts, every
footprint and net from the netlist, a grouped placement, the antenna keep-out
and the net classes. route_pcb.py then autoroutes it, pours ground and runs
DRC (see HARDWARE.md).

build() is shared with pcbs/led_driver/generate_pcb.py; each board passes its
own CONFIG.

Placement rules for this board:
- module U4 on the top edge, antenna keep-out outward
- USB-C J1 on the bottom edge, socket facing out
- SHT40 U5 and TSL2591 U6 on the side edges, away from the charger and buck
- each passive as close as possible to the chip it belongs to
- no courtyard overlaps (checked here, and again by DRC)
"""
import json
import math
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

OX, OY = 100.0, 100.0        # board origin on the KiCad sheet
EDGE_KEEP = 0.5              # courtyards stay this far inside the outline
GAP = 0.25                   # extra spacing between courtyards

W, H = 40.0, 65.0            # sensor node size, mm (mechanical/enclosure_gen.scad)
HOLE_INSET = 5.0             # enclosure posts sit 5 mm in from each edge

# Net classes: (track width, clearance, via diameter, via drill) in mm.
# Power nets carry at most the charger's 0.54 A input limit (R_ILIM 3.0k);
# 0.3 mm on 1 oz copper carries about 1 A at 10 C rise and still necks into the
# 0.5 mm-pitch QFN/WSON pads (0.4 mm cannot, and the router gives up there).
# GND is routed at the default width: the pours on both layers carry the
# ground current, the tracks only guarantee every pad is connected. +3V3 is
# also default width: the buck delivers at most 300 mA and the radio peaks
# near 15 mA, and the SHT40's 0.3 mm pads take a 0.2 mm track cleanly.
SENSOR_NETCLASSES = {
    "Default": (0.2, 0.15, 0.6, 0.3),
    "Power": (0.3, 0.15, 0.6, 0.3),
}
SENSOR_POWER_NETS = ["VBUS", "/Connectors/VBUS_CONN", "VSYS", "VBAT",
                     "/Power/BAT_P", "/Power/BAT_N", "/Power/FET_D", "/Power/BUCK_SW"]

CONFIG = {
    "here": HERE,
    "project": "gos_sensor_node",
    "size": (W, H),
    # Fixed parts: (x, y, rotation) in board mm, origin top-left.
    "fixed": {
        "U4": (20.0, 8.85, 0),         # module; antenna keep-out at the top edge
        "J1": (20.0, H - 3.1, 0),      # USB-C; footprint marks the board edge 3.1 mm below its origin
        "H1": (HOLE_INSET, HOLE_INSET, 0), "H2": (W - HOLE_INSET, HOLE_INSET, 0),
        "H3": (HOLE_INSET, H - HOLE_INSET, 0), "H4": (W - HOLE_INSET, H - HOLE_INSET, 0),
        "U5": (3.0, 26.0, 90),         # SHT40, left edge, upwind of everything (room to route all four pads)
        "C13": (3.0, 23.7, 180),       # SHT40 decoupling, pads straight above its VDD and GND pads
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
    },
    # Everything else is placed near an anchor part, in this order.
    "near": {
        "U4": ["C10", "C11", "C12", "Y1", "C8", "C9", "R10", "R11", "C7", "D2", "R12"],
        "U5": ["R13", "R14", "R15"],
        "U6": ["C14"],
        "U1": ["C1", "C2", "R4", "TH1", "C3", "R1", "R2", "R3", "R5", "R6", "R7", "D1"],  # R4/TH1 early: corner pins 16/1
        "U2": ["C4", "L1", "C5"],
        "U3": ["R8", "C6", "R9"],
        "J1": ["F1", "U7", "R16", "R17", "R18", "R19"],
        "J4": ["R20", "R21", "R22", "R23"],
        "J2": ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7"],
    },
    "silk_refs": ("J3", "J5", "SW", "D1"),  # labels kept on silkscreen (the rest collide with pads)
    "overhang": {"J1"},                     # USB-C socket front sits past the board edge by design
    # No other parts in this strip along the top edge (module antenna is the top 4.3 mm).
    "placement_keepouts": [(0.0, 0.0, W, 6.5)],
    # No copper at all, either layer, across the full width beside the antenna
    # (Raytac: keep the antenna area clear of copper and ground; the module's own
    # keep-out only covers its width).
    "copper_keepouts": [(0.0, 0.0, W, 4.9)],
    "netclasses": SENSOR_NETCLASSES,
    "netclass_nets": {"Power": SENSOR_POWER_NETS},
}


def mm(v):
    return pcbnew.FromMM(v)


def netlist(here, project):
    path = os.path.join(tempfile.mkdtemp(prefix="gos_pcb_"), "net.net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", path,
                    os.path.join(here, project + ".kicad_sch")], check=True, capture_output=True)
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


def inside(box, w, h):
    return (box[0] >= EDGE_KEEP and box[1] >= EDGE_KEEP and
            box[2] <= w - EDGE_KEEP and box[3] <= h - EDGE_KEEP)


def place_near(fp, ax, ay, taken, w, h, rotations=(0, 90)):
    """Spiral out from (ax, ay) until the courtyard fits without overlap."""
    step = 0.25
    for ring in range(0, 200):
        r = ring * step
        points = [(0.0, 0.0)] if ring == 0 else []
        n = max(8, ring * 8)
        for i in range(n):
            a = 2 * math.pi * i / n
            points.append((r * math.cos(a), r * math.sin(a)))
        for dx, dy in points:
            for rot in rotations:
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(pcbnew.VECTOR2I(mm(OX + ax + dx), mm(OY + ay + dy)))
                box = courtyard(fp)
                if inside(box, w, h) and not any(overlaps(box, t) for t in taken):
                    return box
    raise SystemExit("no room for " + fp.GetReference())


def rect_outline(x1, y1, x2, y2):
    poly = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        poly.Append(mm(OX + x), mm(OY + y))
    poly.SetClosed(True)
    return poly


def add_copper_keepout(board, rect):
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetDoNotAllowCopperPour(True)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(ls)
    zone.SetZoneName("antenna keep-out")
    zone.Outline().AddOutline(rect_outline(*rect))
    board.Add(zone)


def write_netclasses(cfg):
    """Store the net classes in the .kicad_pro, where KiCad, kicad-cli DRC and
    the Specctra export all read them."""
    pro = os.path.join(cfg["here"], cfg["project"] + ".kicad_pro")
    with open(pro, encoding="utf-8") as f:
        data = json.load(f)
    classes = []
    for prio, (name, (track, clear, via, drill)) in enumerate(cfg["netclasses"].items()):
        classes.append({
            "bus_width": 12, "clearance": clear, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)",
            "priority": 2147483647 if name == "Default" else prio,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": track,
            "via_diameter": via, "via_drill": drill, "wire_width": 6,
        })
    data["net_settings"] = {
        "classes": classes,
        "meta": {"version": 4},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [{"netclass": cls, "pattern": net}
                              for cls, names in cfg["netclass_nets"].items() for net in names],
    }
    with open(pro, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def build(cfg):
    w, h = cfg["size"]
    path = os.path.join(cfg["here"], cfg["project"] + ".kicad_pcb")
    comps, nets = netlist(cfg["here"], cfg["project"])
    write_netclasses(cfg)
    board = pcbnew.NewBoard(path)  # fresh board each run; the file is fully generated
    board.SetCopperLayerCount(2)

    netinfo = {}
    for name in sorted(set(nets.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    # outline
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
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
        if not ref.startswith(cfg["silk_refs"]):
            # small-part labels go on the assembly drawing, not the silkscreen
            fp.Reference().SetLayer(pcbnew.F_Fab)
        if ref.startswith("TP"):
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM)
        for pad in fp.Pads():
            net = nets.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netinfo[net])
        board.Add(fp)
        footprints[ref] = fp

    fixed, near = cfg["fixed"], cfg["near"]
    planned = set(fixed) | {r for group in near.values() for r in group}
    missing = set(footprints) - planned
    extra = planned - set(footprints)
    if missing or extra:
        raise SystemExit(f"placement table out of date: unplaced {sorted(missing)}, unknown {sorted(extra)}")

    taken = []
    for ref, (x, y, rot) in fixed.items():
        fp = footprints[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
        box = courtyard(fp)
        if ref not in cfg["overhang"] and not inside(box, w, h):
            raise SystemExit(f"{ref} courtyard {box} leaves the board")
        clash = [o for o, t in taken if overlaps(box, t, 0)]
        if clash:
            raise SystemExit(f"{ref} overlaps {clash}")
        taken.append((ref, box))
    for i, rect in enumerate(cfg.get("placement_keepouts", [])):
        taken.append((f"keepout{i}", rect))

    for anchor, group in near.items():
        ax, ay = (pcbnew.ToMM(footprints[anchor].GetPosition().x) - OX,
                  pcbnew.ToMM(footprints[anchor].GetPosition().y) - OY)
        for ref in group:
            box = place_near(footprints[ref], ax, ay, [t for _, t in taken], w, h)
            taken.append((ref, box))

    for rect in cfg.get("copper_keepouts", []):
        add_copper_keepout(board, rect)

    board.Save(path)
    print(f"placed {len(footprints)} footprints, {len(netinfo)} nets, board {w} x {h} mm")
    return path


def main():
    build(CONFIG)


if __name__ == "__main__":
    main()
