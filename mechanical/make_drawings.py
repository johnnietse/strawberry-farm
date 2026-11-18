#!/usr/bin/env python3
"""
Engineering drawing sheets for both enclosures (docs/images/drawings/*.png):

  - third-angle orthographic views (top, front, right side) of the closed enclosure, with
    overall dimensions measured from the exported model (not typed in by hand);
  - an exploded isometric view with numbered balloons;
  - a parts list (bill of materials) and a title block.

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" fit_check.py   # board models first
    python make_drawings.py

Needs OpenSCAD (OPENSCAD environment variable or the default install path), numpy, Pillow
and matplotlib. Renders go to a temporary folder.
"""
from __future__ import annotations

import datetime
import os
import subprocess
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "images", "drawings")
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.exe")
INK, INK2, LINE = "#1f1f1e", "#5f5e58", "#2b2b29"

# OpenSCAD gimbal camera rotations (rx, ry, rz) for the orthographic views
# (checked by rendering: rx 90 / rz 0 shows the -Y wall with the USB cut-out, rz 90 the +X wall)
VIEWS = {"top": (0, 0, 0), "front": (90, 0, 0), "right": (90, 0, 90)}

ENCLOSURES = {
    "sensor_node": {
        "scad": "enclosure_gen.scad",
        "wall": 2.5, "flange_y": 0,
        "title": "G.O.S. SENSOR NODE ENCLOSURE",
        "drawing_no": "GOS-MECH-001",
        "exploded": {"lid_lift": 170, "pcb_lift": 60, "cell_lift": 60},
        "iso_camera": (0, 0, 80, 62, 0, 32, 640),
        "parts": [
            ("1", "Base", "ASA, printed (print/sensor_enclosure_base.stl)", 1, "base"),
            ("2", "Lid with light tube", "ASA, black, printed (print/sensor_enclosure_lid.stl)", 1, "lid"),
            ("3", "Sensor node PCB rev 3.1", "pcbs/gos_sensor_node, JLCPCB assembled", 1, "pcb"),
            ("4", "18650 Li-ion cell", "Adafruit 1781 or equal (ordering.md)", 1, "cell"),
            ("5", "Self-tapping screw M2.5 x 6", "board to posts", 4, None),
            ("6", "Self-tapping screw M3 x 10", "lid to bosses", 4, None),
            ("7", "Cable gland M12", "LED cable (ordering.md)", 1, None),
            ("8", "Clear disc 16 x 1.5 mm", "polycarbonate, light window, glued", 1, None),
            ("9", "USB-C dust plug", "silicone", 1, None),
        ],
    },
    "led_driver": {
        "scad": "led_enclosure.scad",
        "wall": 2.5, "flange_y": 10,
        "title": "G.O.S. LED DRIVER ENCLOSURE",
        "drawing_no": "GOS-MECH-002",
        "exploded": {"lid_lift": 80, "pcb_lift": 40},
        "iso_camera": (0, 0, 40, 62, 0, 32, 360),
        "parts": [
            ("1", "Base with mounting flanges", "ASA, printed (print/led_enclosure_base.stl)", 1, "base"),
            ("2", "Lid", "ASA, printed (print/led_enclosure_lid.stl)", 1, "lid"),
            ("3", "LED driver PCB rev 1.0", "pcbs/led_driver, JLCPCB assembled", 1, "pcb"),
            ("4", "Self-tapping screw M3 x 6", "board to posts", 4, None),
            ("5", "Self-tapping screw M3 x 10", "lid to bosses", 4, None),
        ],
    },
}


def openscad(args):
    r = subprocess.run([OPENSCAD, *args], cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])


def defines(d: dict) -> list:
    out = []
    for k, v in d.items():
        out += ["-D", f'{k}="{v}"' if isinstance(v, str) else f"{k}={str(v).lower() if isinstance(v, bool) else v}"]
    return out


def stl_bbox(path: str) -> np.ndarray:
    pts = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("vertex"):
                pts.append([float(x) for x in line.split()[1:4]])
    a = np.array(pts)
    return np.array([a.min(axis=0), a.max(axis=0)])


def crop(path: str):
    """Crop a render to the object (pixels that differ from the background colour)."""
    img = np.asarray(Image.open(path).convert("RGB")).astype(int)
    bg = img[2, 2]
    mask = np.abs(img - bg).sum(axis=2) > 24
    ys, xs = np.nonzero(mask)
    img = img.copy()
    img[~mask] = 255          # white background, like the sheet
    return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8), (xs.min(), ys.min(), xs.max(), ys.max())


def dim_h(ax, x0, x1, y, text, above=True):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="<|-|>", mutation_scale=8, color=LINE, lw=0.8))
    ax.text((x0 + x1) / 2, y + (1.5 if above else -1.5), text, ha="center", va="bottom" if above else "top",
            fontsize=8, color=INK)


