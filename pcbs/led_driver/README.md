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

60 x 45 mm, two layers, four M3 holes 4 mm in from the corners. Generated, then autorouted:

```
"C:\Program Files\KiCad\9.0in\python.exe" generate_pcb.py
"C:\Program Files\KiCad\9.0in\python.exe" ..\gos_sensor_nodeoute_pcb.py .
```

`route_pcb.py` needs `FREEROUTING_JAR` (and `JAVA` if the default java is too old); see the sensor
node's `HARDWARE.md`, Board layout. It routes with Freerouting, adds thermal vias in each AL8860
exposed pad, pours GND on both layers, runs DRC with schematic parity and writes `fab/` (Gerbers,
drill files, pick-and-place, upload zip).

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
| Supply | 24 V DC adapter, 2.1 mm centre-positive jack | On 12 V a 3-4 LED blue string needs over 80 % switch duty; the AL8860 is specified for 25 to 75 %. On 24 V both strings sit at roughly 35 to 55 %. |
| Channels | blue 450 nm, red 660 nm | Same spectra as the rev 2 design. |
| LEDs per channel | 4 in series, off-board | About 1 W per LED. Plain FR-4 cannot shed 8 W, so the LEDs go on star (MCPCB) heatsinks wired to J3 and J4. |
| Current | 333 mA per channel | AL8860: I = 0.1 V / R_SENSE; 0.30 ohm gives 333 mA (datasheet table). Suits common 1 W horticulture LEDs. Change R_SENSE for other LEDs (1.0 A max in MSOP-8EP at 0.1 ohm, up to 1.5 A at 0.066 ohm). |
| Inductor | 47 uH | Datasheet recommends 33 to 100 uH; its 3-LED test circuit uses 47 uH. Saturation current must exceed about 0.4 A. |
| Dimming | sensor node PWM at 250 Hz into CTRL | Datasheet: CTRL takes 3.3 V logic directly; above 2.5 V = full current, below 0.2 V = off; best accuracy below 500 Hz. |
| Fail-safe | 2.2 kOhm pull-down on each CTRL | A floating CTRL means full brightness. The pull-down keeps the LEDs off when the cable is unplugged or the node is in reset. The node drives these pins in high-drive mode. |
| Protection | 1.1 A PTC fuse and SS34 series diode on the input | Overload and reversed adapter. The AL8860 has its own open-LED, shorted-LED and over-temperature protection. |

Approximate input power: 2 x 333 mA x (4 LEDs x about 3 V blue / 2.1 V red) = about 7 W of LEDs,
roughly 0.35 A from the 24 V adapter. A 24 V 1 A adapter has margin.

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

- LED forward voltages are typical values from memory, not from a chosen LED's datasheet.
  Pick the LEDs, then check the string voltage stays below about 20 V on a 24 V supply.
- The Bourns SRN6045TA-470M saturation and RMS current ratings were not checked.
- The AL8860 CTRL pin's internal pull-up strength is not in the datasheet; 2.2 kOhm was chosen to
  overpower any plausible internal source. Confirm on the bench that the LEDs stay dark with J2
  unplugged.
- The board routing is a machine result that no one has reviewed by hand, and no board has been made. No thermal check of the AL8860 at 333 mA (well under its 1.5 A rating).
