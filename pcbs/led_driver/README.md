# G.O.S. LED driver board rev 1.0

Two constant-current channels for the phytotron grow light, driven by the sensor node's two
PWM outputs (sensor node J4).

The schematic is generated:

```
"C:\Program Files\KiCad\9.0\bin\python.exe" generate_schematic.py --verify
```

`--verify` checks ERC at every severity, the exported netlist against the declared nets, and
that every symbol pin has a footprint pad. Outputs: `led_driver.kicad_sch`,
`led_driver_schematic.pdf`, `led_driver_bom.csv`.

## Board

60 x 45 mm, **4 layers** (F.Cu signals and parts, In1.Cu and In2.Cu solid GND planes, B.Cu
signals; JLCPCB JLC04161H-1080 stack-up, 1.6 mm, ENIG), four M3 holes 4 mm in from the corners.
Generated, then autorouted:

```
"C:\Program Files\KiCad\9.0\bin\python.exe" generate_pcb.py
"C:\Program Files\KiCad\9.0\bin\python.exe" ..\gos_sensor_node\route_pcb.py .
```

`route_pcb.py` needs `FREEROUTING_JAR` (and `JAVA` if the default java is too old); see the sensor
node's `HARDWARE.md`, Board layout. It routes with Freerouting, adds thermal vias in each AL8860
exposed pad, pours GND on all four layers, adds ground stitching vias wherever they fit, runs DRC
with schematic parity and writes `fab/` (Gerbers, drill files, JLCPCB BOM and placement files,
upload zip) and `docs/` (assembly, courtyard, user-layer and all-layer PDFs, renders, STEP model).
Ordering: `documentation/ordering.md`.

The ground planes matter most on this board: two buck converters switch the 24 V supply, and a
plane directly under every switching loop keeps the loop area, and so the radiated noise, small.

Layout: 24 V jack on the left edge; blue channel (U1) in the top half and red (U2) in the bottom;
each channel's diode and inductor in a row from the AL8860 SW pins to its LED terminal on the right
edge; PWM header J2 on the bottom edge. Power nets (VIN, SW, SET, LEDK, GND) are 0.4 mm, signals
0.25 mm.

Current result: DRC at every severity with schematic parity: 0 violations, 0 unconnected, 0 parity
issues.

## Design choices

No requirements were given, so these are engineering defaults. Each one is a constant at the
top of `generate_schematic.py` or a single part to swap.

