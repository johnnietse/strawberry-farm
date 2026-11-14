#!/usr/bin/env python3
"""G.O.S. sensor node rev 3 schematic generator (KiCad 9).

    python generate_schematics.py            regenerate all schematic files
    python generate_schematics.py --verify   regenerate, then check the result with kicad-cli:
                                             ERC, netlist vs. the nets declared here,
                                             and symbol pin numbers vs. footprint pads

Every connection is declared once, in build(), as "pin -> net name". Pin numbers and
positions come from the KiCad stock symbol libraries, never from a hand-typed table.
A part with a pin that is neither given a net nor listed as no-connect is an error.

Paths can be overridden with KICAD9_SYMBOL_DIR, KICAD9_FOOTPRINT_DIR and KICAD_CLI.
"""
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD = r"C:\Program Files\KiCad\9.0"
SYMDIR = os.environ.get("KICAD9_SYMBOL_DIR", KICAD + r"\share\kicad\symbols")
FPDIR = os.environ.get("KICAD9_FOOTPRINT_DIR", KICAD + r"\share\kicad\footprints")
KICAD_CLI = os.environ.get("KICAD_CLI", KICAD + r"\bin\kicad-cli.exe")

PROJECT = "gos_sensor_node"
REV = "3.1"
ROOT_UUID = "c897bbcf-82b3-4b94-b14c-2b8219114053"
GENERATOR = "gos_sensor_node_generator"

# ---------------------------------------------------------------- design values
# Change these, rerun, rerun --verify. Sources are in HARDWARE.md.
R_ISET = "1.8k 1%"    # BQ24074 fast charge: I = 890 / R  -> 494 mA (allowed 590R..8.9k)
R_ILIM = "3.0k 1%"    # BQ24074 input limit when EN2=1,EN1=0: I = 1525 / R -> 508 mA. Must be fitted.
R_TMR = "68k"         # BQ24074 safety timer: 10 * R[k] * 48 s -> 9.1 h (allowed 18k..72k)
R_VBAT_DIV = "2.2M 1%"  # battery sense divider, each leg; ~1 uA at 4.2 V

# ---------------------------------------------------------------- s-expressions
TOK = re.compile(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()"]+')


def parse(text):
    stack, cur = [], []
    for t in TOK.findall(text):
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t)
    return cur[0]


