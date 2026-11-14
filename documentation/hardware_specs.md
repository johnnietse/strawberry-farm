# G.O.S. Hardware Specifications (rev 3.1)

Summary for planning and enclosure work. Full design reference, with datasheet sources:
[`pcbs/gos_sensor_node/HARDWARE.md`](../pcbs/gos_sensor_node/HARDWARE.md).
The rev 2 version of this page is in [`archive/hardware_specs_rev2.md`](archive/hardware_specs_rev2.md).

## Sensor node board

| Item | Value |
|:---|:---|
| Size | 40 x 65 mm, 2 layers, four M2.5 holes 5 mm in from each corner (matches `mechanical/enclosure_gen.scad`) |
| MCU / radio | Raytac MDBT50Q-1MV2 (nRF52840), Thread 802.15.4 and BLE, antenna on the top edge |
| Sensors | Sensirion SHT40-AD1B (temperature, humidity), ams TSL25911FN (light, lux) |
| Battery | one 18650 Li-ion cell in the enclosure cradle, on a 2-pin JST-PH lead |
| Charging | USB-C, TI BQ24074, 494 mA charge, NTC temperature cut-off |
| Supply | TI TPS62740 buck, 3.3 V |
| Cell protection | DW01A + 8205A dual FET: overcharge 4.30 V, over-discharge 2.40 V, over-current about 3 A; reverse-cell P-FET |
| Debug | 10-pin Cortex SWD header, UART on test points |
| Expansion | 4-pin I2C header |
| LED output | 4-pin header carrying two PWM signals to the separate LED driver board |

## Power (estimate, not measured)

About 14 uA asleep; about 40 to 60 uA average with Thread polling every second and a reading every minute,
using the `low_power.conf` firmware build. That is below an 18650's own self-discharge, so the 6-month target
has a wide margin. See the power budget in `HARDWARE.md`.

## LED driver board

Separate board in `pcbs/led_driver/`, powered from its own 12 V supply, driven by the two PWM signals from J4.
See its `README.md` for ratings.

## Status

| Part | State |
|:---|:---|
| Schematic | complete, ERC clean |
| Board | parts placed, not routed |
| Firmware | builds; never run on hardware |
| Gateway receiver | tested against PostgreSQL and Linux multicast; never received from a real node |