def dim_v(ax, y0, y1, x, text):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="<|-|>", mutation_scale=8, color=LINE, lw=0.8))
    ax.text(x - 1.5, (y0 + y1) / 2, text, ha="right", va="center", rotation=90, fontsize=8, color=INK)


def ortho_axis(ax, img, w, h, title, wdim, hdim):
    """Place a cropped orthographic render at true scale (mm) and dimension it."""
    ax.imshow(img, extent=[0, w, 0, h], interpolation="lanczos")
    pad = 0.18 * max(w, h)
    ax.set_xlim(-pad, w + pad * 0.5)
    ax.set_ylim(-pad * 0.6, h + pad * 0.7)
    ax.set_aspect("equal")
    ax.axis("off")
    for x in (0, w):
        ax.plot([x, x], [h + 1, h + pad * 0.45], color=INK2, lw=0.5)
    for y in (0, h):
        ax.plot([-1, -pad * 0.55], [y, y], color=INK2, lw=0.5)
    dim_h(ax, 0, w, h + pad * 0.38, wdim)
    dim_v(ax, 0, h, -pad * 0.48, hdim)
    ax.text(w / 2, -pad * 0.35, title, ha="center", va="top", fontsize=9, fontweight="bold", color=INK)


def render_model(key: str, cfg: dict, tmp: str) -> dict:
    """Overall size of the closed enclosure (from the exported model) and its three views."""
    scad = cfg["scad"]
    stl = os.path.join(tmp, f"{key}_closed.stl")
    openscad(["-o", stl, *defines({"show_pcb": False, "lid_alpha": 1}), scad])
    (x0, y0, z0), (x1, y1, z1) = stl_bbox(stl)
    W, L, H = x1 - x0, y1 - y0, z1 - z0

    views = {}
    # front and right views: only that wall (sliced off the model), so its openings show through
    slices = {"top": {},
              "front": {"wall_view": "front", "slab_y": y0 + cfg["flange_y"] + cfg["wall"] + 1.5},
              "right": {"wall_view": "right", "slab_x": x1 - cfg["wall"] - 1.5}}
    for name, (rx, ry, rz) in VIEWS.items():
        png = os.path.join(tmp, f"{key}_{name}.png")
        # full CGAL render: the preview would frame the slicing box instead of the wall
        openscad(["--render", "-o", png, "--imgsize=1600,1600", "--projection=ortho", "--colorscheme=Tomorrow",
                  f"--camera=0,0,0,{rx},{ry},{rz},500", "--viewall", "--autocenter",
                  *defines({"show_pcb": False, "lid_alpha": 1, **slices[name]}), scad])
        img = crop(png)[0].astype(float)
        # engineering greys: the render's surface colour becomes mid grey, cut faces (holes,
        # recesses) light grey, background white
        lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
        white = (img > 250).all(axis=2)
        grey = np.clip(60 + (lum - 60) * 1.4, 60, 230)   # same mapping for every view
        grey[white] = 255
        views[name] = np.repeat(grey[..., None], 3, axis=2).astype(np.uint8)
    return {"views": views, "W": W, "L": L, "H": H}


def render_iso(key: str, cfg: dict, tmp: str, camera=None, exploded=True):
    """Isometric render cropped to the object; with exploded=True also the anchor pixel of
    every ballooned part (each part rendered alone with the same camera)."""
    scad = cfg["scad"]
    tx, ty, tz, rx, ry, rz, dist = camera or cfg["iso_camera"]
    cam = f"--camera={tx},{ty},{tz},{rx},{ry},{rz},{dist}"
    tag = f"{key}_{dist}_{'x' if exploded else 'c'}"
    base_defs = {"show_pcb": exploded, "lid_alpha": 1, **(cfg["exploded"] if exploded else {})}
    iso_png = os.path.join(tmp, f"{tag}_iso.png")
    openscad(["-o", iso_png, "--imgsize=1500,1500", "--projection=ortho", "--colorscheme=Tomorrow", cam,
              *defines(base_defs), scad])
    iso_img, (cx0, cy0, cx1, cy1) = crop(iso_png)
    centroids = {}
    if exploded:
        for num, _, _, _, only in cfg["parts"]:
            if not only:
                continue
            p = os.path.join(tmp, f"{tag}_iso_{only}.png")
            openscad(["-o", p, "--imgsize=1500,1500", "--projection=ortho", "--colorscheme=Tomorrow", cam,
                      *defines({**base_defs, "only": only}), scad])
            img = np.asarray(Image.open(p).convert("RGB")).astype(int)
            mask = np.abs(img - img[2, 2]).sum(axis=2) > 24
            ys, xs = np.nonzero(mask)
            k = np.argmin((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)
            centroids[only] = (xs[k] - cx0, ys[k] - cy0)
    return iso_img, centroids


def balloon(ax, px, py, bx, by, num, r):
    ax.annotate("", xy=(px, py), xytext=(bx, by),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=0.8, shrinkA=13, shrinkB=0))
    ax.add_patch(Circle((bx, by), r, fill=True, facecolor="white", edgecolor=LINE, lw=1.0, zorder=5))
    ax.text(bx, by, num, ha="center", va="center", fontsize=10, fontweight="bold", color=INK, zorder=6)