def dump(node, ind=0):
    if isinstance(node, str):
        return node
    flat = "(" + " ".join(dump(c) for c in node) + ")"
    if len(flat) <= 110:
        return flat
    pad = "\t" * (ind + 1)
    out, i = "(", 0
    head = []
    while i < len(node) and isinstance(node[i], str):
        head.append(node[i])
        i += 1
    out += " ".join(head)
    for c in node[i:]:
        out += "\n" + pad + dump(c, ind + 1)
    return out + "\n" + "\t" * ind + ")"


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def unq(s):
    if s.startswith('"'):
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def kids(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def n(v):
    s = "%.4f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def rnd(v):
    return round(v + 0.0, 4)


def uid(*key):
    return str(uuid.uuid5(uuid.UUID(ROOT_UUID), "/".join(str(k) for k in key)))


FONT = "(effects (font (size 1.27 1.27))%s)"


def effects(just=None, hide=False):
    extra = ""
    if just:
        extra += " (justify %s)" % just
    if hide:
        extra += " (hide yes)"
    return FONT % extra


# ---------------------------------------------------------------- project symbols
def box_symbol(name, ref, fp, ds, desc, kw, fpf, hw, top, bottom, pins):
    """Rectangle symbol. pins: (number, name, type, side L/R/T/B, position)."""
    def prop(k, v, x, y, hide=True, just=None):
        return "(property %s %s (at %s %s 0) %s)" % (q(k), q(v), n(x), n(y), effects(just, hide))
    out = ["(symbol %s (exclude_from_sim no) (in_bom yes) (on_board yes)" % q(name),
           prop("Reference", ref, -hw, top + 1.27, False, "left"),
           prop("Value", name, -hw, bottom - 1.27, False, "left"),
           prop("Footprint", fp, 0, 0), prop("Datasheet", ds, 0, 0), prop("Description", desc, 0, 0),
           prop("ki_keywords", kw, 0, 0), prop("ki_fp_filters", fpf, 0, 0),
           "(symbol %s (rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default))"
           " (fill (type background))))" % (q(name + "_0_1"), n(-hw), n(top), n(hw), n(bottom)),
           "(symbol %s" % q(name + "_1_1")]
    for num, pname, etype, side, pos in pins:
        x, y, ang = {"L": (-hw - 2.54, pos, 0), "R": (hw + 2.54, pos, 180),
                     "T": (pos, top + 2.54, 270), "B": (pos, bottom - 2.54, 90)}[side]
        out.append("(pin %s line (at %s %s %d) (length 2.54) (name %s %s) (number %s %s))"
                   % (etype, n(x), n(y), ang, q(pname), FONT % "", q(num), FONT % ""))
    out.append(") (embedded_fonts no))")
    return "\n".join(out)


def project_library():
    """Symbols KiCad 9 does not ship. Pin numbers are from the manufacturer datasheets."""
    tps = box_symbol(
        "TPS62740DSS", "U", "Package_SON:WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65",
        "https://www.ti.com/lit/ds/symlink/tps62740.pdf",
        "360 nA Iq step-down converter, 300 mA, 1.8 V to 3.3 V selectable output, WSON-12 (DSS)",
        "buck ultra low power", "WSON*1EP*3x2mm*P0.5mm*", 10.16, 10.16, -10.16,
        [("1", "VIN", "power_in", "L", 7.62), ("12", "EN", "input", "L", 5.08),
         ("4", "CTRL", "input", "L", 2.54), ("11", "VSEL1", "input", "L", 0),
         ("10", "VSEL2", "input", "L", -2.54), ("9", "VSEL3", "input", "L", -5.08),
         ("8", "VSEL4", "input", "L", -7.62),
         ("2", "SW", "output", "R", 7.62), ("5", "VOUT", "power_in", "R", 2.54),
         ("6", "LOAD", "power_out", "R", -2.54), ("7", "PG", "open_collector", "R", -7.62),
         ("3", "GND", "power_in", "B", -2.54), ("13", "EP", "passive", "B", 2.54)])
    fet = box_symbol(
        "FS8205A", "Q", "Package_SO:TSSOP-8_4.4x3mm_P0.65mm",
        "https://atta.szlcsc.com/upload/public/pdf/source/20140228/1457706997167.pdf",
        "Dual N-channel MOSFET, common drain, 20 V, 6 A, 25 mOhm at 4.5 V, TSSOP-8",
        "dual nmos battery protection", "TSSOP*4.4x3mm*P0.65mm*", 7.62, 5.08, -5.08,
        [("2", "S1", "passive", "L", 2.54), ("3", "S1", "passive", "L", 0),
         ("4", "G1", "input", "L", -2.54),
         ("7", "S2", "passive", "R", 2.54), ("6", "S2", "passive", "R", 0),
         ("5", "G2", "input", "R", -2.54),
         ("1", "D12", "passive", "T", -2.54), ("8", "D12", "passive", "T", 2.54)])
    return ('(kicad_symbol_lib (version 20241209) (generator "%s") (generator_version "9.0")\n%s\n%s\n)\n'
            % (GENERATOR, tps, fet))


# ---------------------------------------------------------------- symbol libraries
class Libs:
    def __init__(self):
        self.cache = {"gos": self._index(parse(project_library()))}

    @staticmethod
    def _index(tree):
        return {unq(c[1]): c for c in kids(tree, "symbol")}

    def lib(self, name):
        if name not in self.cache:
            with open(os.path.join(SYMDIR, name + ".kicad_sym"), encoding="utf-8") as f:
                self.cache[name] = self._index(parse(f.read()))
        return self.cache[name]

    def _flat(self, lib, name):
        node = self.lib(lib)[name]
        ext = kids(node, "extends")
        if not ext:
            return copy.deepcopy(node)
        base = self._flat(lib, unq(ext[0][1]))
        bname = unq(base[1])
        for c in kids(base, "symbol"):
            c[1] = q(name + unq(c[1])[len(bname):])
        for p in kids(node, "property"):
            old = [c for c in kids(base, "property") if c[1] == p[1]]
            if old:
                base[base.index(old[0])] = copy.deepcopy(p)
            else:
                last = max(i for i, c in enumerate(base) if isinstance(c, list) and c[0] == "property")
                base.insert(last + 1, copy.deepcopy(p))
        base[1] = q(name)
        return base

    def get(self, lib_id):
        lib, name = lib_id.split(":")
        node = self._flat(lib, name)
        node[1] = q(lib_id)
        return node


class Pin:
    def __init__(self, p):
        at = kids(p, "at")[0]
        self.type = p[1]
        self.num = unq(kids(p, "number")[0][1])
        self.name = unq(kids(p, "name")[0][1])
        self.x, self.y, self.ang = float(at[1]), float(at[2]), int(float(at[3]))
        self.len = float(kids(p, "length")[0][1])


def sym_pins(node):
    return [Pin(p) for u in kids(node, "symbol") for p in kids(u, "pin")]


def sym_prop(node, name):
    for p in kids(node, "property"):
        if unq(p[1]) == name:
            return unq(p[2])
    return ""


def sym_flag(node, name, default="yes"):
    f = kids(node, name)
    return f[0][1] if f else default


# ---------------------------------------------------------------- schematic model
LIBS = Libs()
POWER = {"GND": "power:GND", "+3V3": "power:+3V3", "VBUS": "power:VBUS"}
OUT = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # pin angle -> outward direction (y down)

NETS = {}          # net -> {(ref, pin)}
NET_SHEETS = {}    # net -> {sheet key}
NOCONNECT = set()  # (ref, pin)
PARTS = {}         # ref -> (lib_id, footprint, [pin numbers])
COUNTER = {}


def next_ref(prefix):
    COUNTER[prefix] = COUNTER.get(prefix, 0) + 1
    return "%s%d" % (prefix, COUNTER[prefix])


class Sheet:
    def __init__(self, key, name, filename, sheet_uuid, paper, title):
        self.key, self.name, self.filename, self.sheet_uuid = key, name, filename, sheet_uuid
        self.paper, self.title = paper, title
        self.items, self.used, self.attach, self.points, self.stubs = [], {}, [], {}, []
        self.path = "/%s/%s" % (ROOT_UUID, sheet_uuid) if sheet_uuid else "/" + ROOT_UUID

    # ---- low level
    def mark(self, x, y, net):
        k = (rnd(x), rnd(y))
        if self.points.setdefault(k, net) != net:
            raise SystemExit("%s: nets %s and %s meet at %s" % (self.name, self.points[k], net, k))

    def wire(self, x1, y1, x2, y2, net):
        self.stubs.append((rnd(x1), rnd(y1), rnd(x2), rnd(y2), net))
        self.items.append("(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))"
                          % (n(x1), n(y1), n(x2), n(y2), q(uid(self.key, "w", n(x1), n(y1), n(x2), n(y2)))))

    def text(self, s, x, y, size=1.27):
        self.items.append("(text %s (exclude_from_sim no) (at %s %s 0) (effects (font (size %s %s))"
                          " (justify left top)) (uuid %s))" % (q(s), n(x), n(y), n(size), n(size),
                                                               q(uid(self.key, "t", n(x), n(y)))))

    def instance(self, lib_id, ref, value, x, y, rot, props, pin_nums, node):
        out = ["(symbol (lib_id %s) (at %s %s %d) (unit 1) (exclude_from_sim %s) (in_bom %s) (on_board %s)"
               " (dnp no) (uuid %s)" % (q(lib_id), n(x), n(y), rot, sym_flag(node, "exclude_from_sim", "no"),
                                        sym_flag(node, "in_bom"), sym_flag(node, "on_board"),
                                        q(uid(self.key, ref)))]
        for name, val, px, py, ang, just, hide in props:
            out.append("(property %s %s (at %s %s %d) %s)" % (q(name), q(val), n(px), n(py), ang,
                                                             effects(just, hide)))
        for num in pin_nums:
            out.append("(pin %s (uuid %s))" % (q(num), q(uid(self.key, ref, "pin", num))))
        out.append("(instances (project %s (path %s (reference %s) (unit 1)))))"
                   % (q(PROJECT), q(self.path), q(ref)))
        self.items.append("\n".join(out))

    # ---- parts
    def part(self, ref, lib_id, x, y, value, fp, nets, nc=(), stub=None, stubs=None, **fields):
        node = LIBS.get(lib_id)
        self.used[lib_id] = node
        pins = sym_pins(node)
        assigned = {}

        def targets(key):
            hit = [p for p in pins if p.num == key] or [p for p in pins if p.name == key]
            if not hit:
                raise SystemExit("%s (%s): no pin %r" % (ref, lib_id, key))
            return hit
        for key, net in nets.items():
            for p in targets(key):
                if assigned.setdefault(p.num, net) != net:
                    raise SystemExit("%s pin %s given two nets" % (ref, p.num))
        for key in nc:
            for p in targets(key):
                if assigned.setdefault(p.num, None) is not None:
                    raise SystemExit("%s pin %s is both connected and no-connect" % (ref, p.num))
        missing = [p.num + "/" + p.name for p in pins if p.num not in assigned]
        if missing:
            raise SystemExit("%s (%s): unassigned pins %s" % (ref, lib_id, missing))
        if ref in PARTS:
            raise SystemExit("duplicate reference " + ref)
        PARTS[ref] = (lib_id, fp, [p.num for p in pins])

        default_stub = 0 if len(pins) == 2 else 2.54
        groups = {}
        for p in pins:
            pos = (rnd(x + p.x), rnd(y - p.y))
            net = assigned[p.num]
            length = (stubs or {}).get(p.num, (stubs or {}).get(p.name, default_stub if stub is None else stub))
            if pos in groups and groups[pos][1] != net:
                raise SystemExit("%s: stacked pins at %s on different nets" % (ref, pos))
            groups[pos] = (OUT[p.ang], net, length, p.num)
            if net is None:
                NOCONNECT.add((ref, p.num))
            else:
                NETS.setdefault(net, set()).add((ref, p.num))
                NET_SHEETS.setdefault(net, set()).add(self.key)
        for (px, py), (d, net, length, num) in groups.items():
            if net is None:
                self.mark(px, py, "no-connect %s.%s" % (ref, num))
                self.items.append("(no_connect (at %s %s) (uuid %s))" % (n(px), n(py), q(uid(self.key, ref, "nc", num))))
                continue
            ex, ey = px + d[0] * length, py + d[1] * length
            self.mark(px, py, net)
            if length:
                self.wire(px, py, ex, ey, net)
                self.mark(ex, ey, net)
            self.attach.append((ex, ey, net, d))

        # field placement
        left = [p.x + p.len for p in pins if p.ang == 0]
        top = [p.y - p.len for p in pins if p.ang == 270]
        bottom = [p.y + p.len for p in pins if p.ang == 90]
        xs, ys = [p.x for p in pins] or [0], [p.y for p in pins] or [0]
        if len(pins) == 2 and all(p.x == 0 for p in pins):
            rpos, vpos, just = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27), "left"
        elif len(pins) <= 2:
            rpos, vpos, just = (x, y - 5.08), (x, y + 3.81), None
            if len(pins) == 1:
                rpos, vpos, just = (x + 2.54, y - 2.54), (x + 2.54, y), "left"
        else:
            bx = min(left) if left else min(xs)
            by_top = max(top) if top else max(ys) + 2.54
            by_bot = min(bottom) if bottom else min(ys) - 2.54
            rpos, vpos, just = (x + bx, y - by_top - 1.27), (x + bx, y - by_bot + 1.27), "left"
        vjust = just
        if bottom and len(pins) > 2:   # keep the value text clear of pins leaving the bottom edge
            vpos, vjust = (x + min(p.x for p in pins if p.ang == 90) - 1.9, vpos[1]), "right"
        props = [("Reference", ref, rpos[0], rpos[1], 0, just, False),
                 ("Value", value, vpos[0], vpos[1], 0, vjust, False),
                 ("Footprint", fp, x, y, 0, None, True),
                 ("Datasheet", fields.pop("Datasheet", sym_prop(node, "Datasheet")), x, y, 0, None, True),
                 ("Description", fields.pop("Description", sym_prop(node, "Description")), x, y, 0, None, True)]
        props += [(k, v, x, y, 0, None, True) for k, v in fields.items()]
        self.instance(lib_id, ref, value, x, y, 0, props, [p.num for p in pins], node)
        return ref

    def R(self, value, a, b, x, y, **kw):
        return self.part(next_ref("R"), "Device:R", x, y, value, "Resistor_SMD:R_0603_1608Metric",
                         {"1": a, "2": b}, **kw)

    def C(self, value, a, b, x, y, fp="Capacitor_SMD:C_0603_1608Metric", **kw):
        return self.part(next_ref("C"), "Device:C", x, y, value, fp, {"1": a, "2": b}, **kw)

    def C10u(self, a, b, x, y):
        return self.C("10uF 16V X5R", a, b, x, y, fp="Capacitor_SMD:C_0805_2012Metric")

    def flag(self, net, x, y):
        ref = next_ref("#FLG")
        node = LIBS.get("power:PWR_FLAG")
        self.used["power:PWR_FLAG"] = node
        self.instance("power:PWR_FLAG", ref, "PWR_FLAG", x, y, 0,
                      [("Reference", ref, x, y - 1.9, 0, None, True),
                       ("Value", "PWR_FLAG", x, y - 5.08, 0, None, False),
                       ("Footprint", "", x, y, 0, None, True), ("Datasheet", "~", x, y, 0, None, True),
                       ("Description", sym_prop(node, "Description"), x, y, 0, None, True)], ["1"], node)
        self.mark(x, y, net)
        self.wire(x, y, x, y + 2.54, net)
        self.mark(x, y + 2.54, net)
        self.attach.append((x, y + 2.54, net, (0, 1)))
        NET_SHEETS.setdefault(net, set()).add(self.key)

    # ---- output
    def render_attachments(self):
        for x, y, net, d in self.attach:
            if net in POWER:
                lib_id = POWER[net]
                node = LIBS.get(lib_id)
                self.used[lib_id] = node
                ref = next_ref("#PWR")
                if net == "GND":
                    rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
                else:
                    rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
                just = {(-1, 0): "right", (1, 0): "left"}.get(d)
                vx, vy = x + d[0] * 3.81, y + d[1] * 4.3
                self.instance(lib_id, ref, net, x, y, rot,
                              [("Reference", ref, x, y, 0, None, True),
                               ("Value", net, vx, vy, 0, just, net == "GND"),
                               ("Footprint", "", x, y, 0, None, True), ("Datasheet", "", x, y, 0, None, True),
                               ("Description", sym_prop(node, "Description"), x, y, 0, None, True)],
                              ["1"], node)
                continue
            ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
            right = ang in (180, 270)
            if len(NET_SHEETS[net]) > 1:
                self.items.append(
                    "(global_label %s (shape passive) (at %s %s %d) %s (uuid %s)"
                    " (property \"Intersheetrefs\" \"${INTERSHEET_REFS}\" (at 0 0 0) %s))"
                    % (q(net), n(x), n(y), ang, effects("right" if right else "left"),
                       q(uid(self.key, "g", net, n(x), n(y))), effects(None, True)))
            else:
                self.items.append("(label %s (at %s %s %d) %s (uuid %s))"
                                  % (q(net), n(x), n(y), ang, effects("right bottom" if right else "left bottom"),
                                     q(uid(self.key, "l", net, n(x), n(y)))))

    def check_geometry(self):
        for x1, y1, x2, y2, net in self.stubs:
            for (px, py), other in self.points.items():
                if other != net and min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2):
                    raise SystemExit("%s: %s wire crosses a %s point at %s" % (self.name, net, other, (px, py)))

    def write(self, extra=""):
        self.render_attachments()
        self.check_geometry()
        libs = "\n".join(dump(self.used[k], 2) for k in sorted(self.used))
        file_uuid = ROOT_UUID if not self.sheet_uuid else uid("file", self.key)
        body = ("(kicad_sch (version 20250114) (generator %s) (generator_version \"9.0\") (uuid %s) (paper %s)\n"
                "(title_block (title %s) (rev %s) (company \"Queen's University ePOWER Lab\")"
                " (comment 1 \"Generated by generate_schematics.py - edit that file, not this one\"))\n"
                "(lib_symbols\n%s\n)\n%s\n%s(embedded_fonts no))\n"
                % (q(GENERATOR), q(file_uuid), q(self.paper), q(self.title), q(REV), libs,
                   "\n".join(self.items), extra))
        with open(os.path.join(HERE, self.filename), "w", encoding="utf-8", newline="\n") as f:
            f.write(body)


