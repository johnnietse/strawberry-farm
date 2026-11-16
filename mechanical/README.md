# Enclosures

Two parametric OpenSCAD enclosures, one per board. Board positions come from files that
`fit_check.py` writes from the KiCad boards, so posts, cut-outs and windows follow the boards.

| File | Holds | Outer size |
|---|---|---|
| `enclosure_gen.scad` | sensor node + one 18650 cell | 85 x 130 x 48 mm (with lid) |
| `led_enclosure.scad` | LED driver board | 65.6 x 62 x 36 mm (with lid), plus 10 mm mounting flanges |

Print-ready STL files (base and lid of each, in print orientation): `print/`.

![Sensor node enclosure, exploded](../docs/images/sensor_enclosure_exploded.png)
![LED driver enclosure, exploded](../docs/images/led_enclosure_exploded.png)

## Engineering drawings

`make_drawings.py` makes one drawing sheet per enclosure in `docs/images/drawings/`: third-angle
orthographic views (top, front, right side) with overall dimensions measured from the exported
model, an exploded isometric view with numbered balloons, a parts list and a title block.
Run it after `fit_check.py` (which exports the board models it draws).

![Sensor node enclosure drawing](../docs/images/drawings/sensor_node_enclosure_drawing.png)
![LED driver enclosure drawing](../docs/images/drawings/led_driver_enclosure_drawing.png)

## Fit check

```
"C:\Program Files\KiCad\9.0\bin\python.exe" fit_check.py
```

1. Reads both KiCad boards and writes `pcb_layout.scad` and `led_layout.scad`.
2. Checks the fit and exits non-zero on a failure. Sensor node: posts inside the walls, USB-C
   socket face 0.3 mm inside the front wall, battery cradle behind the board, 18650 can at least
   10 mm from the antenna (35.6 mm), cradle fits, battery lead reaches, lid clearance. LED board:
   jack and LED-terminal faces at the walls, lid bosses clear of the board, lid clearance.
3. Exports each board with its parts as STL (not committed) and renders `fit_check_*.png` and
   `led_fit_*.png`.
4. Writes the print STLs in `print/`.

Last result (2026-11-15): all 12 checks pass. Rerun after any board change.

## Sensor node enclosure

| Feature | Where | Why |
|---|---|---|
| Board | four 5 mm posts, USB-C face 0.3 mm inside the front wall | cable reaches the socket through a 12 x 7 mm cut-out |
| 18650 cradle | across the back, snap-in | 35.6 mm from the module antenna: a metal can beside the antenna detunes it |
| Vents | vertical slots in both side walls, level with the SHT40 | air across the humidity sensor |
| Light window and tube | 10 mm hole in the lid over the TSL2591, a printed tube down to 3 mm above it, 16 x 1.5 mm clear polycarbonate disc glued into a recess on top | the light sensor sees outside light in a defined cone, not light reflected around inside; print the lid black |
| Cable gland | M12, right wall beside J4 | cable to the LED driver board (LAPP SKINTOP SL-M 12x1.5) |
| Lid | 3 mm with a locating lip, 4 x M3 screws into bosses | closed-cell foam tape on the rim for a dust seal |
| Floor | 2 x 4 mm mounting holes, 4 x 2 mm drain holes | pole or rail mounting; condensation drains |

## LED driver enclosure

| Feature | Where | Why |
|---|---|---|
| Board | four 4 mm posts (M3) | |
| 24 V jack | round opening in the left wall at the jack | the plug enters from outside |
| LED strings | two openings in the right wall at J3 and J4 | the Phoenix 1803578 screw plugs enter from outside |
| PWM cable | 14 x 5 mm slot in the wall beside J2 | the cable from the sensor node; a 2.54 mm housing on J2 needs about 23 mm above the board |
| Vents | slots high on both long walls | each AL8860 channel dissipates about 0.25 W |
| Mounting | flanges on the long sides with 2 x 4.5 mm slots each | screw it to the light fixture or its frame, out of the plants' drip zone |

## Material and printing

| | Choice | Why |
|---|---|---|
| Material | **ASA** | UV-stable, heat resistant to about 95 C, low moisture uptake: suits a warm, humid, lit phytotron for years |
| Acceptable | PETG | indoor, out of direct light |
| Avoid | PLA | softens near 55 C and creeps under the screws; grow lights and summer temperatures reach that |
| Sensor-node lid | black | the light tube must not glow |
| Settings | 0.2 mm layers, 4 walls, 25 % infill; base open side up, lid upside down | |

To avoid printing yourself, send the four files in `print/` to an online printing service and ask
for ASA (see `documentation/ordering.md`).

Hardware: sensor node 4 x M2.5x6 (board) and 4 x M3x10 (lid) self-tapping screws; LED driver
4 x M3x6 (board) and 4 x M3x10 (lid). Plus the cable gland, the polycarbonate disc and a USB-C
dust plug for the sensor node's USB cut-out.

## Not verified

- Nothing has been printed. Pilot holes (2.2 mm for M2.5, 2.5 mm for M3) and the cradle snap fit
  depend on the printer; adjust `post_pilot_d`, `boss_pilot_d` and the cradle opening if needed.
- Connector heights come from the manufacturer drawings (USB-C socket centre about 1.6 mm above
  the board, PJ-063AH plug centre 5.0 mm); the openings allow 1.5 to 2 mm of error.
- The light window changes what the TSL2591 reads: calibrate lux with the lid on.
- The vents and the USB cut-out mean neither enclosure is waterproof (the humidity sensor needs
  air). Keep both out of direct spray.