def frame(fig):
    fig.add_artist(Rectangle((0.012, 0.012), 0.976, 0.976, transform=fig.transFigure, fill=False, lw=1.6, color=LINE))
    fig.add_artist(Rectangle((0.02, 0.02), 0.96, 0.96, transform=fig.transFigure, fill=False, lw=0.6, color=LINE))


def table(ax, rows, cols, widths, title, fontsize=8, scale=1.25):
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="upper center", cellLoc="left", colLoc="left", colWidths=widths)
    t.auto_set_font_size(False)
    t.set_fontsize(fontsize)
    t.scale(1, scale)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(LINE)
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_text_props(fontweight="bold")
    ax.set_title(title, fontsize=8.5, loc="left", color=INK)


def title_block(fig, title, number, sheet_no, scale, source, overall, material="ASA (PETG acceptable, not PLA)"):
    a_tb = fig.add_axes([0.03, 0.025, 0.95, 0.095])
    a_tb.axis("off")
    tb = a_tb.table(cellText=[
        ["TITLE", title, "DRAWING NO.", number, "SHEET", sheet_no],
        ["MATERIAL", material, "UNITS", "mm", "SCALE", scale],
        ["PROJECTION", "third angle", "TOLERANCE", "+/-0.3 unless noted (FDM)", "DATE",
         datetime.date.today().isoformat()],
        ["SOURCE", source, "OVERALL", overall, "REV", "A"],
    ], loc="center", cellLoc="left", colWidths=[0.08, 0.3, 0.09, 0.2, 0.06, 0.17])
    tb.auto_set_font_size(False)
    tb.set_fontsize(8)
    tb.scale(1, 1.15)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor(LINE)
        cell.set_linewidth(0.6)
        if c in (0, 2, 4):
            cell.set_text_props(fontweight="bold", color=INK2)