# ---------------------------------------------------------------- the design
def build():
    power = Sheet("power", "Power", "power.kicad_sch", "e4cf0f50-5583-4471-a71d-bf2f85d44f31", "A3",
                  "Power: USB charger, 3.3 V buck, cell protection")
    mcu = Sheet("mcu", "MCU", "MCU.kicad_sch", "4cf87c83-fa01-4d12-9c1c-c6c5074a6016", "A4",
                "MCU: Raytac MDBT50Q-1MV2 (nRF52840)")
    sens = Sheet("sensors", "Sensors", "sensors.kicad_sch", "87bf3c30-a1e6-40d0-a09a-250d6d07ca80", "A4",
                 "Sensors: SHT40, TSL2591")
    conn = Sheet("connectors", "Connectors", "connectors.kicad_sch", "8aa840d5-f7bd-4929-a259-30ad40fabe7f",
                 "A3", "Connectors: USB-C, SWD, I2C, LED board, test points")

    # ---------------- power
    s = power
    s.text("USB-C 5 V -> BQ24074 (charger + power path, VSYS = 4.4 V on USB, VBAT on battery)"
           " -> TPS62740 (3.3 V, all four VSEL high)\n"
           "USB500 mode: EN2 = GND, EN1 high only while VBUS is present (no battery drain through the EN pull-down).\n"
           "Charge 494 mA (ISET 1.8k), safety timer 9.1 h (TMR 68k), termination 10 % (ITERM open).\n"
           "TH1 sits beside J5: it senses board temperature next to the cell, not the cell itself. Without a thermistor fit a fixed 10k.", 25.4, 20.32)
    s.part("U1", "Battery_Management:BQ24074RGT", 101.6, 81.28, "BQ24074RGT",
           "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
           {"13": "VBUS", "OUT": "VSYS", "BAT": "VBAT", "VSS": "GND", "4": "GND", "5": "GND",
            "6": "CHG_EN1", "14": "CHG_TMR", "12": "CHG_ILIM", "16": "CHG_ISET", "1": "CHG_TS",
            "7": "PGOOD_N", "9": "CHG_N"}, nc=["15"], MPN="BQ24074RGTR", Manufacturer="Texas Instruments")
    y = 137.16
    s.C("1uF 25V X7R", "VBUS", "GND", 40.64, y)
    s.R("100k", "VBUS", "CHG_EN1", 58.42, y)
    s.R(R_TMR, "CHG_TMR", "GND", 76.2, y)
    s.R(R_ILIM, "CHG_ILIM", "GND", 93.98, y)
    s.R(R_ISET, "CHG_ISET", "GND", 111.76, y)
    s.part("TH1", "Device:Thermistor_NTC", 129.54, y, "NTC 10k", "Resistor_SMD:R_0603_1608Metric",
           {"1": "CHG_TS", "2": "GND"}, Description="NTC thermistor 10k at 25 C, B 3380 K, 0603")
    s.C10u("VSYS", "GND", 147.32, y)
    s.C10u("VBAT", "GND", 165.1, y)
    y = 172.72
    s.R("100k", "+3V3", "PGOOD_N", 40.64, y)
    s.R("100k", "+3V3", "CHG_N", 58.42, y)
    s.R("1k", "+3V3", "CHG_LED_A", 76.2, y)
    s.part("D1", "Device:LED", 104.14, y, "LED amber (charging)", "LED_SMD:LED_0603_1608Metric",
           {"2": "CHG_LED_A", "1": "CHG_N"})

    s.part("U2", "gos:TPS62740DSS", 279.4, 81.28, "TPS62740DSS", "Package_SON:WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65",
           {"VIN": "VSYS", "EN": "VSYS", "CTRL": "GND", "VSEL1": "VSYS", "VSEL2": "VSYS", "VSEL3": "VSYS",
            "VSEL4": "VSYS", "SW": "BUCK_SW", "VOUT": "+3V3", "3": "GND", "13": "GND"},
           nc=["LOAD", "PG"], MPN="TPS62740DSSR", Manufacturer="Texas Instruments")
    s.C10u("VSYS", "GND", 243.84, 137.16)
    s.part("L1", "Device:L", 261.62, 137.16, "2.2uH", "Inductor_SMD:L_Coilcraft_LPS3314",
           {"1": "BUCK_SW", "2": "+3V3"}, Manufacturer="Coilcraft",
           Description="Shielded inductor 2.2 uH, Coilcraft LPS3314 series, Isat above 0.5 A")
    s.C10u("+3V3", "GND", 279.4, 137.16)

    s.text("Cell protection. BAT_N is the cell negative, NOT system GND: the FS8205A sits between them.\n"
           "DW01A trips: overcharge 4.30 V, overdischarge 2.40 V (release 3.0 V), overcurrent 150 mV across both FETs (about 2.5 A).\n"
           "The 18650 sits in the enclosure cradle and plugs into J5 (pin 1 = positive). Q2 blocks a reversed lead.\n"
           "After connecting a cell, plug USB in once to wake the DW01A.", 25.4, 195.58)
    y = 223.52
    s.part("J5", "Connector_Generic:Conn_01x02", 48.26, y, "Battery JST-PH",
           "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
           {"1": "BAT_P", "2": "BAT_N"}, stub=2.54, MPN="S2B-PH-K-S", Manufacturer="JST",
           Description="Battery lead connector, pin 1 = cell positive. The 18650 sits in the enclosure cradle.")
    s.part("Q2", "Transistor_FET:AO3401A", 83.82, y, "AO3401A", "Package_TO_SOT_SMD:SOT-23",
           {"1": "BAT_N", "2": "VBAT", "3": "BAT_P"}, MPN="AO3401A", Manufacturer="Alpha & Omega")
    s.R("100R", "VBAT", "DW_VCC", 116.84, y)
    s.C("100nF", "DW_VCC", "BAT_N", 134.62, y)
    s.part("U3", "Battery_Management:DW01A", 175.26, y, "DW01A", "Package_TO_SOT_SMD:SOT-23-6",
           {"5": "DW_VCC", "6": "BAT_N", "1": "DW_OD", "3": "DW_OC", "2": "DW_CS"}, nc=["4"], MPN="DW01A")
    s.R("1k", "DW_CS", "GND", 215.9, y)
    s.part("Q1", "gos:FS8205A", 254, y, "FS8205A", "Package_SO:TSSOP-8_4.4x3mm_P0.65mm",
           {"S1": "BAT_N", "G1": "DW_OD", "S2": "GND", "G2": "DW_OC", "D12": "FET_D"},
           MPN="FS8205A", Manufacturer="Fortune Semiconductor")
    s.R(R_VBAT_DIV, "VBAT", "VBAT_SENSE", 325.12, 177.8)
    s.R(R_VBAT_DIV, "VBAT_SENSE", "GND", 325.12, 215.9)
    s.C("100nF", "VBAT_SENSE", "GND", 350.52, 215.9)
    for i, net in enumerate(["GND", "VBUS", "+3V3", "BAT_N", "DW_VCC"]):
        s.flag(net, 325.12 + 15.24 * i, 132.08)

    # ---------------- MCU
    s = mcu
    s.text("VDD and VDDH tied to 3.3 V, DCCH open: Raytac reference circuit 8.3 (REG0 off, supply below 3.6 V).\n"
           "Module pins 3-14 and 50-61 are low-frequency only (below 10 kHz): no SPI, I2C, UART or PWM there.\n"
           "Y1: 32.768 kHz, 9 pF load, with 12 pF caps as in the Raytac reference.\n"
           "Keep copper out of the module antenna area (Raytac spec section 2.3).", 25.4, 165.1)
    used = {"GND": "GND", "VDD": "+3V3", "VDDH": "+3V3", "VBUS": "VBUS",
            "P0.00": "XL1", "P0.01": "XL2", "P0.26": "I2C_SDA", "P0.27": "I2C_SCL", "P0.15": "TSL_INT",
            "P0.13": "PWM_BLUE", "P0.14": "PWM_RED", "P0.06": "UART_TX", "P0.08": "UART_RX",
            "P0.02": "VBAT_SENSE", "P0.28": "PGOOD_N", "P0.29": "CHG_N", "P0.18": "NRESET",
            "SWDIO": "SWDIO", "SWDCLK": "SWDCLK", "P1.00": "SWO", "D+": "USB_DP", "D-": "USB_DN",
            "P0.17": "LED_STAT_N", "P0.24": "BTN_USER"}
    names = {p.name for p in sym_pins(LIBS.get("RF_Module:MDBT50Q-1MV2"))}
    s.part("U4", "RF_Module:MDBT50Q-1MV2", 149.86, 104.14, "MDBT50Q-1MV2", "RF_Module:Raytac_MDBT50Q",
           used, nc=sorted(names - set(used)), stubs={"VDDH": 7.62, "VBUS": 12.7},
           MPN="MDBT50Q-1MV2", Manufacturer="Raytac")
    s.part("Y1", "Device:Crystal", 50.8, 60.96, "32.768kHz 9pF", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm",
           {"1": "XL1", "2": "XL2"}, stub=2.54, MPN="ABS07-32.768KHZ-9-T", Manufacturer="Abracon",
           Description="32.768 kHz crystal, 9 pF load, +/-20 ppm, ESR 70 kOhm max, 3.2 x 1.5 mm")
    s.C("12pF C0G", "XL1", "GND", 40.64, 83.82)
    s.C("12pF C0G", "XL2", "GND", 60.96, 83.82)
    s.C10u("+3V3", "GND", 40.64, 119.38)
    s.C("100nF", "+3V3", "GND", 58.42, 119.38)
    s.C10u("VBUS", "GND", 76.2, 119.38)
    sw = dict(MPN="B3U-1000P", Manufacturer="Omron")
    s.part("SW1", "Switch:SW_Push", 226.06, 60.96, "RESET", "Button_Switch_SMD:SW_SPST_B3U-1000P",
           {"1": "NRESET", "2": "GND"}, stub=2.54, **sw)
    s.part("SW2", "Switch:SW_Push", 226.06, 83.82, "USER", "Button_Switch_SMD:SW_SPST_B3U-1000P",
           {"1": "BTN_USER", "2": "GND"}, stub=2.54, **sw)
    s.R("1k", "+3V3", "LED_STAT_A", 215.9, 119.38)
    s.part("D2", "Device:LED", 243.84, 119.38, "LED green (status)", "LED_SMD:LED_0603_1608Metric",
           {"2": "LED_STAT_A", "1": "LED_STAT_N"})

    # ---------------- sensors
    s = sens
    s.text("I2C addresses: SHT40 0x44, TSL2591 0x29. Place U5 away from the charger and buck (self-heating).\n"
           "U6 needs a clear view of the light: no part taller than it nearby. U6 needs at least 2.7 V and is rated -30 to 70 C.\n"
           "No copper under U5 other than its four pads (Sensirion land pattern); its centre pad stays unsoldered.", 25.4, 25.4)
    s.part("U5", "Sensor_Humidity:SHT4x", 76.2, 88.9, "SHT40-AD1B",
           "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
           {"SDA": "I2C_SDA", "SCL": "I2C_SCL", "VDD": "+3V3", "VSS": "GND"},
           MPN="SHT40-AD1B-R2", Manufacturer="Sensirion")
    s.C("100nF", "+3V3", "GND", 106.68, 88.9)
    s.part("U6", "Sensor_Optical:TSL25911FN", 165.1, 88.9, "TSL25911FN", "OptoDevice:AMS_TSL25911FN",
           {"SCL": "I2C_SCL", "SDA": "I2C_SDA", "INT": "TSL_INT", "VDD": "+3V3", "GND": "GND"}, nc=["NC"],
           MPN="TSL25911FN", Manufacturer="ams OSRAM")
    s.C("1uF 25V X7R", "+3V3", "GND", 215.9, 88.9)
    s.R("4.7k", "+3V3", "I2C_SDA", 76.2, 139.7)
    s.R("4.7k", "+3V3", "I2C_SCL", 93.98, 139.7)
    s.R("100k", "+3V3", "TSL_INT", 111.76, 139.7)

    # ---------------- connectors
    s = conn
    s.text("J1: USB 2.0 device. 5.1k on each CC pin asks the host for 5 V.\n"
           "J4 carries only the two PWM signals to the separate LED driver board, which has its own 5 to 12 V supply\n"
           "(AL8860 needs at least 4.5 V; do not power it from this board). 100k pull-downs hold the signals low during reset.\n"
           "J2: standard 10-pin 1.27 mm Cortex debug header.", 25.4, 20.32)
    s.part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", 60.96, 86.36, "USB-C USB4105-GF-A",
           "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
           {"VBUS": "VBUS_CONN", "GND": "GND", "SHIELD": "GND", "CC1": "CC1", "CC2": "CC2",
            "D+": "USB_CONN_DP", "D-": "USB_CONN_DN"}, nc=["SBU1", "SBU2"],
           MPN="USB4105-GF-A", Manufacturer="GCT")
    s.part("F1", "Device:Polyfuse_Small", 119.38, 60.96, "PTC 0.75A 6V", "Fuse:Fuse_1206_3216Metric",
           {"1": "VBUS_CONN", "2": "VBUS"})
    s.R("5.1k", "CC1", "GND", 137.16, 86.36)
    s.R("5.1k", "CC2", "GND", 154.94, 86.36)
    s.part("U7", "Power_Protection:USBLC6-2SC6", 124.46, 132.08, "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
           {"I/O1": "USB_CONN_DP", "I/O2": "USB_CONN_DN", "5": "VBUS", "2": "GND"},
           MPN="USBLC6-2SC6", Manufacturer="STMicroelectronics")
    s.R("27R", "USB_CONN_DP", "USB_DP", 160.02, 132.08)
    s.R("27R", "USB_CONN_DN", "USB_DN", 177.8, 132.08)
    s.part("J2", "Connector:Conn_ARM_JTAG_SWD_10", 238.76, 86.36, "SWD 2x5 1.27mm",
           "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
           {"1": "+3V3", "3": "GND", "5": "GND", "9": "GND", "2": "SWDIO", "4": "SWDCLK", "6": "SWO",
            "10": "NRESET"}, nc=["7", "8"])
    s.part("J3", "Connector_Generic:Conn_01x04", 317.5, 71.12, "I2C", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
           {"1": "+3V3", "2": "GND", "3": "I2C_SDA", "4": "I2C_SCL"}, stubs={"1": 7.62})
    s.part("J4", "Connector_Generic:Conn_01x04", 317.5, 121.92, "LED board PWM", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
           {"1": "GND", "2": "PWM_BLUE_C", "3": "PWM_RED_C", "4": "GND"})
    s.R("100R", "PWM_BLUE", "PWM_BLUE_C", 259.08, 142.24)
    s.R("100R", "PWM_RED", "PWM_RED_C", 276.86, 142.24)
    s.R("100k", "PWM_BLUE_C", "GND", 259.08, 180.34)
    s.R("100k", "PWM_RED_C", "GND", 276.86, 180.34)
    for i, net in enumerate(["+3V3", "VSYS", "VBAT", "GND", "UART_TX", "UART_RX", "VBUS"]):
        s.part("TP%d" % (i + 1), "Connector:TestPoint", 45.72 + 17.78 * i, 220.98, net,
               "TestPoint:TestPoint_Pad_D1.0mm", {"1": net})
    for i in range(4):
        s.part("H%d" % (i + 1), "Mechanical:MountingHole", 45.72 + 20.32 * i, 256.54, "M2.5",
               "MountingHole:MountingHole_2.7mm_M2.5", {})

    for net, pins in NETS.items():
        if len(pins) < 2:
            raise SystemExit("net %s has a single pin %s" % (net, pins))
    return [power, mcu, sens, conn]


