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
   the export too, so the router keeps clear of them), pour GND on every
   copper layer (solid planes on the inner layers of a 4-layer board) and,
   on 4 layers, add ground stitching vias wherever they fit.
4. Run KiCad DRC with schematic parity. If the router only left connections
   unrouted, or wrote no session, start again from the unrouted board (up to
   ATTEMPTS times); stop on any other DRC finding.
5. Write <board_dir>/fab (Gerbers for every layer, drill files, KiCad and
   JLCPCB pick-and-place files, JLCPCB BOM, upload zip; coordinates from the
   board's bottom-left corner) and <board_dir>/docs (assembly, courtyard,
   user-layer and all-layer PDFs, renders, STEP model).

--fab-only skips routing: DRC on the board as it is, then step 5 only.
"""
import csv
import glob
import json
import math
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
    - Every net class routes with 0.01 mm more clearance than DRC checks (pad-shape rounding).
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
    # Freerouting approximates rounded and custom pad shapes (the solder jumpers' half-round pads)
    # and can land a few micrometres inside KiCad's clearance; route with 0.01 mm to spare
    ns = board.GetDesignSettings().m_NetSettings
    for nc in list(ns.GetNetclasses().values()) + [ns.GetDefaultNetclass()]:
        nc.SetClearance(nc.GetClearance() + pcbnew.FromMM(0.01))
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
    if any(not t.IsLocked() for t in board.GetTracks()) or any(not z.GetIsRuleArea() for z in board.Zones()):
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
    hand = [t.Duplicate() for t in board.GetTracks() if t.IsLocked()]   # hand-laid copper
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise RouteFailed("Specctra session import failed")
    # the session import replaces all tracks; put back hand-laid ones it did not return
    have = {(t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)
            for t in board.GetTracks()}
    for t in hand:
        if (t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) not in have:
            board.Add(t)
    # drop router segments that only repeat a hand-laid track (same net and layer, both ends on it)
    locked = [t for t in board.GetTracks() if t.IsLocked() and t.GetClass() == "PCB_TRACK"]
    tol = pcbnew.FromMM(0.02)

    def on(seg, p):
        """Point p within tol of the centreline of track seg."""
        ax, ay, bx, by = seg.GetStart().x, seg.GetStart().y, seg.GetEnd().x, seg.GetEnd().y
        dx, dy = bx - ax, by - ay
        k = 0 if dx == dy == 0 else max(0.0, min(1.0, ((p.x - ax) * dx + (p.y - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p.x - ax - k * dx, p.y - ay - k * dy) <= tol

    for t in [t for t in board.GetTracks() if not t.IsLocked() and t.GetClass() == "PCB_TRACK"]:
        if any(h.GetNetCode() == t.GetNetCode() and h.GetLayer() == t.GetLayer()
               and on(h, t.GetStart()) and on(h, t.GetEnd()) for h in locked):
            board.Remove(t)
    have = {(v.GetPosition().x, v.GetPosition().y) for v in board.GetTracks() if v.GetClass() == "PCB_VIA"}
    add_thermal_vias(board, [s for s in thermal_via_positions(board) if (s[0], s[1]) not in have])
    return board


def drop_single_layer_vias(board):
    """A via whose tracks all arrive on one layer joins nothing (DRC: via_dangling). That
    happens when the router meets a hand-laid end via on the same layer. Remove those, except
    on GND, where vias also tie into the poured planes."""
    gnd = board.FindNet("GND").GetNetCode()
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    removed = 0
    for v in [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]:
        if v.GetNetCode() == gnd:
            continue
        p, r = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) // 2
        touching = [t for t in tracks if t.GetNetCode() == v.GetNetCode()
                    and ((t.GetStart() - p).EuclideanNorm() <= r or (t.GetEnd() - p).EuclideanNorm() <= r)]
        if len({t.GetLayer() for t in touching}) == 1:
            # tracks may end anywhere on the via's pad, not at its centre: join each end to the
            # centre on its own layer first, so removing the via keeps them connected
            for t in touching:
                for end in (t.GetStart(), t.GetEnd()):
                    if 0 < (end - p).EuclideanNorm() <= r:
                        j = pcbnew.PCB_TRACK(board)
                        j.SetStart(end)
                        j.SetEnd(p)
                        j.SetWidth(t.GetWidth())
                        j.SetLayer(t.GetLayer())
                        j.SetNet(t.GetNet())
                        board.Add(j)
            board.Remove(v)
            removed += 1
    if removed:
        print(f"removed {removed} via(s) joined on one layer only")


def copper_layers(board):
    return list(board.GetEnabledLayers().CuStack())


def add_ground_pour(board, layers=None, fill=True):
    """GND pour on every copper layer: solid planes on the inner layers of a
    4-layer board, ground fill around the tracks on the outer layers."""
    gnd = board.FindNet("GND")
    if gnd is None:
        raise SystemExit("board has no GND net")
    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline):
        raise SystemExit("board outline is not closed")
    for layer in layers or copper_layers(board):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(gnd)
        zone.SetZoneName(f"GND {pcbnew.LayerName(layer)}")
        zone.Outline().AddOutline(outline.Outline(0))
        zone.SetLocalClearance(pcbnew.FromMM(POUR_CLEARANCE))
        zone.SetMinThickness(pcbnew.FromMM(POUR_MIN_WIDTH))
        # SMD pads join the pour solid (their small spokes starve on fine-pitch
        # parts); through-hole pads keep thermal reliefs for hand soldering.
        inner = layer not in (pcbnew.F_Cu, pcbnew.B_Cu)
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if inner else pcbnew.ZONE_CONNECTION_THT_THERMAL)
        zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        zone.SetAssignedPriority(0)
        board.Add(zone)
    # A through-hole pad on the outer pour may end up with one thermal spoke (USB
    # shield tabs between tracks); it is also tied to both inner planes, so one is enough.
    board.GetDesignSettings().m_MinResolvedSpokes = 1
    if fill:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())


ROUTER_MADE = {"shorting_items", "tracks_crossing", "clearance", "copper_edge_clearance",
               "track_dangling", "via_dangling", "hole_clearance", "hole_to_hole", "starved_thermal"}


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
    # violations the autorouter can cause and a new routing attempt can clear
    counts["router_made"] = sum(1 for v in found["violations"] if v.get("type") in ROUTER_MADE)
    return counts


def gerber_layers(path):
    board = pcbnew.LoadBoard(path)
    cu = [pcbnew.LayerName(l) for l in board.GetEnabledLayers().CuStack()]
    return ",".join(cu + ["F.Paste", "B.Paste", "F.Silkscreen", "B.Silkscreen", "F.Mask", "B.Mask", "Edge.Cuts"])


STITCH_PITCH = 1.6       # mm, grid for ground stitching vias
STITCH_VIA = (0.6, 0.3)  # mm, diameter and drill
STITCH_CLEARANCE = 0.2   # mm, to any other copper (net clearance is 0.15)
HOLE_GAP = 0.25          # mm, hole to hole (board rule)


def stitch_ground(board):
    """GND vias on a grid wherever they fit, so every piece of outer-layer ground
    pour is tied to both inner planes through many short paths. A spot is used
    only if it is inside the board edge clearance, outside every part courtyard
    and via keep-out, and clear of every pad, every track of another net and
    every existing via."""
    gnd = board.FindNet("GND")
    fm = pcbnew.FromMM
    r = fm(STITCH_VIA[0]) // 2
    clear = fm(STITCH_CLEARANCE)
    # the edge bounding box includes the outline's line width, so keep 0.1 mm extra
    edge = board.GetDesignSettings().m_CopperEdgeClearance + fm(0.1)
    box = board.GetBoardEdgesBoundingBox()
    pads = [pd for fp in board.GetFootprints() for pd in fp.Pads()]
    courtyards = []
    for fp in board.GetFootprints():
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount():
            courtyards.append(cy)
    keepouts = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    keepouts += [z for fp in board.GetFootprints() for z in fp.Zones()
                 if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetCode() != gnd.GetNetCode()]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    placed = []
    step = fm(STITCH_PITCH)
    y = box.GetTop() + edge + r
    while y <= box.GetBottom() - edge - r:
        x = box.GetLeft() + edge + r
        while x <= box.GetRight() - edge - r:
            pt = pcbnew.VECTOR2I(int(x), int(y))
            ok = (not any(c.Collide(pt, r) for c in courtyards)
                  and not any(z.Outline().Collide(pt, r) for z in keepouts)
                  and not any(pd.HitTest(pt, r + clear) for pd in pads)
                  and not any(t.HitTest(pt, r + clear) for t in tracks)
                  and not any((v.GetPosition() - pt).EuclideanNorm() < v.GetWidth(pcbnew.F_Cu) // 2 + r + fm(HOLE_GAP)
                              for v in vias + placed))
            if ok:
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pt)
                via.SetWidth(fm(STITCH_VIA[0]))
                via.SetDrill(fm(STITCH_VIA[1]))
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via.SetNet(gnd)
                board.Add(via)
                placed.append(via)
            x += step
        y += step
    print(f"ground stitching: {len(placed)} vias")
    return len(placed)


def jlc_cpl(pos_csv, out_csv):
    """KiCad position file -> JLCPCB CPL columns. Coordinates are from the board's
    bottom-left corner (the drill/place origin set by generate_pcb.py)."""
    with open(pos_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            w.writerow([r["Ref"], f'{float(r["PosX"]):.4f}mm', f'{float(r["PosY"]):.4f}mm',
                        "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]):.1f}'])
    return len(rows)


def jlc_bom(sch, out_csv):
    """Schematic BOM grouped by LCSC part, in JLCPCB's column names."""
    tmp = out_csv + ".tmp"
    run([KICAD_CLI, "sch", "export", "bom", "--fields", "Value,Reference,Footprint,LCSC,MPN,Manufacturer,${QUANTITY}",
         "--labels", "Comment,Designator,Footprint,JLCPCB Part #,MPN,Manufacturer,Quantity",
         "--group-by", "LCSC,Value,Footprint", "--ref-range-delimiter", "", "--exclude-dnp",
         "-o", tmp, sch], capture_output=True)
    with open(tmp, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    os.remove(tmp)
    header, body = rows[0], rows[1:]
    fi, li = header.index("Footprint"), header.index("JLCPCB Part #")
    missing = [r for r in body if not r[li]]
    if missing:
        raise SystemExit(f"parts without an LCSC number: {[r[header.index('Designator')] for r in missing]}")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in body:
            r[fi] = r[fi].split(":")[-1]
            w.writerow(r)
    return len(body)


def fabrication(path, board_dir):
    name = os.path.splitext(os.path.basename(path))[0]
    fab = os.path.join(board_dir, "fab")
    gerbers = os.path.join(fab, "gerbers")
    shutil.rmtree(fab, ignore_errors=True)
    os.makedirs(gerbers)
    run([KICAD_CLI, "pcb", "export", "gerbers", "-l", gerber_layers(path), "--subtract-soldermask",
         "--use-drill-file-origin", "-o", gerbers + os.sep, path], capture_output=True)
    run([KICAD_CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--drill-origin", "plot", "--generate-map", "--map-format", "pdf", "-u", "mm",
         "-o", gerbers + os.sep, path], capture_output=True)
    pos = os.path.join(fab, name + "_pos.csv")
    run([KICAD_CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "--exclude-dnp", "--use-drill-file-origin", "-o", pos, path], capture_output=True)
    n_cpl = jlc_cpl(pos, os.path.join(fab, name + "_jlcpcb_cpl.csv"))
    n_bom = jlc_bom(os.path.splitext(path)[0] + ".kicad_sch", os.path.join(fab, name + "_jlcpcb_bom.csv"))
    zpath = os.path.join(fab, name + "_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gerbers)):
            if not f.endswith(".pdf"):
                z.write(os.path.join(gerbers, f), f)
    print(f"fabrication files in {fab}: {n_bom} BOM lines, {n_cpl} placements")


DOC_SETS = [
    # (file suffix, layers, extra kicad-cli options)
    ("assembly_top", "F.Fab,Edge.Cuts", ["--sp", "--ibt"]),
    ("courtyards", "F.Courtyard,B.Courtyard,Edge.Cuts", ["--ibt"]),
    ("user_layers", "User.Drawings,User.Comments,User.Eco1,User.Eco2,Edge.Cuts", ["--ibt"]),
]


def documentation(path, board_dir):
    """PDFs, renders and a 3D model for reading the board without KiCad. Nothing
    here goes to the factory."""
    name = os.path.splitext(os.path.basename(path))[0]
    docs = os.path.join(board_dir, "docs")
    shutil.rmtree(docs, ignore_errors=True)
    os.makedirs(docs)
    for suffix, layers, extra in DOC_SETS:
        run([KICAD_CLI, "pcb", "export", "pdf", "-l", layers, "--mode-single", *extra,
             "-o", os.path.join(docs, f"{name}_{suffix}.pdf"), path], capture_output=True)
    every = gerber_layers(path) + ",F.Fab,B.Fab,F.Courtyard,B.Courtyard,User.Drawings,User.Comments"
    tmp = tempfile.mkdtemp(prefix="gos_pdf_")      # multipage mode writes <board>.pdf into a folder
    run([KICAD_CLI, "pcb", "export", "pdf", "-l", every, "--cl", "Edge.Cuts", "--mode-multipage", "--ibt",
         "-o", tmp + os.sep, path], capture_output=True)
    shutil.move(os.path.join(tmp, name + ".pdf"), os.path.join(docs, f"{name}_all_layers.pdf"))
    for side in ("top", "bottom"):
        run([KICAD_CLI, "pcb", "render", "--side", side, "--width", "1600", "--height", "1600",
             "-o", os.path.join(docs, f"{name}_render_{side}.png"), path], capture_output=True)
    run([KICAD_CLI, "pcb", "export", "step", "--force", "--drill-origin", "--subst-models",
         "-o", os.path.join(docs, f"{name}.step"), path], capture_output=True)
    print("documentation in", docs)


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
    if "--fab-only" in sys.argv:           # board already routed: check it and write the outputs
        counts = drc(path, os.path.join(tempfile.mkdtemp(prefix="gos_drc_"), "drc.json"))
        if any(v for k, v in counts.items() if k != "router_made"):
            raise SystemExit("DRC not clean; fabrication files not written")
        fabrication(path, board_dir)
        documentation(path, board_dir)
        return
    # Freerouting sometimes leaves a connection unrouted, and 2.0.1 occasionally
    # writes an empty session. Each attempt starts again from the unrouted board,
    # with a different pass limit.
    pristine = tempfile.mkdtemp(prefix="gos_unrouted_")
    stem = os.path.splitext(path)[0]
    for ext in (".kicad_pcb", ".kicad_pro"):
        shutil.copy(stem + ext, pristine)
    unrouted = os.path.join(pristine, os.path.basename(path))
    for attempt in range(1, ATTEMPTS + 1):
        print(f"attempt {attempt} of {ATTEMPTS}")
        # a different pass limit per attempt: the same limit tends to repeat the same result
        limit = [passes, max(10, passes // 2), passes * 3 // 2, max(10, passes * 3 // 4)][(attempt - 1) % 4]
        try:
            board = autoroute(unrouted, limit)
        except RouteFailed as e:
            print(" ", e)
            counts = None
            continue
        drop_single_layer_vias(board)
        add_ground_pour(board, fill=False)
        if len(copper_layers(board)) > 2:
            stitch_ground(board)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        stats(board)
        board.Save(path)
        counts = drc(path, os.path.join(tempfile.mkdtemp(prefix="gos_drc_"), "drc.json"))
        rule_problem = counts["schematic_parity"] or counts["violations"] > counts["router_made"]
        if rule_problem or not (counts["unconnected_items"] or counts["router_made"]):
            break                          # clean, or a rule problem rerouting will not fix
    else:
        if counts is None:
            raise SystemExit(f"Freerouting failed {ATTEMPTS} times")
    if any(v for k, v in counts.items() if k != "router_made"):
        raise SystemExit("DRC not clean; fabrication files not written")
    fabrication(path, board_dir)
    documentation(path, board_dir)


if __name__ == "__main__":
    main()
