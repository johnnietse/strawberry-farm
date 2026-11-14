#!/usr/bin/env python3
"""Autoroute a generated board, pour ground, check it and write fabrication files.

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" route_pcb.py [board_dir] [--passes N]

board_dir defaults to this folder (sensor node); pass ../led_driver for the LED
board. Run that board's generate_pcb.py first.

Steps:
1. Export the board to Specctra DSN (net classes from the .kicad_pro set the
   track widths and vias per net).
2. Route it with Freerouting (headless). Set FREEROUTING_JAR to the jar and,
   if needed, JAVA to a java.exe the jar supports. Freerouting 2.0.1 runs on
   Java 21 or later; 2.2 and later need Java 25.
3. Import the session, add thermal vias in exposed ground pads (they are in
   the export too, so the router keeps clear of them), add a GND pour on both
   copper layers and fill it.
4. Run KiCad DRC with schematic parity. If the router only left connections
   unrouted, or wrote no session, start again from the unrouted board (up to
   ATTEMPTS times); stop on any other DRC finding.
5. Write Gerbers, drill files and a pick-and-place file to <board_dir>/fab,
   and a zip of the Gerbers and drill files for the board house.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import pcbnew

KICAD = r"C:\Program Files\KiCad\9.0"
KICAD_CLI = os.environ.get("KICAD_CLI", KICAD + r"\bin\kicad-cli.exe")
JAVA = os.environ.get("JAVA", "java")
FREEROUTING_JAR = os.environ.get("FREEROUTING_JAR", "")

OX, OY = 100.0, 100.0          # board origin used by generate_pcb.py
ATTEMPTS = 4                    # full routing attempts before giving up
ROUTE_TIMEOUT = 900             # s; Freerouting normally needs well under a minute here
POUR_CLEARANCE = 0.25          # mm, ground pour to other copper
POUR_MIN_WIDTH = 0.25          # mm, thinnest pour neck
GERBER_LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


class RouteFailed(Exception):
    """Freerouting produced no usable session; worth another attempt."""


def run(cmd, **kw):
    print("+", " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)))
    return subprocess.run(cmd, check=True, **kw)


def board_file(board_dir):
    pcbs = [p for p in glob.glob(os.path.join(board_dir, "*.kicad_pcb"))]
    if len(pcbs) != 1:
        raise SystemExit(f"expected one .kicad_pcb in {board_dir}, found {pcbs}")
    return pcbs[0]


def rule_area(board, poly, layers, name):
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetDoNotAllowCopperPour(True)
    zone.SetLayerSet(layers)
    zone.SetZoneName(name)
    zone.Outline().AddOutline(poly)
    board.Add(zone)


THERMAL_VIA = (0.6, 0.3)        # mm, diameter and drill of the vias in exposed pads
THERMAL_PITCH = 0.8             # mm


def thermal_via_positions(board):
    """Grid of via positions inside each exposed ground pad (QFN/WSON/MSOP
    thermal pad: a GND SMD pad of at least 1 mm^2 at the centre of a part with
    8 or more pads). They conduct heat to the bottom pour."""
    d = pcbnew.FromMM(THERMAL_VIA[0])
    pitch = pcbnew.FromMM(THERMAL_PITCH)
    spots = []
    for fp in board.GetFootprints():
        if fp.GetPadCount() < 8:
            continue
        for pad in fp.Pads():
            size = pad.GetBoundingBox()
            if (pad.GetNetname() != "GND" or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD
                    or pcbnew.ToMM(size.GetWidth()) * pcbnew.ToMM(size.GetHeight()) < 1.0
                    or (pad.GetPosition() - fp.GetPosition()).EuclideanNorm() > pcbnew.FromMM(0.3)):
                continue                   # exposed pads sit at the part's centre; header pads do not
            axes = []
            for lo, length in ((size.GetLeft(), size.GetWidth()), (size.GetTop(), size.GetHeight())):
                n = max(1, int((length - d) // pitch) + 1)
                first = lo + length // 2 - (n - 1) * pitch // 2
                axes.append([first + i * pitch for i in range(n)])
            spots += [(x, y, pad.GetNet()) for x in axes[0] for y in axes[1]]
    return spots


def add_thermal_vias(board, spots):
    for x, y, net in spots:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pcbnew.VECTOR2I(x, y))
        via.SetWidth(pcbnew.FromMM(THERMAL_VIA[0]))
        via.SetDrill(pcbnew.FromMM(THERMAL_VIA[1]))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(board.FindNet(net.GetNetname()))
        via.SetLocked(True)
        board.Add(via)


def prepare_for_router(board):
    """Adjust a throw-away copy of the board so Freerouting can satisfy KiCad's DRC.

    - Freerouting keeps its track clearance from keep-outs, KiCad does not. A
      footprint keep-out whose notches touch the pads (the SHT4x footprint)
      would leave those pads unreachable, so a clearance-wide window is cut
      out of it around each pad; the rest of the keep-out stays. The board that gets saved keeps the original, and DRC checks
      against it.
    - Freerouting does not know KiCad's copper-to-edge clearance, so the edges
      get keep-out strips of that width.
    """
    shrink = max(c.GetClearance() for c in board.GetDesignSettings().m_NetSettings.GetNetclasses().values())
    shrink = max(shrink, board.GetDesignSettings().m_NetSettings.GetDefaultNetclass().GetClearance())
    for fp in board.GetFootprints():
        pads = [p.GetBoundingBox() for p in fp.Pads()]
        for zone in list(fp.Zones()):
            if not zone.GetIsRuleArea():
                continue
            outline = zone.Outline()
            if not any(outline.Collide(pcbnew.VECTOR2I(b.Centre())) or
                       any(outline.Collide(pcbnew.VECTOR2I(x, y)) for x in (b.GetLeft(), b.GetRight())
                           for y in (b.GetTop(), b.GetBottom())) for b in pads):
                continue
            poly = pcbnew.SHAPE_POLY_SET(outline)
            for b in pads:                 # open a clearance-wide window around each pad
                win = pcbnew.SHAPE_POLY_SET()
                chain = pcbnew.SHAPE_LINE_CHAIN()
                for x, y in ((b.GetLeft() - shrink, b.GetTop() - shrink), (b.GetRight() + shrink, b.GetTop() - shrink),
                             (b.GetRight() + shrink, b.GetBottom() + shrink), (b.GetLeft() - shrink, b.GetBottom() + shrink)):
                    chain.Append(x, y)
                chain.SetClosed(True)
                win.AddOutline(chain)
                poly.BooleanSubtract(win)
            layers = zone.GetLayerSet()
            fp.Remove(zone)
            for i in range(poly.OutlineCount()):
                rule_area(board, poly.Outline(i), layers, f"{fp.GetReference()} keep-out (router)")
    edge = board.GetDesignSettings().m_CopperEdgeClearance
    box = board.GetBoardEdgesBoundingBox()
    x1, y1, x2, y2 = box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()
    both = pcbnew.LSET()
    both.AddLayer(pcbnew.F_Cu)
    both.AddLayer(pcbnew.B_Cu)
    for rx1, ry1, rx2, ry2 in ((x1, y1, x2, y1 + edge), (x1, y2 - edge, x2, y2),
                               (x1, y1, x1 + edge, y2), (x2 - edge, y1, x2, y2)):
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in ((rx1, ry1), (rx2, ry1), (rx2, ry2), (rx1, ry2)):
            chain.Append(x, y)
        chain.SetClosed(True)
        rule_area(board, chain, both, "edge clearance (router)")


def autoroute(path, passes):
    if not FREEROUTING_JAR or not os.path.exists(FREEROUTING_JAR):
        raise SystemExit("set FREEROUTING_JAR to freerouting-<version>.jar")
    work = tempfile.mkdtemp(prefix="gos_route_")
    dsn, ses = os.path.join(work, "board.dsn"), os.path.join(work, "board.ses")
    board = pcbnew.LoadBoard(path)
    if len(board.GetTracks()) or any(not z.GetIsRuleArea() for z in board.Zones()):
        raise SystemExit("board already routed or poured; run generate_pcb.py first")
    export = pcbnew.LoadBoard(path)        # throw-away copy for the router
    prepare_for_router(export)
    add_thermal_vias(export, thermal_via_positions(export))  # fixed obstacles for the router
    if not pcbnew.ExportSpecctraDSN(export, dsn):
        raise SystemExit("Specctra export failed")
    # Freerouting 2.0.1 can keep retrying a net it cannot fit and ignore -mp,
    # hence the timeout. Do not pass "-mt 1": with it, 2.0.1 writes an empty session.
    run([JAVA, "-Djava.awt.headless=true", "-jar", FREEROUTING_JAR,
         "-de", dsn, "-do", ses, "-mp", str(passes), "--gui.enabled=false"],
        timeout=ROUTE_TIMEOUT)
    if not os.path.exists(ses) or os.path.getsize(ses) == 0:
        raise RouteFailed("Freerouting wrote no session")
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise RouteFailed("Specctra session import failed")
    have = {(v.GetPosition().x, v.GetPosition().y) for v in board.GetTracks() if v.GetClass() == "PCB_VIA"}
    add_thermal_vias(board, [s for s in thermal_via_positions(board) if (s[0], s[1]) not in have])
    return board


def add_ground_pour(board):
    gnd = board.FindNet("GND")
    if gnd is None:
        raise SystemExit("board has no GND net")
    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline):
        raise SystemExit("board outline is not closed")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(gnd)
        zone.SetZoneName(f"GND {pcbnew.LayerName(layer)}")
        zone.Outline().AddOutline(outline.Outline(0))
        zone.SetLocalClearance(pcbnew.FromMM(POUR_CLEARANCE))
        zone.SetMinThickness(pcbnew.FromMM(POUR_MIN_WIDTH))
        # SMD pads join the pour solid (their small spokes starve on fine-pitch
        # parts); through-hole pads keep thermal reliefs for hand soldering.
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        zone.SetAssignedPriority(0)
        board.Add(zone)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            # shield and mounting tabs: full connection (mechanical, and a
            # thermal relief there can end up with a single spoke)
            if pad.GetNetname() == "GND" and pad.GetNumber().startswith(("S", "MP")):
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def drc(path, report):
    run([KICAD_CLI, "pcb", "drc", "--schematic-parity", "--severity-all", "--format", "json",
         "--units", "mm", "-o", report, path], capture_output=True)
    with open(report, encoding="utf-8") as f:
        data = json.load(f)
    found = {k: data.get(k, []) for k in ("violations", "unconnected_items", "schematic_parity")}
    for kind, items in found.items():
        for item in items[:30]:
            where = "; ".join(i.get("description", "") for i in item.get("items", []))
            print(f"  {kind}: [{item.get('severity')}] {item.get('type')}: {item.get('description')} | {where}")
    counts = {k: len(v) for k, v in found.items()}
    print("DRC:", counts)
    return counts


def fabrication(path, board_dir):
    name = os.path.splitext(os.path.basename(path))[0]
    fab = os.path.join(board_dir, "fab")
    gerbers = os.path.join(fab, "gerbers")
    shutil.rmtree(fab, ignore_errors=True)
    os.makedirs(gerbers)
    run([KICAD_CLI, "pcb", "export", "gerbers", "-l", GERBER_LAYERS, "--subtract-soldermask",
         "-o", gerbers + os.sep, path], capture_output=True)
    run([KICAD_CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--generate-map", "--map-format", "pdf", "-u", "mm", "-o", gerbers + os.sep, path],
        capture_output=True)
    run([KICAD_CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "--exclude-dnp", "-o", os.path.join(fab, name + "_pos.csv"), path], capture_output=True)
    zpath = os.path.join(fab, name + "_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gerbers)):
            if not f.endswith(".pdf"):
                z.write(os.path.join(gerbers, f), f)
    print("fabrication files in", fab)


def stats(board):
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    length = sum(pcbnew.ToMM(t.GetLength()) for t in tracks)
    print(f"routed: {len(tracks)} track segments, {length:.0f} mm, {len(vias)} vias")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    passes = 40
    if "--passes" in sys.argv:
        passes = int(sys.argv[sys.argv.index("--passes") + 1])
        args = [a for a in args if a != str(passes)]
    board_dir = os.path.abspath(args[0] if args else os.path.dirname(os.path.abspath(__file__)))
    path = board_file(board_dir)
    # Freerouting's result differs between runs of the same board: it sometimes
    # leaves a connection unrouted, and 2.0.1 occasionally writes an empty
    # session. Each attempt starts again from the unrouted board.
    pristine = tempfile.mkdtemp(prefix="gos_unrouted_")
    stem = os.path.splitext(path)[0]
    for ext in (".kicad_pcb", ".kicad_pro"):
        shutil.copy(stem + ext, pristine)
    unrouted = os.path.join(pristine, os.path.basename(path))
    for attempt in range(1, ATTEMPTS + 1):
        print(f"attempt {attempt} of {ATTEMPTS}")
        try:
            board = autoroute(unrouted, passes)
        except RouteFailed as e:
            print(" ", e)
            counts = None
            continue
        add_ground_pour(board)
        stats(board)
        board.Save(path)
        counts = drc(path, os.path.join(tempfile.mkdtemp(prefix="gos_drc_"), "drc.json"))
        if counts["violations"] or counts["schematic_parity"] or not counts["unconnected_items"]:
            break                          # clean, or a rule problem rerouting will not fix
    else:
        if counts is None:
            raise SystemExit(f"Freerouting failed {ATTEMPTS} times")
    if any(counts.values()):
        raise SystemExit("DRC not clean; fabrication files not written")
    fabrication(path, board_dir)


if __name__ == "__main__":
    main()