def write_all():
    sheets = build()
    for sh in sheets:
        sh.write()
    root = Sheet("root", "Root", PROJECT + ".kicad_sch", None, "A4", "G.O.S. sensor node")
    root.text("G.O.S. sensor node rev %s\n\n"
              "18650 cell + USB-C charging, nRF52840 module (Thread / BLE), SHT40 and TSL2591 over I2C.\n"
              "LED drivers live on a separate, separately powered board; J4 gives it the two PWM signals.\n"
              "The 18650 sits in the enclosure and plugs into J5. LoRa and GNSS are not fitted.\n\n"
              "Sheets share nets through global labels and power symbols; the sheet symbols below carry no pins.\n"
              "Pin map, power tree and datasheet sources: HARDWARE.md" % REV, 25.4, 25.4, 1.524)
    for i, sh in enumerate(sheets):
        x, y, w, h = 25.4 + 60.96 * i, 91.44, 45.72, 20.32
        root.items.append(
            "(sheet (at %s %s) (size %s %s) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n"
            "(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid %s)\n"
            "(property \"Sheetname\" %s (at %s %s 0) %s)\n(property \"Sheetfile\" %s (at %s %s 0) %s)\n"
            "(instances (project %s (path %s (page %s)))))"
            % (n(x), n(y), n(w), n(h), q(sh.sheet_uuid), q(sh.name), n(x), n(y - 0.7), effects("left bottom"),
               q(sh.filename), n(x), n(y + h + 0.6), effects("left top"), q(PROJECT), q("/" + ROOT_UUID),
               q(i + 2)))
    root.write('(sheet_instances (path "/" (page "1")))\n')

    os.makedirs(os.path.join(HERE, "libraries"), exist_ok=True)
    with open(os.path.join(HERE, "libraries", "gos.kicad_sym"), "w", encoding="utf-8", newline="\n") as f:
        f.write(project_library())
    with open(os.path.join(HERE, "sym-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "gos")(type "KiCad")'
                '(uri "${KIPRJMOD}/libraries/gos.kicad_sym")(options "")(descr "G.O.S. sensor node symbols"))\n)\n')
    with open(os.path.join(HERE, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write("(fp_lib_table\n  (version 7)\n)\n")
    pro = os.path.join(HERE, PROJECT + ".kicad_pro")
    with open(pro, encoding="utf-8") as f:
        data = json.load(f)
    data["sheets"] = [[ROOT_UUID, "Root"]] + [[sh.sheet_uuid, sh.name] for sh in sheets]
    with open(pro, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote %d sheets, %d parts, %d nets" % (len(sheets) + 1, len(PARTS), len(NETS)))


# ---------------------------------------------------------------- verification
def verify():
    bad = 0
    root = os.path.join(HERE, PROJECT + ".kicad_sch")
    tmp = tempfile.mkdtemp(prefix="gos_verify_")

    # 1. footprint pads cover every symbol pin
    for ref, (lib_id, fp, pins) in sorted(PARTS.items()):
        lib, name = fp.split(":")
        path = os.path.join(FPDIR, lib + ".pretty", name + ".kicad_mod")
        if not os.path.isfile(path):
            print("FOOTPRINT MISSING %s: %s" % (ref, fp))
            bad += 1
            continue
        with open(path, encoding="utf-8") as f:
            pads = set(re.findall(r'\(pad "([^"]*)"', f.read()))
        lost = [p for p in pins if p not in pads]
        if lost:
            print("PAD MISMATCH %s (%s): symbol pins %s have no pad in %s" % (ref, lib_id, lost, fp))
            bad += 1
    print("footprints: %d parts checked" % len(PARTS))

    # 2. netlist exported by KiCad equals the nets declared in build()
    net_file = os.path.join(tmp, "netlist.net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net_file, root],
                   check=True, capture_output=True)
    with open(net_file, encoding="utf-8") as f:
        tree = parse(f.read())
    actual, floating = {}, set()
    for net in kids(kids(tree, "nets")[0], "net"):
        name = unq(kids(net, "name")[0][1])
        nodes = frozenset((unq(kids(nd, "ref")[0][1]), unq(kids(nd, "pin")[0][1])) for nd in kids(net, "node"))
        if name.startswith("unconnected-"):
            floating |= nodes
        else:
            actual[nodes] = name.split("/")[-1]
    expected = {frozenset(v): k for k, v in NETS.items()}
    for nodes, name in sorted(expected.items(), key=lambda kv: kv[1]):
        if nodes not in actual:
            print("NET MISMATCH %s: declared %s" % (name, sorted(nodes)))
            bad += 1
        elif actual[nodes] != name:
            print("NET NAME %s exported as %s" % (name, actual[nodes]))
            bad += 1
    for nodes, name in actual.items():
        if nodes not in expected:
            print("NET UNEXPECTED %s: %s" % (name, sorted(nodes)))
            bad += 1
    if floating != NOCONNECT:
        print("NO-CONNECT MISMATCH: only in netlist %s, only declared %s"
              % (sorted(floating - NOCONNECT), sorted(NOCONNECT - floating)))
        bad += 1
    print("netlist: %d nets declared, %d exported, %d no-connect pins" % (len(expected), len(actual), len(floating)))

    # 3. ERC, every severity
    erc_file = os.path.join(tmp, "erc.json")
    subprocess.run([KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", erc_file, root],
                   capture_output=True)
    with open(erc_file, encoding="utf-8") as f:
        erc = json.load(f)
    count = 0
    for sh in erc.get("sheets", []):
        for v in sh.get("violations", []):
            count += 1
            where = "; ".join(i.get("description", "") for i in v.get("items", []))
            print("ERC %s [%s] %s %s: %s" % (v.get("severity"), v.get("type"), sh.get("path"),
                                             v.get("description"), where))
    print("ERC: %d violations" % count)
    bad += count
    print("VERIFY " + ("FAILED (%d problems)" % bad if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    write_all()
    if "--verify" in sys.argv:
        sys.exit(verify())