| Choice | Value | Why |
|---|---|---|
| Supply | 24 V DC adapter, 5.5 x 2.1 mm centre-positive plug (the jack's centre pin is 2.0 mm) | On 12 V a 3-4 LED blue string needs over 80 % switch duty; the AL8860 is specified for 25 to 75 %. On 24 V both strings sit at roughly 35 to 55 %. |
| Channels | blue 450 nm, red 660 nm | Same spectra as the rev 2 design. |
| LEDs per channel | 4 in series, off-board | About 1 W per LED. Plain FR-4 cannot shed 8 W, so the LEDs go on star (MCPCB) heatsinks wired to J3 and J4. |
| Current | 333 mA per channel | AL8860: I = 0.1 V / R_SENSE; 0.30 ohm gives 333 mA (datasheet table). Suits common 1 W horticulture LEDs. Change R_SENSE for other LEDs (1.0 A max in MSOP-8EP at 0.1 ohm, up to 1.5 A at 0.066 ohm). |
| Inductor | 100 uH (Bourns SRN6045TA-101M) | Datasheet range 33 to 100 uH. Its 47 uH example is for 1 A LEDs; at 333 mA the hysteresis band is a third as wide, and LTspice shows 47 uH switching at up to 1.27 MHz, above the 1 MHz limit, with on-times below the 500 ns needed for 4 % accuracy. 100 uH halves the frequency. Rated 0.92 A against a 0.4 A peak. |
| Dimming | sensor node PWM at 250 Hz into CTRL | Datasheet: CTRL takes 3.3 V logic directly; above 2.5 V = full current, below 0.2 V = off; best accuracy below 500 Hz. |
| Fail-safe | 1.5 kOhm pull-down on each CTRL | A floating CTRL means full brightness. The pull-down keeps the LEDs off when the cable is unplugged or the node is in reset. The datasheet does not give the CTRL pull-up, but its 80 uA maximum shutdown current bounds it: at most 80 uA x 1.5 k = 0.12 V, below the 0.2 V off threshold (LTspice, `simulation/ctrl_failsafe.cir`). 2.2 k left only 24 mV of margin. With the node driving through its 100 ohm resistor, CTRL still reaches 3.0 V (above 2.5 V = full current). |
| Protection | 1.1 A PTC fuse and SS34 series diode on the input | Overload and reversed adapter. The AL8860 has its own open-LED, shorted-LED and over-temperature protection. |

Approximate input power: 333 mA x (4 x 2.75 V blue + 4 x 2.1 V red) = about 6.5 W of LEDs, about
0.3 A from the 24 V adapter. LTspice puts each channel at 94 to 97 % efficiency. The recommended
adapter (Mean Well GST36U24-P1J, 24 V 1.5 A) has ample margin.

## Recommended LEDs and simulation

Luxeon Star SP-01-V4 (royal blue 448 nm) and SP-01-D2 (deep red 655 nm), each a LUXEON Rebel on a
20 mm star; see `documentation/ordering.md`. With their datasheet forward voltages (typical and
maximum) and a 20 to 28 V supply, LTspice (`simulation/led_channel.cir`) gives 335 to 339 mA per
string, 435 to 672 kHz switching, 32 to 68 % duty and a 392 mA inductor peak: all inside the
AL8860 and inductor limits. Mount the stars on a heatsink and use twisted pair for each string.
Do not plug or unplug an LED string while the board is powered.

## Connectors

| Ref | What | Pins |
|---|---|---|
| J1 | 24 V DC jack | centre positive |
| J2 | PWM from sensor node J4, 1x4 2.54 mm | 1 GND, 2 PWM blue, 3 PWM red, 4 GND |
| J3 | blue LED string, 2-pin 3.81 mm terminal | 1 anode (string +), 2 cathode (string -) |
| J4 | red LED string, 2-pin 3.81 mm terminal | 1 anode, 2 cathode |

Both J3 and J4 pins sit near the supply voltage, not near ground: the AL8860 switches the low
side of the string through the inductor. Do not connect either LED pin to ground or to the
enclosure.

## Verified from the Diodes AL8860 datasheet (DS39014 Rev. 8-2, April 2026)

Pinout (MSOP-8EP: SET 1, GND 2-3 and EP, CTRL 4, SW 5-6, N/C 7, VIN 8), 4.5 to 40 V input,
I = 0.1 / R_SENSE, CTRL thresholds and PWM guidance, 33 to 100 uH inductor range, 10 uF X7R
input capacitor close to VIN, 25 to 75 % recommended duty cycle.

## Not verified

- LED forward voltages come from the Luxeon Star product pages (typical and maximum), fitted to a
  simple model; other LEDs need the simulation rerun with their values.
- The Bourns SRN6045TA-101M ratings (1.33 A / 0.92 A, 0.456 ohm) were read from the JLCPCB and Mouser catalogue entries, not from the Bourns datasheet.
- The AL8860 CTRL pull-up is bounded from the datasheet's shutdown current, not measured. Confirm on
  the bench that the LEDs stay dark with J2 unplugged (`documentation/bring_up.md`).
- The switching loops (input capacitor, AL8860, diode, inductor) were placed and routed by hand; the rest is autorouted. No board has been made. Losses per channel are about 0.25 W (switch, diode, inductor, sense resistor), well inside the MSOP-8EP package; not measured.
