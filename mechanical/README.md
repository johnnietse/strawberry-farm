# Sensor node enclosure

`enclosure_gen.scad` is a parametric OpenSCAD model of the enclosure for the rev 3.1 sensor node
and one 18650 cell. Board positions come from `pcb_layout.scad`, which `fit_check.py` writes
from the KiCad board, so the posts, cut-outs and windows follow the board.

```
"C:\Program Files\KiCad\9.0\bin\python.exe" fit_check.py
```

`fit_check.py`:

1. reads `pcbs/gos_sensor_node/gos_sensor_node.kicad_pcb` and writes `pcb_layout.scad`
2. checks the fit (posts on the board holes, USB-C socket at the front wall, battery clear of the
   board and the antenna, battery lead length, lid clearance) and exits non-zero on a failure
3. exports the board with its parts (`pcb_assembly.stl`, not committed) and renders
   `fit_check_iso.png`, `fit_check_top.png` and `fit_check_section.png`

Rerun it after any board change. Last result: all checks pass.

## What changed from the rev 2 model

The rev 2 model did not fit the rev 3.1 board:

- The outer shell was built half height while the cavity was cut full height, so the box had no
  floor and the posts and battery cradle sat below it.
- The battery cradle overlapped the board area.
- The board sat in the middle of the box, about 30 mm behind the USB cut-out.
- No light reached the TSL2591.
- A side port for an external SHT4x probe that this design does not use.

The board was kept, since its size and hole pattern already matched the posts, and the enclosure
was rebuilt around it.

## Layout

| Feature | Where | Why |
|---|---|---|
| Board | on four 5 mm posts, USB-C socket face 0.3 mm inside the front wall | the cable reaches the socket through a 12 x 7 mm cut-out |
| 18650 cradle | across the back, snap-in | 35 mm from the module antenna (a metal can next to the antenna detunes it) |
| Vents | vertical slots in both side walls, level with the SHT40 | air across the humidity sensor |
| Light window | 10 mm hole in the lid over the TSL2591, recess for a 16 x 1.5 mm clear polycarbonate disc | the light sensor needs light |
| Cable gland | M12, right wall beside J4 | cable to the LED driver board |
| Lid | 3 mm with a locating lip, 4 x M3 screws into bosses | |
| Floor | 2 x 4 mm pole/rail mounting holes, 4 x 2 mm drain holes | |

## Printing

ASA for the phytotron (UV and heat resistant), PETG for prototypes. 0.2 mm layers, 4 walls, 25 %
infill. Print the base open side up and the lid upside down:

```
openscad -D 'part="base"' -o base.stl enclosure_gen.scad
openscad -D 'part="lid"' -o lid.stl enclosure_gen.scad
```

Hardware: 4 x M2.5x6 self-tapping screws (board), 4 x M3x10 self-tapping screws (lid), one M12
cable gland, one 16 mm x 1.5 mm clear polycarbonate disc (glue it into the lid recess from inside).

## Not verified

- Nothing has been printed. Post pilot holes (2.2 mm for M2.5, 2.5 mm for M3) and the snap fit of
  the cradle depend on the printer; adjust `post_pilot_d`, `boss_pilot_d` and the cradle opening
  if needed.
- The USB cut-out height assumes the socket centre is 1.6 mm above the board; the 7 mm tall
  opening allows about 1.5 mm of error either way.
- The light window changes what the TSL2591 reads: calibrate lux against a reference meter
  with the lid on.
- The side vents lower the ingress protection; there is no IP rating for this design.
