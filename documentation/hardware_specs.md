# G.O.S. Hardware Specifications (sensor node rev 3.2, LED driver rev 1.1)

Summary for planning and enclosure work. Full design reference, with datasheet sources:
[`pcbs/gos_sensor_node/HARDWARE.md`](../pcbs/gos_sensor_node/HARDWARE.md).
The rev 2 version of this page is in [`archive/hardware_specs_rev2.md`](archive/hardware_specs_rev2.md).
What changed in revision 3.2, with test results: [`rev3.2_changes.md`](rev3.2_changes.md); the rev 3.1 and
rev 1.0 boards are kept in `pcbs/archive/`.

## Sensor node board

| Item | Value |
|:---|:---|
| Size | 40 x 65 mm, 4 layers (two inner GND planes, JLC04161H-1080, 1.6 mm, ENIG), four M2.5 holes 5 mm in from each corner (matches `mechanical/enclosure_gen.scad`, checked by `mechanical/fit_check.py`) |
| MCU / radio | Raytac MDBT50Q-1MV2 (nRF52840), Thread 802.15.4 and BLE, antenna on the top edge |
| Sensors | Sensirion SHT40-AD1B (temperature, humidity) on a thermally isolated tongue (rev 3.2), ams TSL25911FN (light, lux), J6 input for a self-powered quantum (PAR) sensor (rev 3.2) |
| Battery | one 18650 Li-ion cell in the enclosure cradle, on a 2-pin JST-PH lead |
| Charging | USB-C, TI BQ24074, 494 mA charge, NTC temperature cut-off |
| Supply | TI TPS62740 buck, 3.3 V |
| Cell protection | DW01A + FS8205A dual FET (SOT-23-6): overcharge 4.30 V, over-discharge 2.40 V, over-current about 3 A; reverse-cell P-FET |
| Debug | 10-pin Cortex SWD header, UART on test points |
| Expansion | 4-pin I2C header |
| LED output | 4-pin header carrying two PWM signals to the separate LED driver board |

## Power (estimate, not measured)

About 14 uA asleep; about 40 to 60 uA average with Thread polling every second and a reading every minute,
using the `low_power.conf` firmware build. That is below an 18650's own self-discharge, so the 6-month target
has a wide margin. See the power budget in `HARDWARE.md`.

## LED driver board

Separate board in `pcbs/led_driver/` (60 x 45 mm, 4 layers), powered from a 24 V adapter, driven by
the two PWM signals from the sensor node's J4. Two AL8860 constant-current channels at 333 mA, or 667 mA per channel with its solder jumper bridged (rev 1.1)
(blue and red LED strings, 4 LEDs each), 100 uH inductors, 1.5 k fail-safe pull-downs. LTspice
results in `simulation/README.md`; ratings in its `README.md`.

## Enclosures

Sensor node: 85 x 130 x 48 mm with the 18650 cradle, vents, light window and tube, two cable glands (LED cable; PAR sensor cable, rev 3.2).
LED driver: 65.6 x 62 x 36 mm with mounting flanges. Both in ASA, generated from the KiCad boards
and fit checked (`mechanical/README.md`).

## Status

| Part | State |
|:---|:---|
| Schematic | complete, ERC clean |
| Board | routed (4 layers; buck loop routed by hand), DRC clean, layout reviewed (`design_review.md`), order files ready (`ordering.md`); not made |
| LED driver board | routed (4 layers; switching loops routed by hand), DRC clean, LTspice checked, order files ready; not made |
| Enclosures | both generated from the boards, 15 fit checks pass, print files ready; not printed |
| Firmware | six builds (PACKET_V5, with PAR); never run on hardware |
| Gateway receiver | 44 tests; tested against PostgreSQL and Linux multicast; never received from a real node |