def sheet(key: str, cfg: dict, tmp: str):
    scad = cfg["scad"]
    m = render_model(key, cfg, tmp)
    views, W, L, H = m["views"], m["W"], m["L"], m["H"]

    # exploded isometric: whole assembly, then each part alone with the same camera
    tx, ty, tz, rx, ry, rz, dist = cfg["iso_camera"]
    cam = f"--camera={tx},{ty},{tz},{rx},{ry},{rz},{dist}"
    base_defs = {"show_pcb": True, "lid_alpha": 1, **cfg["exploded"]}
    iso_png = os.path.join(tmp, f"{key}_iso.png")
    openscad(["-o", iso_png, "--imgsize=1500,1500", "--projection=ortho", "--colorscheme=Tomorrow", cam,
              *defines(base_defs), scad])
    iso_full = np.asarray(Image.open(iso_png).convert("RGB"))
    iso_img, (cx0, cy0, cx1, cy1) = crop(iso_png)
    centroids = {}
    for num, _, _, _, only in cfg["parts"]:
        if not only:
            continue
        p = os.path.join(tmp, f"{key}_iso_{only}.png")
        openscad(["-o", p, "--imgsize=1500,1500", "--projection=ortho", "--colorscheme=Tomorrow", cam,
                  *defines({**base_defs, "only": only}), scad])
        img = np.asarray(Image.open(p).convert("RGB")).astype(int)
        mask = np.abs(img - img[2, 2]).sum(axis=2) > 24
        ys, xs = np.nonzero(mask)
        # anchor on a visible pixel of the part near its centre
        k = np.argmin((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)
        centroids[num] = (xs[k] - cx0, ys[k] - cy0)

    # ---------------- sheet (A3 landscape proportions) ----------------
    fig = plt.figure(figsize=(16.54, 11.69), dpi=110, facecolor="white")
    fig.add_artist(Rectangle((0.012, 0.012), 0.976, 0.976, transform=fig.transFigure, fill=False, lw=1.6, color=LINE))
    fig.add_artist(Rectangle((0.02, 0.02), 0.96, 0.96, transform=fig.transFigure, fill=False, lw=0.6, color=LINE))

    # third-angle layout: top view above the front view, right view to the right of the front view
    a_top = fig.add_axes([0.03, 0.55, 0.3, 0.40])
    a_front = fig.add_axes([0.03, 0.20, 0.3, 0.33])
    a_right = fig.add_axes([0.31, 0.20, 0.25, 0.33])
    ortho_axis(a_top, views["top"], W, L, "TOP VIEW", f"{W:.1f}", f"{L:.1f}")
    ortho_axis(a_front, views["front"], W, H, "FRONT VIEW", f"{W:.1f}", f"{H:.1f}")
    ortho_axis(a_right, views["right"], L, H, "RIGHT SIDE VIEW", f"{L:.1f}", f"{H:.1f}")

    a_iso = fig.add_axes([0.56, 0.36, 0.42, 0.60])
    a_iso.imshow(iso_img)
    a_iso.axis("off")
    hgt, wid = iso_img.shape[:2]
    a_iso.set_xlim(-0.12 * wid, 1.12 * wid)
    a_iso.set_ylim(1.05 * hgt, -0.05 * hgt)
    a_iso.text(wid / 2, 1.03 * hgt, "EXPLODED ISOMETRIC VIEW (not to scale)", ha="center", fontsize=9,
               fontweight="bold", color=INK)
    for num, (px, py) in centroids.items():
        side = -1 if px < wid / 2 else 1
        bx = (-0.07 * wid) if side < 0 else (1.07 * wid)
        by = py
        a_iso.annotate("", xy=(px, py), xytext=(bx, by),
                       arrowprops=dict(arrowstyle="-|>", color=LINE, lw=0.8, shrinkA=13, shrinkB=0))
        a_iso.add_patch(Circle((bx, by), 0.035 * wid, fill=True, facecolor="white", edgecolor=LINE, lw=1.0))
        a_iso.text(bx, by, num, ha="center", va="center", fontsize=10, fontweight="bold", color=INK)

    # parts list
    a_bom = fig.add_axes([0.56, 0.135, 0.42, 0.21])
    a_bom.axis("off")
    rows = [[n, name, qty, note] for n, name, note, qty, _ in cfg["parts"]]
    t = a_bom.table(cellText=rows, colLabels=["ITEM", "PART", "QTY", "MATERIAL / SOURCE / NOTE"], loc="upper center",
                    cellLoc="left", colLoc="left", colWidths=[0.07, 0.34, 0.06, 0.53])
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 1.25)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(LINE)
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_text_props(fontweight="bold")
    a_bom.set_title("PARTS LIST (items without a balloon are not drawn)", fontsize=8.5, loc="left", color=INK)

    # title block
    a_tb = fig.add_axes([0.03, 0.025, 0.95, 0.095])
    a_tb.axis("off")
    tb = a_tb.table(cellText=[
        ["TITLE", cfg["title"], "DRAWING NO.", cfg["drawing_no"], "SHEET", "1 OF 1"],
        ["MATERIAL", "ASA (PETG acceptable, not PLA)", "UNITS", "mm", "SCALE", "views to scale, iso NTS"],
        ["PROJECTION", "third angle", "TOLERANCE", "+/-0.3 unless noted (FDM)", "DATE",
         datetime.date.today().isoformat()],
        ["SOURCE", f"mechanical/{scad} (OpenSCAD), generated", "OVERALL", f"{W:.1f} x {L:.1f} x {H:.1f}", "REV", "A"],
    ], loc="center", cellLoc="left", colWidths=[0.08, 0.3, 0.09, 0.2, 0.06, 0.17])
    tb.auto_set_font_size(False)
    tb.set_fontsize(8)
    tb.scale(1, 1.15)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor(LINE)
        cell.set_linewidth(0.6)
        if c in (0, 2, 4):
            cell.set_text_props(fontweight="bold", color=INK2)
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{key}_enclosure_drawing.png")
    fig.savefig(out, dpi=110, facecolor="white")
    plt.close(fig)
    print(f"{out}: {W:.1f} x {L:.1f} x {H:.1f} mm")
    return m


# ---------------------------------------------------------------------------------------------
# System assembly drawing (GOS-MECH-003): the light node and the LED driver it drives, the way
# they are put together and installed. Sheet 1: both enclosures at the same true scale (1:2 on
# A3) and one exploded view; sheet 2: installation layout, cables and assembly sequence.
# ---------------------------------------------------------------------------------------------
SYSTEM_PARTS = [
    ("1", "Sensor node base", "ASA, print/sensor_enclosure_base.stl", 1),
    ("2", "Sensor node lid with light tube", "ASA, black, print/sensor_enclosure_lid.stl", 1),
    ("3", "Sensor node PCB rev 3.1", "light node firmware (router.conf)", 1),
    ("4", "18650 Li-ion cell", "Adafruit 1781 or equal", 1),
    ("5", "LED driver base with flanges", "ASA, print/led_enclosure_base.stl", 1),
    ("6", "LED driver lid", "ASA, print/led_enclosure_lid.stl", 1),
    ("7", "LED driver PCB rev 1.0", "pcbs/led_driver", 1),
    ("8", "Control cable, 4-wire", "2.54 mm 4-pin female housing both ends, pin 1 to pin 1", 1),
    ("9", "Cable gland M12", "LAPP S1507 SKINTOP SL-M 12x1.5, sensor right wall", 1),
    ("10", "Self-tapping screws", "4 x M2.5x6 + 4 x M3x10 (sensor); 4 x M3x6 + 4 x M3x10 (LED)", 16),
    ("11", "Clear disc 16 x 1.5 mm", "polycarbonate, glued into the sensor lid", 1),
]
SYSTEM_BALLOONS = {"sensor_node": {"base": "1", "lid": "2", "pcb": "3", "cell": "4"},
                   "led_driver": {"base": "5", "lid": "6", "pcb": "7"}}
