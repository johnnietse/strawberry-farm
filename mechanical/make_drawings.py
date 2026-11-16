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


def sheet(key: str, cfg: dict, tmp: str):
    scad = cfg["scad"]
    # overall size of the closed enclosure, from the exported model
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for key, cfg in ENCLOSURES.items():
            sheet(key, cfg, tmp)


if __name__ == "__main__":
    main()