ISO_ROT = (62, 0, 32)
SYSTEM_EXPLODE = {"sensor_node": {"lid_lift": 100, "pcb_lift": 40, "cell_lift": 40},
                  "led_driver": {"lid_lift": 60, "pcb_lift": 30}}
SYSTEM_TARGET_Z = {"sensor_node": 85, "led_driver": 50}


def place(ax, img, x, y, w, h):
    ax.imshow(img, extent=[x, x + w, y, y + h], interpolation="lanczos")


def ext_h(ax, x0, x1, y_from, y_dim, text):
    for x in (x0, x1):
        ax.plot([x, x], [y_from, y_dim + np.sign(y_dim - y_from) * 2], color=INK2, lw=0.5)
    ax.add_patch(FancyArrowPatch((x0, y_dim), (x1, y_dim), arrowstyle="<|-|>", mutation_scale=7, color=LINE, lw=0.7))
    above = y_dim > y_from
    ax.text((x0 + x1) / 2, y_dim + (1.2 if above else -1.2), text, ha="center",
            va="bottom" if above else "top", fontsize=7.5, color=INK)


def ext_v(ax, y0, y1, x_from, x_dim, text):
    for y in (y0, y1):
        ax.plot([x_from, x_dim + np.sign(x_dim - x_from) * 2], [y, y], color=INK2, lw=0.5)
    ax.add_patch(FancyArrowPatch((x_dim, y0), (x_dim, y1), arrowstyle="<|-|>", mutation_scale=7, color=LINE, lw=0.7))
    left = x_dim < x_from
    ax.text(x_dim + (-1.2 if left else 1.2), (y0 + y1) / 2, text, ha="right" if left else "left", va="center",
            rotation=90, fontsize=7.5, color=INK)


def multiview_group(ax, m, x0, label):
    """Third-angle group for one enclosure at true size (mm): top above front, right beside front."""
    W, L, H, v = m["W"], m["L"], m["H"], m["views"]
    g = 22
    place(ax, v["front"], x0, 0, W, H)
    place(ax, v["top"], x0, H + g, W, L)
    place(ax, v["right"], x0 + W + g, 0, L, H)
    ext_h(ax, x0, x0 + W, 0, -10, f"{W:.1f}")
    ext_v(ax, 0, H, x0, x0 - 9, f"{H:.1f}")
    ext_h(ax, x0, x0 + W, H + g + L, H + g + L + 9, f"{W:.1f}")
    ext_v(ax, H + g, H + g + L, x0, x0 - 9, f"{L:.1f}")
    ext_h(ax, x0 + W + g, x0 + W + g + L, 0, -10, f"{L:.1f}")
    ext_v(ax, 0, H, x0 + W + g + L, x0 + W + g + L + 9, f"{H:.1f}")
    for text, cx, cy in (("FRONT", x0 + W / 2, -19), ("TOP", x0 + W / 2, H + g + L + 21),
                         ("RIGHT SIDE", x0 + W + g + L / 2, -19)):
        ax.text(cx, cy, text, ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
    ax.text(x0 + W + g, H + g + L + 18, label, ha="left", va="center", fontsize=9, fontweight="bold", color=INK)
    return x0 + W + g + L


def system_sheet_1(models, tmp):
    fig = plt.figure(figsize=(16.54, 11.69), dpi=110, facecolor="white")   # A3: 420 x 297 mm
    frame(fig)

    # multiview at exactly 1:2 on an A3 print: data range (mm) = 2 x the axis size on paper
    box = [0.03, 0.40, 0.60, 0.56]
    ax = fig.add_axes(box)
    rx_mm, ry_mm = 2 * box[2] * 420, 2 * box[3] * 297
    ax.set_xlim(-30, -30 + rx_mm)
    ax.set_ylim(-45, -45 + ry_mm)
    ax.set_aspect("equal")
    ax.axis("off")
    end = multiview_group(ax, models["sensor_node"], 0, "LIGHT NODE: SENSOR NODE ENCLOSURE (ITEMS 1-4)")
    multiview_group(ax, models["led_driver"], end + 45, "LED DRIVER ENCLOSURE (ITEMS 5-7)")
    ax.text(-28, -45 + ry_mm - 4, "ORTHOGRAPHIC VIEWS, BOTH UNITS AT THE SAME SCALE (1:2 ON A3)",
            fontsize=9, fontweight="bold", color=INK, va="top")

    # one exploded view: same camera rotation and distance for both units, so the same scale
    isos, cents = {}, {}
    for key, cfg in ENCLOSURES.items():
        # smaller lifts than the single sheets, so both units fit one frame at one scale
        c = {**cfg, "exploded": SYSTEM_EXPLODE[key]}
        isos[key], cents[key] = render_iso(key, c, tmp, camera=(0, 0, SYSTEM_TARGET_Z[key], *ISO_ROT, 700))
    a, b = isos["sensor_node"], isos["led_driver"]
    gap = int(0.55 * a.shape[1])
    hh = max(a.shape[0], b.shape[0])
    canvas = np.full((hh, a.shape[1] + gap + b.shape[1], 3), 255, np.uint8)
    ya, yb = (hh - a.shape[0]) // 2, hh - b.shape[0] - int(0.08 * hh)
    canvas[ya:ya + a.shape[0], :a.shape[1]] = a
    xb = a.shape[1] + gap
    canvas[yb:yb + b.shape[0], xb:xb + b.shape[1]] = b
    pos = {("sensor_node", k): (x, y + ya) for k, (x, y) in cents["sensor_node"].items()}
    pos.update({("led_driver", k): (x + xb, y + yb) for k, (x, y) in cents["led_driver"].items()})

    a_iso = fig.add_axes([0.64, 0.40, 0.34, 0.56])
    a_iso.imshow(canvas)
    a_iso.axis("off")
    H_, W_ = canvas.shape[:2]
    a_iso.set_xlim(-0.12 * W_, 1.12 * W_)
    a_iso.set_ylim(1.06 * H_, -0.04 * H_)
    r = 0.025 * W_
    for (key, part), (px, py) in pos.items():
        bx = -0.07 * W_ if key == "sensor_node" else 1.07 * W_
        balloon(a_iso, px, py, bx, py, SYSTEM_BALLOONS[key][part], r)
    # control cable (item 8), drawn schematically from the sensor right wall to the LED driver slot
    p0 = (a.shape[1] * 0.98, pos[("sensor_node", "pcb")][1])
    p1 = (xb + b.shape[1] * 0.35, yb + b.shape[0] * 0.85)
    t = np.linspace(0, 1, 60)
    cx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * (p0[0] + gap * 0.6) + t ** 2 * p1[0]
    cy = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * (p1[1] + 0.15 * H_) + t ** 2 * p1[1]
    a_iso.plot(cx, cy, color="#1f6f9f", lw=2.2, solid_capstyle="round")
    balloon(a_iso, cx[30], cy[30], cx[30], cy[30] + 0.12 * H_, "8", r)
    a_iso.text(W_ / 2, 1.04 * H_, "EXPLODED ISOMETRIC VIEW, BOTH UNITS (same scale, not to scale on paper)",
               ha="center", fontsize=8.5, fontweight="bold", color=INK)

    table(fig.add_axes([0.03, 0.135, 0.60, 0.235]), [[n, p, q, s] for n, p, s, q in SYSTEM_PARTS],
          ["ITEM", "PART", "QTY", "MATERIAL / SOURCE / NOTE"], [0.06, 0.30, 0.05, 0.59],
          "PARTS LIST (items 8 to 11 are not drawn as parts; item 8 is shown as a line)", fontsize=7.5, scale=1.12)
    a_n = fig.add_axes([0.64, 0.135, 0.34, 0.235])
    a_n.axis("off")
    notes = [
        "NOTES",
        "1. Cable 8 joins sensor node J4 to LED driver J2, pin 1 to pin 1",
        "   (GND, PWM blue, PWM red, GND). Unplugged = LEDs off.",
        "2. Sensor end: through gland 9 in the RIGHT wall. The housing does",
        "   not pass the gland seal: release the 4 pins from the housing,",
        "   thread the wires through dome nut, seal and gland body, refit",
        "   the pins in the same positions, then plug onto J4.",
        "3. LED end: housing passes the 14 x 5 mm slot in the FRONT wall;",
        "   plug onto J2. Strain relief: cable tie to the flange slot.",
        "4. Light node power: 5 V USB-C through the front-wall cut-out.",
        "5. Close both lids only after flashing and the bench test",
        "   (documentation/bring_up.md): SWD is inside.",
        "6. Installation and the other cables: sheet 2.",
    ]
    a_n.text(0.0, 1.0, "\n".join(notes), va="top", ha="left", fontsize=8, family="monospace", color=INK)

    s, l = models["sensor_node"], models["led_driver"]
    title_block(fig, "G.O.S. SYSTEM ASSEMBLY: LIGHT NODE + LED DRIVER", "GOS-MECH-003", "1 OF 2",
                "1:2 (views, A3), iso NTS", "make_drawings.py from both .scad files",
                f"{s['W']:.0f}x{s['L']:.0f}x{s['H']:.0f} + {l['W']:.1f}x{l['L']:.0f}x{l['H']:.1f}")
    out = os.path.join(OUT, "system_assembly_sheet1.png")
    fig.savefig(out, dpi=110, facecolor="white")
    plt.close(fig)
    print(out)


def system_sheet_2(tmp):
    fig = plt.figure(figsize=(16.54, 11.69), dpi=110, facecolor="white")
    frame(fig)
    icons = {k: render_iso(k, cfg, tmp, camera=(0, 0, cfg["iso_camera"][2] / 2, *ISO_ROT, 500), exploded=False)[0]
             for k, cfg in ENCLOSURES.items()}

    ax = fig.add_axes([0.03, 0.30, 0.56, 0.66])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 64)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(1, 63, "INSTALLATION LAYOUT (schematic, not to scale)", fontsize=9, fontweight="bold", color=INK, va="top")

    def icon(img, cx, y0, h):
        """Render at its own aspect ratio, centred on cx."""
        w = h * img.shape[1] / img.shape[0]
        ax.imshow(img, extent=[cx - w / 2, cx + w / 2, y0, y0 + h], zorder=3)

    def box(x, y, w, h, text, fc="white", ls="-", fs=7.5):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=LINE, lw=0.9, ls=ls))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK)

    def wire(xs, ys, label, color=LINE, ls="-", lw=1.4, at=0.5, dx=0.0, dy=1.0):
        ax.plot(xs, ys, color=color, ls=ls, lw=lw)
        i = int(at * (len(xs) - 1))
        ax.text(xs[i] + dx, ys[i] + dy, label, fontsize=7.5, color=color, fontweight="bold")

    # growth chamber
    ax.add_patch(Rectangle((2, 4), 62, 54, fill=False, edgecolor=INK2, lw=1.2, ls=(0, (6, 3))))
    ax.text(3, 56.5, "PHYTOTRON / GROWTH CHAMBER", fontsize=7.5, color=INK2)
    # light fixture with the two LED strings on a heatsink
    box(8, 46, 40, 4, "heatsink (about 2 C/W per channel)", fc="#ededeb")
    for i in range(4):
        ax.add_patch(Circle((12 + i * 4, 45), 1.1, color="#3a5fcd"))
        ax.add_patch(Circle((32 + i * 4, 45), 1.1, color="#b0303a"))
    ax.text(18, 42.2, "blue string, 4 x 448 nm", ha="center", fontsize=7, color="#3a5fcd")
    ax.text(38, 42.2, "red string, 4 x 655 nm", ha="center", fontsize=7, color="#b0303a")
    # LED driver on the fixture frame
    icon(icons["led_driver"], 56, 44, 7)
    ax.text(56, 52, "LED driver (5-7)\nflanges to fixture frame", ha="center", fontsize=7, color=INK)
    wire([50, 47, 47], [47, 47, 46.5], "", color="#3a5fcd", lw=1.0)
    wire([50.5, 49, 49], [45.5, 45.5, 45], "", color="#b0303a", lw=1.0)
    ax.text(43.5, 49, "W3, W4", fontsize=7, color=INK)
    # plants and the nodes at canopy height
    for x in (14, 24, 34, 44):
        ax.add_patch(Rectangle((x - 3, 6), 6, 6, facecolor="#8a6f4e", edgecolor=LINE, lw=0.5))
        ax.add_patch(Circle((x, 15), 3.6, facecolor="#6aa84f", edgecolor=LINE, lw=0.5))
    ax.plot([54, 54], [6, 17], color=INK2, lw=2)
    icon(icons["sensor_node"], 54, 17, 9)
    ax.text(50, 33.5, "light node (1-4), on a pole\nat canopy height (floor holes)", fontsize=7, color=INK,
            ha="right", va="bottom")
    ax.plot([7.5, 7.5], [6, 20], color=INK2, lw=2)
    icon(icons["sensor_node"], 7.5, 20, 7)
    ax.text(4, 29.5, "climate node(s), battery", fontsize=7, color=INK)
    # cables
    wire([57, 60.5, 60.5, 58], [24, 24, 45.5, 45.5], "W1", color="#1f6f9f", at=0.5, dx=0.8, dy=10)
    box(68, 47, 13, 5, "24 V adapter\nGST36U24-P1J", fs=7)
    wire([68, 60], [49, 49], "W2", color=LINE, at=0.0, dx=-5, dy=0.8)
    box(68, 18, 13, 5, "5 V USB-C\nadapter", fs=7)
    wire([68, 57], [20, 20], "W5", color=LINE, at=0.0, dx=-5, dy=0.8)
    # gateway: bought boards in a bought case
    box(70, 32, 22, 9, "Raspberry Pi 4B / 5\nofficial case (bought)\nDocker stack", fs=7)
    box(66, 35, 3.5, 3, "", fc="#d9d9d6")
    ax.text(67.7, 34.3, "nRF52840\nDongle", fontsize=6.5, color=INK, ha="center", va="top")
    wire([69.5, 70], [36.5, 36.5], "", lw=1.0)
    ax.text(81, 30.5, "W6: USB 2.0 port + extension", fontsize=7, color=INK, ha="center", va="top")
    wire([92, 97], [36.5, 36.5], "", lw=1.0)
    ax.text(93, 38, "W7\nLAN", fontsize=7, color=INK)
    # Thread radio links (2.4 GHz)
    wire([56, 66], [26, 36], "Thread (R1)", color="#7a4fa0", ls="--", lw=1.1, at=0.0, dx=-9.5, dy=4.5)
    wire([10, 50], [24, 22], "", color="#7a4fa0", ls="--", lw=1.1)

    rows = [
        ["W1", "light node J4 (gland 9)", "LED driver J2 (front slot)", "4-wire, 2.54 mm 4-pin, pin 1 to 1"],
        ["W2", "24 V adapter", "LED driver J1 (left wall)", "5.5 x 2.1 mm plug, centre +"],
        ["W3", "LED driver J3 (right wall)", "blue string, 4 in series", "Phoenix 1803578 plug, 28-16 AWG"],
        ["W4", "LED driver J4 (right wall)", "red string, 4 in series", "Phoenix 1803578 plug, 28-16 AWG"],
        ["W5", "5 V USB-C adapter", "light node USB-C (front)", "power; climate nodes: charging only"],
        ["W6", "Pi USB 2.0 port", "nRF52840 Dongle", "short USB extension, not by USB 3.0"],
        ["W7", "Pi Ethernet / Wi-Fi", "LAN", "dashboard, API, Grafana"],
        ["R1", "nodes", "Dongle", "Thread, 2.4 GHz radio, no cable"],
    ]
    table(fig.add_axes([0.61, 0.62, 0.37, 0.33]), rows, ["ID", "FROM", "TO", "CABLE / NOTE"],
          [0.06, 0.28, 0.28, 0.38], "INTERCONNECT LIST", fontsize=7.2, scale=1.3)

    steps = [
        "ASSEMBLY SEQUENCE",
        " 1 Print items 1, 2, 5, 6 in ASA (lid 2 black). Glue disc 11 in lid 2.",
        " 2 Flash each board and bench test it open (bring_up.md):",
        "   light node router.conf, climate node low_power.conf.",
        " 3 Screw the boards to their posts (M2.5x6 sensor, M3x6 LED driver).",
        " 4 Sensor node: cell 4 into the cradle; check lead polarity",
        "   (ordering.md) before plugging J5.",
        " 5 Fit gland 9; route W1 through it as in sheet 1 note 2; plug J4.",
        " 6 LED driver: W1 through the front slot onto J2; W3/W4 plugs onto",
        "   J3 (blue) and J4 (red) through the right wall.",
        " 7 Foam tape on the sensor rim; close both lids with M3x10 screws.",
        " 8 Mount: LED driver by its flanges on the fixture frame, out of",
        "   the drip zone; nodes on a pole or rail at canopy height.",
        " 9 Gateway: Pi in its case, Dongle on the extension (W6).",
        "10 Power up: Pi first, then W5, then W2. Check the dashboard.",
        "",
        "RADIO: Thread does not pass a closed metal chamber. The light",
        "node routes for the climate nodes, so only its link must reach",
        "the Dongle: place the Dongle inside, at a window or a cable port.",
    ]
    a_s = fig.add_axes([0.61, 0.135, 0.37, 0.45])
    a_s.axis("off")
    a_s.text(0, 1, "\n".join(steps), va="top", ha="left", fontsize=7.8, family="monospace", color=INK)

    a_l = fig.add_axes([0.03, 0.135, 0.56, 0.15])
    a_l.axis("off")
    legend = [
        "LEGEND  blue line: control cable W1 | black line: power and LED cables | purple dashed: Thread radio",
        "Items 1-11: parts list on sheet 1. Gateway parts (Raspberry Pi, case, power supply, Dongle, USB",
        "extension) are bought, not printed: the official case of the Pi model fits the board and its",
        "ports; the Dongle stays outside the Pi case on the extension, where the antenna is not shielded.",
        "Climate nodes use the same enclosure without cable W1 and gland 9: close the 12.2 mm gland hole",
        "with an M12 x 1.5 blanking plug so air and water do not enter there.",
    ]
    a_l.text(0, 1, "\n".join(legend), va="top", ha="left", fontsize=8, color=INK)

    title_block(fig, "G.O.S. SYSTEM: INSTALLATION AND INTERCONNECT", "GOS-MECH-003", "2 OF 2", "NTS",
                "make_drawings.py", "see sheet 1", material="see parts list, sheet 1")
    out = os.path.join(OUT, "system_assembly_sheet2.png")
    fig.savefig(out, dpi=110, facecolor="white")
    plt.close(fig)
    print(out)


def main():
    import sys
    only_system = "--system" in sys.argv
    with tempfile.TemporaryDirectory() as tmp:
        models = {}
        for key, cfg in ENCLOSURES.items():
            if "--sheet2" in sys.argv:
                continue
            if only_system:
                models[key] = render_model(key, cfg, tmp)
            else:
                models[key] = sheet(key, cfg, tmp)
        if "--sheet2" not in sys.argv:
            system_sheet_1(models, tmp)
        system_sheet_2(tmp)


if __name__ == "__main__":
    main()
